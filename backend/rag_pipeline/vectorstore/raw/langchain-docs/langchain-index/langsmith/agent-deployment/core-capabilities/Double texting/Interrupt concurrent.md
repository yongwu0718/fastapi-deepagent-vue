# 中断并发运行

本指南假定您了解什么是双文本（double-texting），您可以在双文本概念指南中了解相关内容。

本指南介绍用于处理双文本的 `interrupt` 选项，该选项会中断先前对 graph 的 run，并使用双文本启动一个新的 run。此选项不会删除第一个 run，而是将其保留在数据库中，但将其状态设置为 `interrupted`。以下是使用 `interrupt` 选项的快速示例。

## 设置

导入所需的包并实例化 client、assistant 和 thread。

```python
import asyncio

from langchain_core.messages import convert_to_messages
from langgraph_sdk import get_client

client = get_client(url=<your_url>)
# Using the graph deployed with the name "agent"
assistant_id = "agent"
thread = await client.threads.create()
```
## 创建 runs

现在我们可以开始两个 run，并加入第二个 run 直到它完成：

```python
# the first run will be interrupted
interrupted_run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "what's the weather in sf?"}]},
)
# sleep a bit to get partial outputs from the first run
await asyncio.sleep(2)
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "what's the weather in nyc?"}]},
    multitask_strategy="interrupt",
)
# wait until the second run completes
await client.runs.join(thread["thread_id"], run["run_id"])
```
## 查看 run 结果

我们可以看到 thread 包含了第一次 run 的部分数据加上第二次 run 的数据。

```python
state = await client.threads.get_state(thread["thread_id"])

for m in convert_to_messages(state["values"]["messages"]):
    m.pretty_print()
```

输出：

```
================================ Human Message =================================

what's the weather in sf?
================================== Ai Message ==================================

[{'id': 'toolu_01MjNtVJwEcpujRGrf3x6Pih', 'input': {'query': 'weather in san francisco'}, 'name': 'tavily_search_results_json', 'type': 'tool_use'}]
Tool Calls:
tavily_search_results_json (toolu_01MjNtVJwEcpujRGrf3x6Pih)
Call ID: toolu_01MjNtVJwEcpujRGrf3x6Pih
Args:
query: weather in san francisco
================================= Tool Message =================================
Name: tavily_search_results_json

[{"url": "https://www.wunderground.com/hourly/us/ca/san-francisco/KCASANFR2002/date/2024-6-18", "content": "High 64F. Winds W at 10 to 20 mph. A few clouds from time to time. Low 49F. Winds W at 10 to 20 mph. Temp. San Francisco Weather Forecasts. Weather Underground provides local & long-range weather ..."}]
================================ Human Message =================================

what's the weather in nyc?
================================== Ai Message ==================================

[{'id': 'toolu_01KtE1m1ifPLQAx4fQLyZL9Q', 'input': {'query': 'weather in new york city'}, 'name': 'tavily_search_results_json', 'type': 'tool_use'}]
Tool Calls:
tavily_search_results_json (toolu_01KtE1m1ifPLQAx4fQLyZL9Q)
Call ID: toolu_01KtE1m1ifPLQAx4fQLyZL9Q
Args:
query: weather in new york city
================================= Tool Message =================================
Name: tavily_search_results_json

[{"url": "https://www.accuweather.com/en/us/new-york/10021/june-weather/349727", "content": "Get the monthly weather forecast for New York, NY, including daily high/low, historical averages, to help you plan ahead."}]
================================== Ai Message ==================================

The search results provide weather forecasts and information for New York City. Based on the top result from AccuWeather, here are some key details about the weather in NYC:

* This is a monthly weather forecast for New York City for the month of June.
* It includes daily high and low temperatures to help plan ahead.
* Historical averages for June in NYC are also provided as a reference point.
* More detailed daily or hourly forecasts with precipitation chances, humidity, wind, etc. can be found by visiting the AccuWeather page.

In summary, the search provides a convenient overview of the expected weather conditions in New York City over the next month to give you an idea of what to prepare for if traveling or making plans there. Let me know if you need any other details!
```

验证原始的、被中断的 run 确实被中断了。

```python
print((await client.runs.get(thread["thread_id"], interrupted_run["run_id"]))["status"])
```

输出：

```
'interrupted'
```