# 虚拟环境 & 包管理

## 激活虚拟环境

```bash
.venv\Scripts\activate
```

## uv 常用命令

初始化项目，生成 `pyproject.toml`：

```bash
uv init
```

同步安装依赖：

```bash
uv sync
```

安装新包：

```bash
uv pip install <package>
```

更新已安装的包：

```bash
uv pip install -U
```

删除依赖包：

```bash
uv remove <package>
```

检查依赖冲突：

```bash
uv pip check
```

查看顶层依赖（需安装 pipdeptree）：

```powershell
pipdeptree --warn silence | Select-String -NotMatch '^\s'
```

## 静态代码审查

```powershell
pylint F:\langchain-rag\agent_rag\utils\nodes.py --verbose nodes.py
```
