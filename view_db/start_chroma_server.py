"""
启动 Chroma 本地服务器脚本。
绕过 Windows 下 uv trampoline 的路径规范化问题，直接用 Python 调用 chromadb 内部 CLI。

用法：
    python file_tool/chroma/start_chroma_server.py
    python file_tool/chroma/start_chroma_server.py --path F:/custom/chroma_db
"""
import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = r"F:\index_rag\data\save_db\chroma_db"

def main():
    parser = argparse.ArgumentParser(description="启动 Chroma 本地服务器")
    parser.add_argument(
        "--path",
        default=DEFAULT_DB_PATH,
        help=f"Chroma 持久化数据库路径 (默认: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="绑定地址 (默认: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8010,
        help="绑定端口 (默认: 8010)"
    )
    args = parser.parse_args()

    os.makedirs(args.path, exist_ok=True)

    print(f"🚀 启动 Chroma 服务器...")
    print(f"   数据库路径: {args.path}")
    print(f"   监听地址:   {args.host}:{args.port}")

    from chromadb_rust_bindings import cli

    cli_args = [
        "chroma", "run",
        "--path", args.path,
        "--host", args.host,
        "--port", str(args.port),
    ]

    try:
        cli(cli_args)
    except KeyboardInterrupt:
        print("\n⏹️  Chroma 服务器已停止")
    except Exception as e:
        print(f"❌ 启动 Chroma 服务器失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()