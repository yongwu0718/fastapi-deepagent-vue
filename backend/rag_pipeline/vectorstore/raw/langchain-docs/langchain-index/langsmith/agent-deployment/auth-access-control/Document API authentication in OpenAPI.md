# 在 OpenAPI 中记录 API 认证

本指南介绍如何为您的 LangSmith API 文档自定义 OpenAPI 安全模式。一个记录良好的安全模式有助于 API 使用者理解如何通过您的 API 进行认证，甚至可以启用自动客户端生成。有关 LangGraph 认证系统的更多详细信息，请参阅认证与访问控制概念指南。

**实现与文档**
本指南仅涵盖如何在 OpenAPI 中记录您的安全要求。要实现实际的认证逻辑，请参阅如何添加自定义认证。

本指南适用于所有 LangSmith 部署（云和自托管）。如果您不使用 LangSmith，则不适用于 LangGraph 开源库的使用。

## 默认模式

默认安全方案因部署类型而异：

默认情况下，LangSmith 需要在 `x-api-key` header 中提供 LangSmith API 密钥：

```yaml
components:
  securitySchemes:
    apiKeyAuth:
      type: apiKey
      in: header
      name: x-api-key
security:
  - apiKeyAuth: []
```

当使用 LangGraph SDK 时，可以从环境变量中推断这一点。

默认情况下，自托管部署没有安全方案。这意味着它们只能在受保护的网络上部署或使用认证。要添加自定义认证，请参阅如何添加自定义认证。

## 自定义安全模式

要在您的 OpenAPI 文档中自定义安全模式，请在 `langgraph.json` 中的 `auth` 配置中添加一个 `openapi` 字段。请记住，这只会更新 API 文档——您还必须实现相应的认证逻辑，如如何添加自定义认证中所示。

请注意，LangSmith 不提供认证端点——您需要在客户端应用中处理用户认证，并将生成的凭据传递给 LangGraph API。

```json
{
  "auth": {
    "path": "./auth.py:my_auth",  // 在此处实现认证逻辑
    "openapi": {
      "securitySchemes": {
        "OAuth2": {
          "type": "oauth2",
          "flows": {
            "implicit": {
              "authorizationUrl": "https://your-auth-server.com/oauth/authorize",
              "scopes": {
                "me": "Read information about the current user",
                "threads": "Access to create and manage threads"
              }
            }
          }
        }
      },
      "security": [
        {"OAuth2": ["me", "threads"]}
      ]
    }
  }
}
```

## 测试

更新配置后：

1. 部署您的应用
2. 访问 `/docs` 以查看更新后的 OpenAPI 文档
3. 使用来自认证服务器的凭据试用端点（请确保首先已实现认证逻辑）