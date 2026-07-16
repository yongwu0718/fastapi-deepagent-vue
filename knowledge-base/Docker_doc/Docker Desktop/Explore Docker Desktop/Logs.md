# 探索 Docker Desktop 中的 **Logs** 视图

Docker Desktop 中的 **Logs** 视图提供了一个统一的、实时的日志流，汇聚来自所有容器和近期构建的日志。与从 [**Containers** 视图](/desktop/use-desktop/logs/container/)访问的日志不同，**Logs** 视图允许您从单个界面监控和搜索整个环境中的日志输出（最多可达 100,000 条条目）。

## 日志条目 (Log entries)

表格视图中的每条日志条目显示以下内容：

| 列 (Column)       | 描述 (Description)                                                                    |
| ------------- | ------------------------------------------------------------------------------ |
| **Timestamp** | 日志行发出的日期和时间，例如 `2026-02-26 11:18:53`。 |
| **Object**    | 产生日志行的容器或构建。                             |
| **Message**   | 完整的日志消息，包括任何状态码，如 `[ OK ]`。             |

选择行右侧的展开箭头可显示该条目的完整消息。

## 搜索和过滤日志 (Search and filter logs)

使用 **Logs** 视图顶部的 **Search** 字段查找特定条目。搜索栏支持：

- 用于精确匹配搜索的纯文本词
- 正则表达式（例如，`/error|warn/`）

您可以保存搜索词以便日后快速访问。

要进一步筛选日志流，请选择工具栏中的 **Filter** 图标以打开容器过滤面板。在这里您可以：

- 勾选单个容器以仅显示其输出
- 勾选 Compose 堆栈以显示或隐藏整个组
- 使用 **Select all** 或 **Clear all** 快速一次性切换所有容器

## 显示设置 (Display settings)

选择工具栏中的 **Display settings** 图标以切换以下选项：

- **View build logs**：在日志流中包含或排除构建相关的日志输出
- **Wrap lines**（自动换行）
- **Show timestamps**（显示时间戳）

## 反馈 (Feedback)

选择视图顶部的 **Give feedback** 以分享建议或报告问题。