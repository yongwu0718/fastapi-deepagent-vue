from deepagents.backends import CompositeBackend, FilesystemBackend, LocalShellBackend
from backend.config.env_settings import MEMORY_DIR, SKILLS_DIR, DOC_INDEX, WORKSPACE_DIR
from backend.core.skill_manager.filtered_backend import SkillFilteredBackend
import os

# 合并 PATH 环境变量
merged_path = os.pathsep.join([
    # 系统 PATH
    r"D:\python_3.12",
    r"D:\python_3.12\Scripts",
    r"D:\node",
    os.environ.get("PATH", ""),
])

backend = CompositeBackend(
    # default 使用 LocalShellBackend，提供 execute 能力
    default=LocalShellBackend(
        root_dir=os.path.join(WORKSPACE_DIR),
        virtual_mode=True,
        inherit_env=True,
        env={"PATH": merged_path},
    ),
    routes={
        # 虚拟记忆后端,写入文件
        "/memory/": FilesystemBackend(root_dir=MEMORY_DIR, virtual_mode=True),
        # 技能后端：动态过滤，ls 时按 skills_config.yaml 隐藏未启用的 skill
        "/active_skills/": SkillFilteredBackend(
            FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True)
        ),
        # 虚拟知识库后端,写入文件
        "/knowledge/": FilesystemBackend(root_dir=DOC_INDEX, virtual_mode=True),
    }
)