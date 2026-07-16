# 拒绝并发

本指南假定您了解什么是双文本（double-texting），您可以在双文本概念指南中了解相关内容。

本指南介绍用于处理双文本的 `reject` 选项，该选项会通过抛出错误来拒绝新的 graph run，并继续执行原始 run 直到完成。以下是使用 `reject` 选项的快速示例。

## 设置
导入所需的包并实例化 client、assistant 和 thread。

```python
import httpx
from langchain_core.messages import convert_to_messages
from langgraph_sdk import get_client

client = get_client(url=<your_url>)
# Using the graph deployed with the name "agent"
assistant_id = "agent"
thread = await client.threads.create()
```
## 创建 runs

现在我们可以运行一个 thread，并尝试使用 “reject” 选项运行第二个 run，由于我们已经启动了一个 run，第二个 run 应该会失败：

```python
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "what's the weather in sf?"}]},
)
try:
    await client.runs.create(
        thread["thread_id"],
        assistant_id,
        input={
            "messages": [{"role": "user", "content": "what's the weather in nyc?"}]
        },
        multitask_strategy="reject",
    )
except httpx.HTTPStatusError as e:
    print("Failed to start concurrent run", e)
```

输出：

```
Failed to start concurrent run Client error '409 Conflict' for url 'http://localhost:8123/threads/f9e7088b-8028-4e5c-88d2-9cc9a2870e50/runs'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/409
```

## 查看 run 结果

我们可以验证原始的 thread 已经执行完成：

```python
# wait until the original run completes
await client.runs.join(thread["thread_id"], run["run_id"])

state = await client.threads.get_state(thread["thread_id"])

for m in convert_to_messages(state["values"]["messages"]):
    m.pretty_print()
```
输出：
```
================================ Human Message =================================

what's the weather in sf?
================================== Ai Message ==================================

[{'id': 'toolu_01CyewEifV2Kmi7EFKHbMDr1', 'input': {'query': 'weather in san francisco'}, 'name': 'tavily_search_results_json', 'type': 'tool_use'}]
Tool Calls:
tavily_search_results_json (toolu_01CyewEifV2Kmi7EFKHbMDr1)
Call ID: toolu_01CyewEifV2Kmi7EFKHbMDr1
Args:
query: weather in san francisco
================================= Tool Message =================================
Name: tavily_search_results_json

[{"url": "https://www.accuweather.com/en/us/san-francisco/94103/june-weather/347629", "content": "Get the monthly weather forecast for San Francisco, CA, including daily high/low, historical averages, to help you plan ahead."}]
================================== Ai Message ==================================

According to the search results from Tavily, the current weather in San Francisco is:

The average high temperature in San Francisco in June is around 65°F (18°C), with average lows around 54°F (12°C). June tends to be one of the cooler and foggier months in San Francisco due to the marine layer of fog that often blankets the city during the summer months.

Some key points about the typical June weather in San Francisco:

* Mild temperatures with highs in the 60s F and lows in the 50s F
* Foggy mornings that often burn off to sunny afternoons
* Little to no rainfall, as June falls in the dry season
* Breezy conditions, with winds off the Pacific Ocean
* Layers are recommended for changing weather conditions

In summary, you can expect mild, foggy mornings giving way to sunny but cool afternoons in San Francisco this time of year. The marine layer keeps temperatures moderate compared to other parts of California in June.
```