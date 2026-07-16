# 测试事件：lifespan 和 startup - shutdown

当你需要在测试中运行 `lifespan` 时，可以将 `TestClient` 与 `with` 语句一起使用：
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

items = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    items["foo"] = {"name": "Fighters"}
    items["bar"] = {"name": "Tenders"}
    yield
    # clean up items
    items.clear()

app = FastAPI(lifespan=lifespan)

@app.get("/items/{item_id}")
async def read_items(item_id: str):
    return items[item_id]

def test_read_items():
    # Before the lifespan starts, "items" is still empty
    assert items == {}

    with TestClient(app) as client:
        # Inside the "with TestClient" block, the lifespan starts and items added
        assert items == {"foo": {"name": "Fighters"}, "bar": {"name": "Tenders"}}

        response = client.get("/items/foo")
        assert response.status_code == 200
        assert response.json() == {"name": "Fighters"}

        # After the requests is done, the items are still there
        assert items == {"foo": {"name": "Fighters"}, "bar": {"name": "Tenders"}}

    # The end of the "with TestClient" block simulates terminating the app, so
    # the lifespan ends and items are cleaned up
    assert items == {}
```

你可以在官方 Starlette 文档站点的“在测试中运行 lifespan”阅读更多细节。

对于已弃用的 `startup` 和 `shutdown` 事件，可以按如下方式使用 `TestClient`：
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

items = {}


@app.on_event("startup")
async def startup_event():
    items["foo"] = {"name": "Fighters"}
    items["bar"] = {"name": "Tenders"}


@app.get("/items/{item_id}")
async def read_items(item_id: str):
    return items[item_id]


def test_read_items():
    with TestClient(app) as client:
        response = client.get("/items/foo")
        assert response.status_code == 200
        assert response.json() == {"name": "Fighters"}
```