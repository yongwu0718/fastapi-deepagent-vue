# 自身记忆

## Python 解释器调用 (execute 工具)

### 工作环境
- 沙箱的当前工作目录（CWD）在 `F:\index_rag\knowledge-base\workspace`
- `/knowledge/workspace/` 目录下的文件可直接用 `python 文件名.py` 运行，无需拼路径
- `python3` 命令不可用，必须用 `python`
- 工作目录不在沙箱内，写入临时文件需要先通过 `python -c "with open(...)"` 创建，且路径需用 `/tmp/...` 但在执行时沙箱会拼接成完整路径，可能导致文件找不到。因此：
  - **最佳实践：把代码写为沙箱 CWD 下的 `.py` 文件，或者直接用 `python -c "..."` 执行**
  - 也可以用 `read_file` 读取代码内容，然后通过 `write_file` 写到 `/knowledge/workspace/xxx.py`，再用 `python xxx.py` 运行

### 支持的运行方式
| 方式 | 命令 |
|------|------|
| 直接运行文件 (CWD下) | `python a.py` |
| 运行其他路径文件 | `python /some/full/path/file.py` （需路径在沙箱可访问） |
| 运行内联代码 | `python -c "print('hello')"` |

## 用户偏好
- 用户希望看到推理过程，不只是最终结论。
- **思维链（thinking 标签）要展开**，展示真实的内部思考：
  - 对问题的理解与分析
  - 考虑了几种方向/方案，为什么选这个
  - 排除了什么可能性，理由是什么
  - 工具调用的决策逻辑（为什么用这个 tool、为什么现在用）
  - 结果不理想时的反思
- thinking 不是"给自己看的笔记"，而是用户想看到的**推理过程展示**。
- 简洁不等于只给结论。分析、对比、建议类问题更要展开推理链。