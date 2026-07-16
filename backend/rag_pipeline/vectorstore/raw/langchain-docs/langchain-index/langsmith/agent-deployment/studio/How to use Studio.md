# 如何使用 Studio

本页介绍您在 Studio 中将使用的核心工作流。它解释了如何运行您的应用、管理 assistant 配置以及处理对话 threads。每个部分都包含 graph 模式（完整功能的 graph 执行视图）和 chat 模式（轻量级对话界面）中的步骤：

* 运行应用：执行您的应用或代理并观察其行为。
* 管理 assistants：创建、编辑和选择应用使用的 assistant 配置。
* 管理 threads：查看和组织 threads，包括分叉或编辑过去的 runs 以进行调试。

## 运行应用

### 指定输入

1. 在页面左侧 graph 界面下方的 **Input** 区域中定义 graph 的输入。Studio 将尝试根据 graph 定义的状态 schema 为您的输入渲染一个表单。要禁用此功能，请点击 **View Raw** 按钮，这将为您提供一个 JSON 编辑器。
2. 点击 **Input** 区域顶部的向上或向下箭头，可以切换并使用之前提交过的输入。

### 运行设置

#### Assistant

要指定用于本次运行的 assistant：

1. 点击左下角的 **Settings** 按钮。如果当前已选择 assistant，按钮上还会显示 assistant 名称。如果未选择 assistant，则会显示 **Manage Assistants**。
2. 选择要运行的 assistant。
3. 点击模态框顶部的 **Active** 切换按钮以激活它。

更多信息请参阅管理 assistants。

#### Streaming

点击 **Submit** 旁边的下拉菜单，然后点击切换按钮以启用或禁用流式传输。

#### Breakpoints

要使用断点运行 graph：

1. 点击 **Interrupt**。
2. 选择一个节点，并选择是在该节点执行之前还是之后暂停。
3. 在 thread 日志中点击 **Continue** 以恢复执行。

有关断点的更多信息，请参阅 Human-in-the-loop。

#### 提交运行

要使用指定的输入和运行设置提交运行：

1. 点击 **Submit** 按钮。这将向当前选定的 thread 添加一个 run。如果当前未选择 thread，则将创建一个新 thread。
2. 要取消正在进行的运行，请点击 **Cancel** 按钮。

在对话面板底部指定聊天应用的输入。

1. 点击 **Send message** 按钮，将输入作为 Human 消息提交并流式接收响应。

要取消正在进行的运行：

1. 点击 **Cancel**。
2. 点击 **Show tool calls** 切换按钮以在对话中隐藏或显示工具调用。

## 管理 assistants

Studio 允许您查看、编辑和更新您的 assistants，并允许您使用这些 assistant 配置运行您的 graph。

更多概念详情请参阅 Assistants 概述。

要查看您的 assistants：

1. 点击左下角的 **Manage Assistants**。这将打开一个模态框，供您查看所选 graph 的所有 assistants。
2. 指定您希望标记为 **Active** 的 assistant 及其版本。当提交 runs 时，LangSmith 将使用此 assistant。

**Default configuration** 选项将处于活动状态，它反映您的 graph 中定义的默认配置。对此配置进行的编辑将用于更新运行时配置，但除非您点击 **Create new assistant**，否则不会更新或创建新的 assistant。

Chat 模式使您能够通过页面顶部的下拉选择器在图中的不同 assistants 之间切换。要创建、编辑或删除 assistants，请使用 Graph 模式。

## 管理 threads

Studio 提供了查看服务器上保存的所有 threads 并编辑其状态的工具。您可以在 graph 模式和 chat 模式下创建新 threads、在 threads 之间切换以及修改过去的状态。

### 查看 threads

1. 在右侧窗格的顶部，选择下拉菜单以查看现有的 threads。
2. 选择所需的 thread，thread 历史将显示在页面右侧。
3. 要创建新的 thread，请点击 **+ New Thread** 并提交一个 run。
4. 要在 thread 中查看更细粒度的信息，请将页面顶部的滑块向右拖动。要查看较少信息，请将滑块向左拖动。此外，可以折叠或展开状态的单个轮次、节点和键。
5. 在 `Pretty` 和 `JSON` 模式之间切换以获得不同的渲染格式。

### 编辑 thread 历史

要编辑 thread 的状态：

1. 在所需节点旁边选择 **Edit node state**。
2. 根据需要编辑节点的输出，然后点击 **Fork** 以确认。这将从所选节点的 checkpoint 创建一个新的分叉 run。

如果您希望从给定的 checkpoint 重新运行 thread 而不编辑状态，请点击 **Re-run from here**。这同样会从所选 checkpoint 创建一个新的分叉 run。这对于使用不特定于状态的更改（例如所选的 assistant）重新运行非常有用。

1. 在页面右侧窗格中查看所有 threads。
2. 选择所需的 thread，thread 历史将显示在中央面板中。
3. 要创建新的 thread，请点击 **+** 并提交一个 run。

要编辑 thread 中的 human 消息：

1. 点击 human 消息下方的 **Edit node state**。
2. 根据需要编辑消息并提交。这将创建对话历史的一个新分叉。
3. 要重新生成 AI 消息，请点击 AI 消息下方的重试图标。

## 后续步骤

请参阅以下指南，了解有关您可以在 Studio 中完成的任务的更多详细信息：

* 迭代 prompts
* 在 datasets 上运行实验