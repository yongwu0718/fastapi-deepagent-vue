# Base64 Bytes in JSON

Handle `bytes` fields in JSON requests/responses using Base64 encoding.

## The Problem

JSON doesn't support raw binary data. When you have `bytes` fields in Pydantic models, they need special handling for JSON serialization.

## Using `bytes` with Base64

Pydantic automatically handles `bytes` as Base64-encoded strings in JSON:

```python
from pydantic import BaseModel

class FileData(BaseModel):
    name: str
    content: bytes  # Automatically Base64-encoded in JSON

# Request body (JSON):
# {"name": "hello.txt", "content": "SGVsbG8gV29ybGQ="}

# In Python, content is raw bytes:
# file_data.content == b"Hello World"
```

## Example

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class BinaryData(BaseModel):
    name: str
    data: bytes

@app.post("/upload/")
async def upload_binary(payload: BinaryData):
    return {
        "name": payload.name,
        "size": len(payload.data),
    }
```

Request:
```json
{
    "name": "config.json",
    "data": "eyJrZXkiOiAidmFsdWUifQ=="
}
```

## Key Rules

- Pydantic automatically decodes Base64 strings to `bytes` on input and encodes `bytes` to Base64 strings on output.
- The OpenAPI schema will document the field as `type: string, format: binary`.
- This works out of the box — no extra configuration needed.

## When to Use

- Transmitting small binary data (signatures, hashes, small files) in JSON.
- Not suitable for large files — use `UploadFile` with `multipart/form-data` instead.

## Alternative: UploadFile for Large Files

For large binary files, prefer `UploadFile`:

```python
from fastapi import File, UploadFile

@app.post("/files/")
async def upload_file(file: UploadFile):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}
```