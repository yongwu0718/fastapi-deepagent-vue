import asyncio
import io
import os
import sys
import time
import uuid

import aiofiles
import qrcode
from wechatbot import WeChatBot, IncomingMessage
from langchain.messages import HumanMessage
from backend.core.main_agent import init_graph
from backend.api.utils.file_handler import FILE_EXTRACTORS
from backend.config.logger import setup_logging, get_logger
from backend.config.observability import build_langfuse_config, langfuse_init
from backend.config.env_settings import LANGFUSE_TRACING_ENABLED,UPLOADS_DIR

# ── 初始化日志系统：setup_logging() 只在 FastAPI 启动时自动调用，
#    独立脚本必须手动调用才能写入日期日志文件
setup_logging()
logger = get_logger(__name__)

# ── 初始化 Langfuse 可观测性 ──
langfuse_init()

def extract_ai_text(result: dict) -> str:
    """从 graph.ainvoke 结果中提取最后一条 AI 消息文本。"""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai":
            content = getattr(msg, "content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                joined = "\n".join(parts).strip()
                if joined:
                    return joined
    return "（未获取到有效回复）"


class WeChatAgentBot:
    """微信 AI Agent 机器人，封装消息处理、文件解析、Agent 调用等核心逻辑。

    将原本 _main() 中的内嵌函数与状态提升为有组织的类方法，
    _main() 自身简化为初始化和启动。
    """

    MERGE_TIMEOUT: float = 3.0  # 文本等待附件的最长秒数（类常量）

    # ── 文件处理 ──────────────────────────────────────────
    @staticmethod
    async def _extract_files(bot: WeChatBot, msg: IncomingMessage) -> list[tuple[str, str]]:
        """从消息中提取支持的附件文本，返回 [(file_name, text), ...]"""
        results: list[tuple[str, str]] = []
        if not msg.files:
            return results

        supported_files: list[tuple] = []
        for fc in msg.files:
            file_name = fc.file_name or "unknown"
            ext = os.path.splitext(file_name.lower())[1]
            extractor = FILE_EXTRACTORS.get(ext)
            if extractor is None:
                logger.info("跳过不支持的文件 | user=%s name=%s", msg.user_id, file_name)
            else:
                supported_files.append((fc, ext, extractor))

        for fc, ext, extractor in supported_files:
            file_name = fc.file_name or "unknown"
            logger.info("正在下载附件 | user=%s name=%s size=%s", msg.user_id, file_name, fc.size)
            downloaded = await bot.download(msg)
            if downloaded is None or not downloaded.data:
                logger.warning("附件下载失败 | user=%s name=%s", msg.user_id, file_name)
                continue

            logger.info("附件下载完成，正在提取文本 | user=%s name=%s bytes=%d type=%s",
                        msg.user_id, file_name, len(downloaded.data), ext)
            file_bytes = io.BytesIO(downloaded.data) if ext == ".pdf" else downloaded.data
            file_text = await asyncio.to_thread(extractor, file_bytes)
            results.append((file_name, file_text))
            logger.info("文本提取完成 | user=%s name=%s chars=%d", msg.user_id, file_name, len(file_text))

            # 异步写入 workspace
            txt_name = os.path.splitext(file_name)[0] + ".md"
            txt_path = os.path.join(UPLOADS_DIR, txt_name)
            os.makedirs(UPLOADS_DIR, exist_ok=True)
            async with aiofiles.open(txt_path, "w", encoding="utf-8") as f:
                await f.write(file_text)
            logger.info("文本已保存 | user=%s path=%s", msg.user_id, txt_path)

        return results

    # ── 生命周期 ──────────────────────────────────────────
    def __init__(self, graph):
        self.graph = graph
        self.bot: WeChatBot | None = None
        self._threads: dict[str, str] = {}
        self._pending_texts: dict[str, tuple[str, IncomingMessage, asyncio.Task]] = {}

    def _get_thread_id(self, user_id: str) -> str:
        """每个微信用户对应一个 thread_id，按需创建。"""
        if user_id not in self._threads:
            self._threads[user_id] = uuid.uuid4().hex
            logger.info("新会话 | user=%s thread=%s", user_id, self._threads[user_id])
        return self._threads[user_id]

    async def _build_bot(self) -> WeChatBot:
        """创建并登录 WeChatBot 实例。"""
        def _on_bot_error(err: Exception) -> None:
            cls_name = type(err).__name__
            err_msg = str(err) or "(无消息)"
            if cls_name == "TimeoutError":
                logger.debug("长轮询超时（正常） | %s", err_msg)
            else:
                logger.error("Bot 内部错误 | type=%s msg=%s", cls_name, err_msg)

        def _show_qr(url: str) -> None:
            """将扫码链接生成二维码图片并打开。"""
            img = qrcode.make(url)
            qr_path = os.path.join(UPLOADS_DIR, "qr_code.png")
            os.makedirs(UPLOADS_DIR, exist_ok=True)
            img.save(qr_path)
            print(f"\n二维码已保存至: {qr_path}", flush=True)
            print(f"扫码链接: {url}", flush=True)
            print("\n请用微信扫描二维码图片，或复制链接到微信中打开", flush=True)
            logger.info("二维码链接 | url=%s path=%s", url, qr_path)
            # 尝试自动打开图片
            try:
                os.startfile(qr_path)
            except Exception:
                pass

        bot = WeChatBot(
            on_qr_url=_show_qr,
            on_scanned=lambda: print("已扫码，等待确认..."),
            on_error=_on_bot_error,
        )
        bot._log = lambda msg: logger.debug("[wechatbot-sdk] %s", msg)

        # 凭据在 24 小时内有效，过期后强制扫码
        cred_path = os.path.join(os.path.expanduser("~"), ".wechatbot", "credentials.json")
        need_qr = True
        if os.path.isfile(cred_path):
            age = time.time() - os.path.getmtime(cred_path)
            if age < 86400:  # 24 小时
                need_qr = False
                logger.info("凭据有效（%.1f 小时前），跳过扫码", age / 3600)
            else:
                logger.info("凭据已过期（%.1f 小时前），需要重新扫码", age / 3600)

        creds = await bot.login(force=need_qr)
        logger.info("登录成功 | account=%s user=%s", creds.account_id, creds.user_id)
        return bot

    # ── Agent 调用 ────────────────────────────────────────
    async def _invoke_agent(self, user_id: str, reply_msg: IncomingMessage,
                            question: str, attachment_texts: list[tuple[str, str]]) -> None:
        """调用 LangGraph Agent 并回复用户。"""
        content_blocks: list[dict[str, str]] = []
        if question:
            content_blocks.append({"type": "text", "text": question})
        for i, (name, content) in enumerate(attachment_texts):
            content_blocks.append({"type": "text", "text": f"[附件 {i + 1}: {name}]\n{content}"})

        assert self.bot is not None
        try:
            await self.bot.send_typing(user_id)
            thread_id = self._get_thread_id(user_id)
            config: dict = {"configurable": {"thread_id": thread_id}}
            if LANGFUSE_TRACING_ENABLED:
                langfuse_cfg = build_langfuse_config(thread_id=thread_id, tags=["wechat-bot"])
                config["callbacks"] = langfuse_cfg["callbacks"]
                config["metadata"] = langfuse_cfg["metadata"]

            result = await self.graph.ainvoke(
                {"messages": [HumanMessage(content=content_blocks)]},
                config=config,
            )
            reply = extract_ai_text(result)
            logger.info("Agent 响应 | user=%s reply=%.100s", user_id, reply[:100])
            await self.bot.reply(reply_msg, reply)

        except Exception:
            logger.exception("Agent 调用失败 | user=%s", user_id)
            await self.bot.reply(reply_msg, "抱歉，处理你的消息时出错了，请稍后重试。")

    # ── 消息处理 ──────────────────────────────────────────
    async def _handle_message(self, msg: IncomingMessage) -> None:
        """处理单条微信消息：命令路由、文本-附件合并、Agent 调用。"""
        user_id = msg.user_id
        text = msg.text

        if not text and not msg.files:
            return

        logger.info("收到消息 | user=%s text=%.100s files=%d",
                    user_id, text[:100] if text else "", len(msg.files))

        # ── 特殊命令：重置会话 ──
        # WeChat SDK 可能将反斜杠转义为 \\，因此先去掉所有反斜杠再比较
        if text and text.replace("\\", "").strip() == "重置":
            self._reset_session(user_id, msg)
            return

        # ── 收到文件 → 检查是否有待合并的文本 ──
        if msg.files:
            await self._handle_file_message(user_id, msg, text)
            return

        # ── 纯文本消息（无附件）→ 直接调用 Agent ──
        if text:
            await self._invoke_agent(user_id, msg, text, [])

    def _reset_session(self, user_id: str, msg: IncomingMessage) -> None:
        """重置用户会话线程。"""
        pending = self._pending_texts.pop(user_id, None)
        if pending:
            pending[2].cancel()
        old_tid = self._threads.pop(user_id, None)
        new_tid = uuid.uuid4().hex
        self._threads[user_id] = new_tid
        logger.info("会话重置 | user=%s old_thread=%s new_thread=%s",
                    user_id, old_tid or "无", new_tid)
        asyncio.create_task(self._do_reply(msg, "会话已重置，下次消息将开启新对话。"))

    async def _do_reply(self, msg: IncomingMessage, text: str) -> None:
        """发送「正在输入」提示 + 回复文本。"""
        assert self.bot is not None
        await self.bot.send_typing(msg.user_id)
        await self.bot.reply(msg, text)

    async def _handle_file_message(self, user_id: str, msg: IncomingMessage,
                                   fallback_text: str | None) -> None:
        """处理带附件的消息（可能与缓冲区文本合并）。"""
        pending = self._pending_texts.pop(user_id, None)
        if pending:
            pending[2].cancel()
            merged_question, _, _ = pending
            logger.info("消息合并 | user=%s text=%.50s + %d files",
                        user_id, merged_question[:50], len(msg.files))
        else:
            merged_question = fallback_text or ""

        assert self.bot is not None
        attachment_texts = await self._extract_files(self.bot, msg)
        await self._invoke_agent(user_id, msg, merged_question, attachment_texts)

    def _schedule_text_merge(self, user_id: str, text: str, msg: IncomingMessage) -> None:
        """将纯文本暂存，等待 MERGE_TIMEOUT 秒看是否有附件到达。"""
        prev = self._pending_texts.pop(user_id, None)
        if prev:
            prev[2].cancel()

        async def _on_timeout(uid: str, t: str, m: IncomingMessage) -> None:
            await asyncio.sleep(self.MERGE_TIMEOUT)
            pending = self._pending_texts.pop(uid, None)
            if pending:
                logger.info("文本合并超时，单独处理 | user=%s text=%.50s", uid, t[:50])
                await self._invoke_agent(uid, m, t, [])

        task = asyncio.create_task(_on_timeout(user_id, text, msg))
        self._pending_texts[user_id] = (text, msg, task)

    # ── 主循环 ────────────────────────────────────────────
    async def run(self) -> None:
        """登录并启动长轮询。"""
        self.bot = await self._build_bot()
        self.bot.on_message(self._handle_message)

        logger.info("开始监听微信消息 (Ctrl+C 停止)")
        try:
            await self.bot.start()
        except KeyboardInterrupt:
            self.bot.stop()
            logger.info("已停止监听")


async def _main():
    """初始化 Agent 并启动 Bot。"""
    logger.info("正在初始化 LangGraph Agent ...")
    async with init_graph() as graph:
        logger.info("Agent 编译完成，开始连接微信")
        bot = WeChatAgentBot(graph)
        await bot.run()


def main():
    """同步入口，供 console script 调用"""
    asyncio.run(_main())

if __name__ == "__main__":
    asyncio.run(_main())
