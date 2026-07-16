# Extra Data Types

Beyond `int`, `float`, `str`, and `bool`, FastAPI supports many additional Pydantic data types with automatic validation, serialization, and documentation.

## Supported Types

| Type | Request Format | Response Format |
|---|---|---|
| `UUID` | `str` | `str` |
| `datetime.datetime` | ISO 8601 `str` | ISO 8601 `str` |
| `datetime.date` | ISO 8601 `str` | ISO 8601 `str` |
| `datetime.time` | ISO 8601 `str` | ISO 8601 `str` |
| `datetime.timedelta` | `float` (seconds) | `float` (seconds) |
| `Decimal` | `float` | `float` |
| `frozenset` | `list` (deduplicated) | `list` (uniqueItems) |
| `bytes` | `str` (binary format) | `str` (binary format) |

## Example

```python
from datetime import datetime, time, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Body, FastAPI

app = FastAPI()

@app.put("/items/{item_id}")
async def read_items(
    item_id: UUID,
    start_datetime: Annotated[datetime, Body()],
    end_datetime: Annotated[datetime, Body()],
    process_after: Annotated[timedelta, Body()],
    repeat_at: Annotated[time | None, Body()] = None,
):
    start_process = start_datetime + process_after
    duration = end_datetime - start_process
    return {
        "item_id": item_id,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "process_after": process_after,
        "repeat_at": repeat_at,
        "start_process": start_process,
        "duration": duration,
    }
```

## Key Rules

- All types are validated automatically — an invalid UUID string will return a 422 error.
- You can use native Python operations on the parsed values (e.g., `datetime` arithmetic).
- For a full list of supported types, see [Pydantic data types](https://docs.pydantic.dev/latest/concepts/types/).

## Common Patterns

### UUID as primary key

```python
from uuid import UUID

@app.get("/users/{user_id}")
async def get_user(user_id: UUID):
    # user_id is automatically parsed and validated
    return {"user_id": user_id}
```

### Decimal for precise financial values

```python
from decimal import Decimal

class Invoice(BaseModel):
    amount: Decimal
    tax_rate: Decimal
```

### datetime with timezone

```python
from datetime import datetime

class Event(BaseModel):
    starts_at: datetime
    # ISO 8601 string in request: "2025-01-01T12:00:00+05:00"
```