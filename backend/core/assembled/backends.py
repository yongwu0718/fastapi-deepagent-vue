from pathlib import Path
import shutil

from deepagents.backends import CompositeBackend, FilesystemBackend, LocalShellBackend
from backend.config.env_settings import MEMORY_DIR, SKILLS_DIR, DOC_INDEX, WORKSPACE_DIR
from backend.core.skill_manager.filtered_backend import SkillFilteredBackend
from backend.config.logger import get_logger
import os

logger = get_logger(__name__)

# 合并 PATH 环境变量
merged_path = os.pathsep.join([
    # 系统 PATH
    r"D:\python_3.12",
    r"D:\python_3.12\Scripts",
    r"D:\node",
    os.environ.get("PATH", ""),
])


def _ensure_user_dir_initialized(user_dir: Path, shared_dir: str | None) -> None:
    """首次访问时从共享目录复制文件到用户目录（幂等）。

    与 memory_and_skill_service._ensure_user_init 逻辑一致：
    检查 .initialized 标记，不存在则 copytree，然后写入标记。
    """
    init_marker = user_dir / ".initialized"
    if init_marker.exists():
        return
    if shared_dir:
        shared = Path(shared_dir)
        if shared.exists():
            logger.info("初始化用户目录 | target=%s | source=%s", user_dir, shared)
            try:
                shutil.copytree(shared, user_dir, dirs_exist_ok=True)
            except Exception:
                logger.warning("用户目录初始化失败 | target=%s", user_dir, exc_info=True)
    init_marker.touch()


def create_backend(cache=None):
    """构建 CompositeBackend。

    若传入用户 cache，则 /active_skills/ 和 /memory/ 指向用户专属目录，
    SkillFilteredBackend 从用户 cache 读取启用列表。
    首次构建时从全局共享目录复制 skill/memory 文件到用户目录。

    若不传 cache（向后兼容），使用全局共享目录。

    Args:
        cache: 当前用户的 diskcache 实例（可选）。

    Returns:
        CompositeBackend 实例。
    """
    if cache is not None:
        # ── 用户隔离模式 ──
        user_base = Path(cache.directory)
        user_skills_dir = user_base / "skills"
        user_memory_dir = user_base / "memory"

        # 确保用户目录存在
        user_base.mkdir(parents=True, exist_ok=True)
        user_skills_dir.mkdir(parents=True, exist_ok=True)
        user_memory_dir.mkdir(parents=True, exist_ok=True)

        # 首次访问时从全局共享目录复制 skill/memory 文件到用户目录
        _ensure_user_dir_initialized(user_skills_dir, SKILLS_DIR)
        _ensure_user_dir_initialized(user_memory_dir, MEMORY_DIR)

        return CompositeBackend(
            default=LocalShellBackend(
                root_dir=os.path.join(WORKSPACE_DIR),
                virtual_mode=True,
                inherit_env=True,
                env={"PATH": merged_path},
            ),
            routes={
                "/memory/": FilesystemBackend(root_dir=str(user_memory_dir), virtual_mode=True),
                "/active_skills/": SkillFilteredBackend(
                    FilesystemBackend(root_dir=str(user_skills_dir), virtual_mode=True),
                    cache=cache,
                ),
                "/knowledge/": FilesystemBackend(root_dir=DOC_INDEX, virtual_mode=True),
            }
        )

    # ── 全局模式（向后兼容） ──
    return CompositeBackend(
        default=LocalShellBackend(
            root_dir=os.path.join(WORKSPACE_DIR),
            virtual_mode=True,
            inherit_env=True,
            env={"PATH": merged_path},
        ),
        routes={
            "/memory/": FilesystemBackend(root_dir=MEMORY_DIR, virtual_mode=True),
            "/active_skills/": SkillFilteredBackend(
                FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True),
            ),
            "/knowledge/": FilesystemBackend(root_dir=DOC_INDEX, virtual_mode=True),
        }
    )


# 向后兼容：保留全局 backend（无用户隔离）
backend = create_backend()
