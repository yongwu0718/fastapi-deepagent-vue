# 服务器运维

```bash
.venv\Scripts\activate;cd backend; fastapi dev
```

```bash
cd frontend;  npm run dev   
``` 

```bash
cd F:\index_rag\frontend; npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/api/client
```
## LangGraph 本地服务器

```bash
langgraph dev
```

## Chroma 数据库

启动本地 Chroma 服务：

```bash
.venv\Scripts\activate; python F:\index_rag\view_db\start_chroma_server.py
```

可视化 Chroma 数据库：

```bash
.venv\Scripts\activate; python -m streamlit run F:\index_rag\view_db\view_chroma.py
```

## FastAPI 后端

```bash
.venv\Scripts\activate;cd backend; fastapi dev
```

```bash
.venv\Scripts\activate; cd F:\index_rag\tools\fast-api; fastapi dev
```

## Streamlit

```bash
.venv\Scripts\activate; streamlit run API-agent/backend/sql/view_sql.py
```

## 前端 (npm)

```bash
cd frontend;  npm run dev   
``` 
