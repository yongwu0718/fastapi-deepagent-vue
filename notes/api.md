# API 客户端 & 终端交互

## 删除 LangGraph 线程

```bash
curl.exe -X DELETE "http://127.0.0.1:2024/threads/<thread-id>"
```

## 生成 OpenAPI 客户端 SDK

```bash
npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/api/client
```

或者在指定项目目录下执行：

```bash
cd F:\index_rag\frontend; npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/api/client
```

## 终端运行（PYTHONPATH）

交互模式：

```bash
.venv\Scripts\activate
python f:/index_rag/API-agent/backend/cli/interact.py
```

获取消息历史：

```bash
.venv\Scripts\activate
$env:PYTHONPATH = "f:/index_rag/API-agent"
python f:/index_rag/API-agent/backend/cli/get_message_history.py
```
