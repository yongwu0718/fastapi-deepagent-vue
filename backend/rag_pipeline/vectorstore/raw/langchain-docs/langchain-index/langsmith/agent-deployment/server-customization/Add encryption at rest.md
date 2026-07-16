# 添加静态加密

Agent Server 支持对 checkpoint 数据和元数据进行静态加密。您可以选择使用单密钥的基本加密，或针对高级用例使用自定义加密。

## 选择加密方法

| 方法                | 加密内容                                                     | 适用场景                                                                |
| --------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Basic encryption**  | Checkpoint blobs，可选 JSON 字段                 | 单一静态密钥，自动 AES 加密，选择性字段加密 |
| **Custom encryption** | Checkpoints、threads、runs、assistants、crons 和 stores | 多租户密钥，KMS 集成                                        |

## Basic encryption

对于使用单一静态密钥的简单加密，请设置 `LANGGRAPH_AES_KEY` 环境变量。LangGraph 将自动使用 AES 加密 checkpoint blob。

1. 在 `langgraph.json` 中将 `pycryptodome` 添加到依赖项：
   ```json
   {
     "dependencies": [".", "pycryptodome"],
     "graphs": {
       "agent": "./agent.py:graph"
     }
   }
   ```

2. 将 `LANGGRAPH_AES_KEY` 环境变量设置为 16、24 或 32 字节的密钥（分别对应 AES-128、AES-192 或 AES-256）。

### 加密 JSON 字段

要同时加密特定的 JSON 字段，请将 `LANGGRAPH_AES_JSON_KEYS` 设置为要加密的键的逗号分隔列表：

```bash
export LANGGRAPH_AES_KEY="your-16-24-or-32-byte-key"
export LANGGRAPH_AES_JSON_KEYS="api_key,secret_token,user_credentials"
```

这些键在 thread、assistant、run、cron 和 store 数据中出现的位置都会被加密。

加密字段无法被搜索或过滤。

系统字段不能被加密：`langgraph_version`、`langgraph_api_version`、`langgraph_plan`、`langgraph_host`、`langgraph_api_url`、`langgraph_request_id`、`langgraph_auth_user_id` 和 `langgraph_auth_permissions`。

## Custom encryption

需要 Agent Server 版本 0.6.22+ 和 Python SDK 版本 `langgraph-sdk>=0.3.1`。

Agent Server 版本 0.5.34–0.6.21 包含了一个预发布版本的自定义加密。使用这些版本加密的数据在升级到 0.6.22+ 时将会损坏。请勿在这些版本上使用自定义加密。

仅当基本加密不满足您的需求时才使用自定义加密。自定义加密要求您实现并维护加密处理程序，并增加运维复杂性。如果您只需要一个带有可选选择性字段加密的单一静态密钥，请改用基本加密。

在以下场景中使用自定义加密：

* **多租户密钥隔离** — 为不同客户使用不同的加密密钥
* **KMS 集成** — 用于密钥管理、轮换和审计日志的 AWS KMS、Google Cloud KMS 或 HashiCorp Vault

### 工作原理

1. 在 `langgraph.json` 中配置加密模块路径
2. 定义您的加密模块，包含用于 blob 和 JSON 加密的处理程序
3. 通过 `X-Encryption-Context` header 传递加密上下文（如租户 ID）
4. LangGraph 在存储数据之前和检索数据之后调用您的处理程序

对于具有密钥轮换和审计日志的生产部署，请参阅使用 AWS Encryption SDK 的信封加密。

### 配置

将您的加密模块添加到 `langgraph.json`：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  },
  "encryption": {
    "path": "./encryption.py:encryption"
  }
}
```

如果您从基本加密迁移，请保持 `LANGGRAPH_AES_KEY` 配置。自定义加密处理新的写入，而现有的 AES 加密数据仍然可读。

### 定义您的加密模块

#### Blob 加密（checkpoints）

Blob 处理程序加密 checkpoint 数据——即来自 graph 执行的序列化状态。以下是一个使用每个租户密钥的简化示例，使用了 Fernet（来自 `cryptography` 库的对称加密方案）：

```python
import os
from cryptography.fernet import Fernet
from langgraph_sdk import Encryption, EncryptionContext

encryption = Encryption()

# 在生产环境中，请从 secrets 管理器获取
TENANT_KEYS = {
    "tenant-a": Fernet(os.environ["TENANT_A_KEY"]),
    "tenant-b": Fernet(os.environ["TENANT_B_KEY"]),
}

def _get_fernet(ctx: EncryptionContext) -> Fernet:
    tenant_id = ctx.metadata.get("tenant_id")
    if not tenant_id or tenant_id not in TENANT_KEYS:
        raise ValueError(f"Unknown tenant: {tenant_id}")
    return TENANT_KEYS[tenant_id]

@encryption.encrypt.blob
async def encrypt_blob(ctx: EncryptionContext, data: bytes) -> bytes:
    return _get_fernet(ctx).encrypt(data)

@encryption.decrypt.blob
async def decrypt_blob(ctx: EncryptionContext, data: bytes) -> bytes:
    return _get_fernet(ctx).decrypt(data)
```

`ctx.metadata` 字典来自 `X-Encryption-Context` header，并与加密数据一起以明文存储，以便在解密时使用正确的密钥。

#### JSON 加密（元数据）

JSON 处理程序加密结构化数据，如 thread metadata、assistant context 和 run kwargs。与 blob 加密不同，您选择要加密的字段——保留一些未加密的字段用于搜索和过滤。

```python
import json
import os
from cryptography.fernet import Fernet
from langgraph_sdk import Encryption, EncryptionContext

encryption = Encryption()

TENANT_KEYS = {
    "tenant-a": Fernet(os.environ["TENANT_A_KEY"]),
    "tenant-b": Fernet(os.environ["TENANT_B_KEY"]),
}

SKIP_FIELDS = {
    "tenant_id", "owner",
    "run_id", "thread_id", "graph_id", "assistant_id", "user_id", "checkpoint_id",
    "source", "step", "parents", "run_attempt",
    "langgraph_version", "langgraph_api_version", "langgraph_plan", "langgraph_host",
    "langgraph_api_url", "langgraph_request_id", "langgraph_auth_user",
    "langgraph_auth_user_id", "langgraph_auth_permissions",
}
ENCRYPTED_PREFIX = "encrypted:"

def _get_fernet(ctx: EncryptionContext) -> Fernet:
    tenant_id = ctx.metadata.get("tenant_id")
    if not tenant_id or tenant_id not in TENANT_KEYS:
        raise ValueError(f"Unknown tenant: {tenant_id}")
    return TENANT_KEYS[tenant_id]

@encryption.encrypt.json
async def encrypt_json(ctx: EncryptionContext, data: dict) -> dict:
    fernet = _get_fernet(ctx)
    result = {}
    for k, v in data.items():
        if k in SKIP_FIELDS or v is None:
            result[k] = v
        else:
            value_json = json.dumps(v)
            encrypted = fernet.encrypt(value_json.encode()).decode()
            result[k] = ENCRYPTED_PREFIX + encrypted
    return result

@encryption.decrypt.json
async def decrypt_json(ctx: EncryptionContext, data: dict) -> dict:
    fernet = _get_fernet(ctx)
    result = {}
    for k, v in data.items():
        if isinstance(v, str) and v.startswith(ENCRYPTED_PREFIX):
            encrypted_value = v[len(ENCRYPTED_PREFIX):]
            decrypted = fernet.decrypt(encrypted_value.encode()).decode()
            result[k] = json.loads(decrypted)
        else:
            result[k] = v
    return result
```

#### JSON 加密注意事项

**加密字段无法被搜索或过滤。** 设计您的 metadata schema，使需要查询的字段保持未加密状态。

**JSON encryptors 必须保留键结构。** SQL JSONB 合并操作在键级别进行。改变键的 encryptor——无论是通过合并字段（例如，将敏感数据移动到 `__encrypted__` 中）还是加密键名本身——都会在合并期间导致数据丢失。请使用 per-key 加密：就地转换值，同时保留键。

**迁移考虑：** 在加密值中使用可识别的前缀或格式，以便您的解密器能够检测并跳过未加密的数据。这允许您将来加密其他字段而无需重新加密现有记录。上面的示例使用了这种模式。

**性能考虑：** per-key 加密意味着每个字段一次加密调用。如果您的加密涉及往返外部服务（例如 KMS），这会显著影响延迟。考虑在本地缓存数据密钥，或使用信封加密：用 KMS 加密本地数据密钥，然后将其用于多个字段。

用于授权的用户定义字段（例如 `tenant_id`、`owner`）通常应保持**未加密**，用于搜索和过滤的字段也应如此。此外，**某些系统管理的字段将永远不会被加密**：

* 资源标识符（`thread_id`、`run_id`、`assistant_id`、`graph_id`、`checkpoint_id`、`task_id`）
* 大多数以 `langgraph_` 开头的字段（`langgraph_auth_user` 除外）
* 必需的 checkpoint metadata（`source`、`step`、`parents`、`run_attempt`）
* 用于调度和编排的内部字段（`__after_seconds__`、`__request_start_time_ms__`、大多数以 `__pregel` 开头的字段）
* 在 run 的 `config` 中指定的 run 级执行限制（`max_concurrency`、`recursion_limit`）
* 在 run 的 `config.configurable` 中指定的 thread TTL 更新（`ttl`）

#### 加密的内容

**JSON 处理程序**（`@encryption.encrypt.json` / `@encryption.decrypt.json`）递归应用于以下字段：

* `thread.metadata`、`thread.values`
* `assistant.metadata`、`assistant.context`
* `run.metadata`、`run.kwargs`
* `cron.metadata`、`cron.payload`
* `store.value`

某些字段被排除在加密之外。除非另有说明，这些排除适用于嵌套 JSON 对象的每一级，而不仅仅是根级。

**Blob 处理程序**（`@encryption.encrypt.blob` / `@encryption.decrypt.blob`）应用于 checkpoint blob（graph 执行状态）。

#### 从认证上下文中派生加密上下文

不显式传递 `X-Encryption-Context`，而是从已认证的用户派生加密上下文：

```python
from langgraph_sdk import Encryption, EncryptionContext
from starlette.authentication import BaseUser

encryption = Encryption()

@encryption.context
async def get_encryption_context(user: BaseUser, ctx: EncryptionContext) -> dict:
    return {
        **ctx.metadata,
        "tenant_id": user["tenant_id"],
    }
```

该处理程序在每次请求认证后运行一次。返回的字典成为该请求中所有加密操作的 `ctx.metadata`。

### 传递加密上下文

通过 `X-Encryption-Context` header 传递加密上下文。上下文是您定义的任意数据——您控制 schema，可以包含您的加密逻辑需要的任何字段（例如 `tenant_id`、`key_version`）。该上下文在处理程序中可作为 `ctx.metadata` 使用，并以明文存储以便在解密期间使用。

```python
import base64
import json
from langgraph_sdk import get_client

encryption_context = base64.b64encode(
    json.dumps({"tenant_id": "tenant-a"}).encode()
).decode()

client = get_client(url="http://localhost:2024")

result = await client.runs.wait(
    thread_id=None,
    assistant_id="agent",
    input={"messages": [{"role": "user", "content": "Hello"}]},
    headers={"X-Encryption-Context": encryption_context},
)
```

加密上下文以明文存储。在解密时，它会自动恢复——调用者在读取时不需要传递该 header。

### 使用 AWS Encryption SDK 进行信封加密

对于 AWS 上的生产部署，请使用 AWS Encryption SDK 配合 AWS KMS，或您在云提供商内的等效方案。这种方法：

* 自动处理信封加密（无需手动打包密钥）
* 提供密钥轮换和审计日志
* 将密文与加密上下文绑定（租户隔离）
* 在本地缓存数据密钥以避免重复的 KMS 调用、延迟和速率限制

#### 完整示例

```python
import base64
import json
import os

import aws_encryption_sdk
from aws_encryption_sdk import (
    CachingCryptoMaterialsManager,
    CommitmentPolicy,
    LocalCryptoMaterialsCache,
    StrictAwsKmsMasterKeyProvider,
)
from langgraph_sdk import Encryption, EncryptionContext

encryption = Encryption()

# SDK 使用信封加密：一次 KMS API 调用生成一个数据密钥，
# 然后在本地进行加密/解密。缓存跨操作复用数据密钥。
client = aws_encryption_sdk.EncryptionSDKClient(
    commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_REQUIRE_DECRYPT
)
key_provider = StrictAwsKmsMasterKeyProvider(key_ids=[os.environ["KMS_KEY_ARN"]])
cache = LocalCryptoMaterialsCache(capacity=100)
cmm = CachingCryptoMaterialsManager(
    master_key_provider=key_provider,
    cache=cache,
    max_age=300.0,
    max_messages_encrypted=100,
)

SKIP_FIELDS = {
    "tenant_id", "owner",
    "run_id", "thread_id", "graph_id", "assistant_id", "user_id", "checkpoint_id",
    "source", "step", "parents", "run_attempt",
    "langgraph_version", "langgraph_api_version", "langgraph_plan", "langgraph_host",
    "langgraph_api_url", "langgraph_request_id", "langgraph_auth_user",
    "langgraph_auth_user_id", "langgraph_auth_permissions",
}
ENCRYPTED_PREFIX = "encrypted:"

@encryption.encrypt.blob
async def encrypt_blob(ctx: EncryptionContext, data: bytes) -> bytes:
    ciphertext, _ = client.encrypt(
        source=data,
        materials_manager=cmm,
        encryption_context={"tenant_id": ctx.metadata["tenant_id"]},
    )
    return ciphertext

@encryption.decrypt.blob
async def decrypt_blob(ctx: EncryptionContext, data: bytes) -> bytes:
    plaintext, _ = client.decrypt(source=data, key_provider=key_provider)
    return plaintext

@encryption.encrypt.json
async def encrypt_json(ctx: EncryptionContext, data: dict) -> dict:
    tenant_id = ctx.metadata["tenant_id"]
    result = {}
    for k, v in data.items():
        if k in SKIP_FIELDS or v is None:
            result[k] = v
        else:
            ciphertext, _ = client.encrypt(
                source=json.dumps(v).encode(),
                materials_manager=cmm,
                encryption_context={"tenant_id": tenant_id},
            )
            result[k] = ENCRYPTED_PREFIX + base64.b64encode(ciphertext).decode()
    return result

@encryption.decrypt.json
async def decrypt_json(ctx: EncryptionContext, data: dict) -> dict:
    result = {}
    for k, v in data.items():
        if isinstance(v, str) and v.startswith(ENCRYPTED_PREFIX):
            ciphertext = base64.b64decode(v[len(ENCRYPTED_PREFIX):])
            plaintext, _ = client.decrypt(source=ciphertext, key_provider=key_provider)
            result[k] = json.loads(plaintext.decode())
        else:
            result[k] = v
    return result
```

`encryption_context` 通过 KMS 以加密方式绑定到密文——如果上下文不匹配，解密将失败。该上下文嵌入在密文中，因此解密处理程序不需要引用 `ctx.metadata`。

#### 密钥轮换

KMS 自动处理主密钥轮换。当您在 KMS 密钥上启用自动轮换时，旧的加密数据密钥仍然可以解密，而新操作使用轮换后的密钥材料。无需重新加密现有数据。

## 相关内容

* 自定义认证