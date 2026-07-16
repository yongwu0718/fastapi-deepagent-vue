# 使用服务端缓存

> 在您的 agent 部署中使用 stale-while-revalidate 和键值缓存 API 进行服务端缓存。

Agent Server 包含一个内置缓存，您可以在已部署的 graph 中使用。使用键和加载函数调用 `swr`，服务器会缓存结果，在后台重新验证过期的条目，并在每次读取时返回最新数据。

所有缓存 API **仅限服务端**，需要 LangGraph Agent Server 运行时。值必须是可 JSON 序列化的。

`swr` 需要 Agent Server 运行时 **v0.7.79** 或更高版本，目前处于 **beta** 阶段。
`cache_get` 和 `cache_set` 需要 **v0.7.29** 或更高版本。

## 快速开始

传入一个键和一个异步加载函数。`swr` 会返回缓存值（如果存在），否则调用您的加载函数获取它：

```python
from langgraph_sdk.cache import swr

result = await swr("config:global", load_config)
config_data = result.value
```

在第一次调用时，`swr` 会等待 `load_config()` 并缓存结果。在后续调用中，它会立即返回缓存的值，并在后台进行重新验证。

## 配置新鲜度

控制缓存值被视为“fresh”的时长以及何时过期：

```python
from datetime import timedelta
from langgraph_sdk.cache import swr

result = await swr(
    "config:global",
    load_config,
    fresh_for=timedelta(minutes=5),
    max_age=timedelta(hours=1),
)
```

| 参数         | 默认值                  | 描述                                                                           |
| ------------ | ----------------------- | ------------------------------------------------------------------------------ |
| `fresh_for`  | `timedelta(0)`          | 将缓存值视为 fresh 的时长。在此窗口期内，`swr` 直接返回缓存值，不进行重新验证。 |
| `max_age`    | `timedelta(days=1)`     | 缓存条目的最长生命周期。超过此期限后，`swr` 在返回之前会阻塞等待加载函数。上限为 1 天。 |

### 重新验证机制

| 缓存状态      | 条件                           | 行为                                                           |
| ------------- | ------------------------------ | -------------------------------------------------------------- |
| **Miss**      | 键不在缓存中                   | 等待 `loader()`，存储结果，并返回。                            |
| **Fresh**     | `age < fresh_for`              | 返回缓存值，不重新验证。                                       |
| **Stale**     | `fresh_for <= age < max_age`   | 立即返回缓存值，并触发后台刷新。                               |
| **Expired**   | `age >= max_age`               | 等待 `loader()`，存储结果，并返回。                            |

## 与 Pydantic 模型一起使用

传入 `model` 参数，自动序列化和反序列化 Pydantic 模型：

```python
from pydantic import BaseModel
from langgraph_sdk.cache import swr

class UserProfile(BaseModel):
    name: str
    email: str
    role: str

result = await swr(
    f"profile:{user_id}",
    lambda: fetch_profile(user_id),
    model=UserProfile,
)
profile: UserProfile = result.value  # 自动反序列化
```

`swr` 在存储前调用 `model_dump(mode="json")`，在读取时调用 `model.model_validate()`。

## 缓存认证凭据

您可以在自定义认证处理程序中缓存凭据验证结果，以避免每次请求都访问身份提供者：

```python
from datetime import timedelta
from langgraph_sdk import Auth
from langgraph_sdk.cache import swr

auth = Auth()

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    token = (headers.get(b"authorization") or b"").decode()
    if not token:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing token")

    result = await swr(
        f"auth:token:{token}",
        lambda: validate_and_fetch_user(token),
        fresh_for=timedelta(minutes=5),
        max_age=timedelta(hours=1),
    )
    return result.value
```

通过这种设置，服务器在 5 分钟内直接返回缓存用户信息而不重新验证，然后在最多 1 小时内进行后台重新验证。1 小时后，下一次请求会阻塞直到 `validate_and_fetch_user` 完成。

## 检查缓存状态

`swr` 返回一个带有值和缓存状态的 `SWRResult` 对象：

```python
result = await swr("my-key", my_loader)

result.value   # 缓存值或新加载的值
result.status  # "miss" | "fresh" | "stale" | "expired"
```

调用 `.mutate()` 来更新缓存值或强制重新验证：

```python
await result.mutate(new_value)  # 用新值更新缓存
await result.mutate()           # 通过调用加载函数强制重新验证
```

## 底层缓存 API

对于不需要重新验证的简单 get/set 缓存，可以直接使用 `cache_get` 和 `cache_set`：

```python
from datetime import timedelta
from langgraph_sdk.cache import cache_get, cache_set

value = await cache_get("my-key")

if value is None:
    value = await expensive_computation()
    await cache_set("my-key", value, ttl=timedelta(hours=1))
```

### `cache_get`

```python
async def cache_get(key: str) -> Any | None
```

返回反序列化后的值，如果键不存在或已过期则返回 `None`。

### `cache_set`

```python
async def cache_set(key: str, value: Any, *, ttl: timedelta | None = None) -> None
```

| 参数    | 类型                   | 默认值    | 描述                                                       |
| ------- | ---------------------- | --------- | ---------------------------------------------------------- |
| `key`   | `str`                  | 必需      | 缓存键                                                     |
| `value` | `Any`                  | 必需      | 要缓存的值，必须是可 JSON 序列化的                         |
| `ttl`   | `timedelta \| None`    | `None`    | 生存时间。服务器将其上限设为 1 天。`None` 或零默认使用 1 天 |

## 后续步骤

* 向您的部署添加自定义认证。
* 添加自定义生命周期事件，以便在服务器启动时初始化资源。
* 了解 agent server 架构。