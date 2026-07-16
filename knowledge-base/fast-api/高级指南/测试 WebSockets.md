# 测试 WebSockets

你可以使用同一个 `TestClient` 来测试 WebSockets。

为此，在 `with` 语句中使用 `TestClient` 连接到 WebSocket：
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

app = FastAPI()

@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})
    await websocket.close()

def test_read_main():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}

def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}
```

注意

更多细节请查看 Starlette 的文档：测试 WebSockets。