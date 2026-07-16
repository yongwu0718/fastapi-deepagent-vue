# FastAPI 高级指南 — 索引

> 本索引覆盖 FastAPI 进阶用户指南的全部章节，建立在初级指南基础之上，适合在掌握基本用法后按需查阅。

---

## 一、高级 Python 类型

| 文档 | 说明 |
|------|------|
| [高级 Python 类型](./高级%20Python%20类型.md) | Union、Optional、泛型、类型别名等高级类型注解技巧 |

---

## 二、响应进阶

| 文档 | 说明 |
|------|------|
| [直接返回响应](./直接返回响应.md) | 直接返回 `JSONResponse`、`HTMLResponse` 等 Response 对象 |
| [自定义响应 - HTML、流、文件等](./自定义响应%20-%20HTML、流、文件等.md) | 使用不同类型的 Response：HTML、Streaming、File、Redirect 等 |
| [响应 - 更改状态码](./响应%20-%20更改状态码.md) | 在响应返回前动态修改 HTTP 状态码 |
| [响应Cookies](./响应Cookies.md) | 在响应中设置和删除 Cookies |
| [响应头](./响应头.md) | 在响应中添加和设置自定义 HTTP 响应头 |
| [额外的状态码](./额外的状态码.md) | 使用多个状态码标记同一路径操作的可能响应 |
| [OpenAPI 中的附加响应](./OpenAPI%20中的附加响应.md) | 在 OpenAPI 文档中声明额外的响应模型和状态码 |

---

## 三、路径操作进阶

| 文档 | 说明 |
|------|------|
| [路径操作的高级配置](./路径操作的高级配置.md) | 配置 operation_id、openapi_extra、include_in_schema 等高级选项 |

---

## 四、依赖项进阶

| 文档 | 说明 |
|------|------|
| [高级依赖项](./高级依赖项.md) | 参数化依赖项、可调用实例、依赖项中的 yield 高级用法 |
| [使用覆盖测试依赖项](./使用覆盖测试依赖项.md) | 在测试中覆盖/替换依赖项以模拟外部服务 |

---

## 五、安全性进阶

| 文档 | 说明 |
|------|------|
| [HTTP 基础授权](./HTTP%20基础授权.md) | 实现 HTTP Basic Authentication |
| [OAuth2 作用域](./OAuth2%20作用域.md) | 使用 OAuth2 Scopes 实现细粒度权限控制 |

---

## 六、中间件进阶

| 文档 | 说明 |
|------|------|
| [高级中间件](./高级中间件.md) | 自定义中间件实现细节、ASGI 中间件的添加方式 |
| [严格的 Content-Type 检查](./严格的%20Content-Type%20检查.md) | 收紧服务端对请求 Content-Type 的校验策略 |

---

## 七、WebSocket 与流式数据

| 文档 | 说明 |
|------|------|
| [WebSockets](./WebSockets.md) | 在 FastAPI 中创建 WebSocket 端点，实现双向持久通信 |
| [流式数据](./流式数据.md) | 使用 `StreamingResponse` 流式传输大数据/实时数据 |

---

## 八、事件与生命周期

| 文档 | 说明 |
|------|------|
| [生命周期事件](./生命周期事件.md) | 使用 lifespan 管理应用启动/关闭时的资源初始化和释放 |
| [测试事件：lifespan 和 startup - shutdown](./测试事件：lifespan%20和%20startup%20-%20shutdown.md) | 测试包含生命周期事件的应用 |

---

## 九、应用架构

| 文档 | 说明 |
|------|------|
| [子应用 - 挂载](./子应用%20-%20挂载.md) | 将独立 FastAPI 应用挂载到主应用的子路径，各自拥有独立文档 |
| [包含 WSGI - Flask，Django，其它](./包含%20WSGI%20-%20Flask，Django，其它.md) | 将 Flask、Django 等 WSGI 应用嵌入 FastAPI |
| [使用代理](./使用代理.md) | 配置 FastAPI 在反向代理（Nginx、Traefik 等）后正确运行 |

---

## 十、OpenAPI 进阶

| 文档 | 说明 |
|------|------|
| [OpenAPI 网络钩子](./OpenAPI%20网络钩子.md) | 在 OpenAPI 文档中声明 Webhook，用于事件回调通知 |
| [OpenAPI 回调](./OpenAPI%20回调.md) | 在 OpenAPI Schema 中声明回调 URL，让外部服务调回你的 API |
| [生成 SDK](./生成%20SDK.md) | 基于 OpenAPI 为前端/第三方自动生成客户端 SDK |

---

## 十一、数据类型与编码

| 文档 | 说明 |
|------|------|
| [使用数据类](./使用数据类.md) | 使用标准库 `dataclass` 替代 Pydantic 模型声明请求/响应数据 |
| [在 JSON 中使用 Base64 表示字节](./在%20JSON%20中使用%20Base64%20表示字节.md) | 在 JSON 序列化中通过 Base64 编码处理 bytes 类型 |

---

## 十二、直接使用底层对象

| 文档 | 说明 |
|------|------|
| [直接使用 Request](./直接使用%20Request.md) | 直接在路径操作中获取和使用 Starlette `Request` 对象 |

---

## 十三、测试进阶

| 文档 | 说明 |
|------|------|
| [异步测试](./异步测试.md) | 使用 `httpx.AsyncClient` 编写异步 API 测试 |
| [测试 WebSockets](./测试%20WebSockets.md) | 使用 TestClient 测试 WebSocket 端点 |

---

## 十四、其他高级特性

| 文档 | 说明 |
|------|------|
| [模板](./模板.md) | 使用 Jinja2 模板引擎渲染 HTML 页面 |
| [设置和环境变量](./设置和环境变量.md) | 使用 Pydantic Settings 管理应用配置和环境变量 |

---

## 推荐学习路径

1. **[高级 Python 类型](./高级%20Python%20类型.md)** → 掌握类型提示高级用法
2. **[自定义响应](./自定义响应%20-%20HTML、流、文件等.md)** → **[响应Cookies](./响应Cookies.md)** → **[响应头](./响应头.md)**
3. **[高级依赖项](./高级依赖项.md)** → **[使用覆盖测试依赖项](./使用覆盖测试依赖项.md)**
4. **[生命周期事件](./生命周期事件.md)** → **[测试事件](./测试事件：lifespan%20和%20startup%20-%20shutdown.md)**
5. **[WebSockets](./WebSockets.md)** → **[测试 WebSockets](./测试%20WebSockets.md)** → **[流式数据](./流式数据.md)**
6. **[子应用 - 挂载](./子应用%20-%20挂载.md)** → **[包含 WSGI](./包含%20WSGI%20-%20Flask，Django，其它.md)** → **[使用代理](./使用代理.md)**
7. **[OAuth2 作用域](./OAuth2%20作用域.md)** → **[HTTP 基础授权](./HTTP%20基础授权.md)**
8. **[模板](./模板.md)** → **[设置和环境变量](./设置和环境变量.md)** → **[生成 SDK](./生成%20SDK.md)**