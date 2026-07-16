# Form Data and File Uploads

FastAPI handles form data and file uploads with `Form`, `File`, and `UploadFile`.

## Form Data

Install `python-multipart` first:

```bash
pip install python-multipart
```

```python
from fastapi import Form

@app.post("/login/")
async def login(username: str = Form(), password: str = Form()):
    return {"username": username}
```

### Form with Pydantic Model

```python
from pydantic import BaseModel

class LoginForm(BaseModel):
    username: str
    password: str
    remember_me: bool = False

@app.post("/login/")
async def login(form_data: LoginForm = Form()):
    return {"username": form_data.username}
```

## File Uploads

### Single File

```python
from fastapi import UploadFile

@app.post("/upload/")
async def upload_file(file: UploadFile):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}
```

### Multiple Files

```python
@app.post("/upload-multiple/")
async def upload_files(files: list[UploadFile]):
    return {"filenames": [f.filename for f in files]}
```

### Save Uploaded File

```python
@app.post("/upload/")
async def upload_file(file: UploadFile):
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"file_path": file_path}
```

### `UploadFile` vs `bytes`

| Feature | `UploadFile` | `bytes` |
|---------|-------------|---------|
| Memory usage | Stored on disk (spooled) | All in memory |
| Large files | OK | Will exhaust memory |
| Methods | `read()`, `write()`, `seek()`, `filename` | Just the bytes |
| Async | `await file.read()` | N/A |

**Always use `UploadFile` for file uploads.**

## Form + File Together

```python
@app.post("/submit/")
async def submit_form(
    name: str = Form(),
    description: str = Form(),
    file: UploadFile = File(),
):
    return {
        "name": name,
        "description": description,
        "filename": file.filename,
    }
```

## Key Rules

- Form data and file uploads require `python-multipart`.
- `Form()` and `File()` parameters are required by default; use `None` default for optional.
- Use `UploadFile` (not `bytes`) for file uploads — it handles large files properly.
- Form fields and file fields cannot be mixed with JSON body in the same request.
- Use `UploadFile` attributes: `file.filename`, `file.content_type`, `file.size`.