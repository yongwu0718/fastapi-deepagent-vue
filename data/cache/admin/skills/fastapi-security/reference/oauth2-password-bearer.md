---
title: OAuth2 Password + Bearer Token (Minimal)
impact: MEDIUM
impactDescription: Simplest working OAuth2 authentication pattern — good for learning and small projects, but use JWT for production
type: pattern
tags: [fastapi, security, oauth2, password, bearer, minimal]
---

# OAuth2 Password + Bearer Token (Minimal)

**Pattern: Starter** - A minimal OAuth2 implementation without JWT or password hashing. Good for understanding the flow, but not production-ready.

## Complete Minimal Example

```python
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fake user DB
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}

def fake_hash_password(password: str):
    return "fakehashed" + password

def get_user(db, username: str):
    if username in db:
        return db[username]
    return None

def fake_decode_token(token):
    # This doesn't provide any security at all
    # In production, use JWT.decode()
    user = get_user(fake_users_db, token)
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    if current_user["disabled"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=400, detail="Incorrect username or password"
        )
    user = get_user(fake_users_db, form_data.username)
    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == user["hashed_password"]:
        raise HTTPException(
            status_code=400, detail="Incorrect username or password"
        )
    return {"access_token": user["username"], "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[dict, Depends(get_current_active_user)],
):
    return current_user
```

## How It Works

1. `POST /token` with `username` + `password` → returns `{"access_token": ".", "token_type": "bearer"}`
2. Client includes `Authorization: Bearer <token>` in subsequent requests
3. `OAuth2PasswordBearer` extracts token from header
4. `get_current_user` dependency validates token and returns user

## Upgrade Path to JWT

Replace `fake_decode_token` with real JWT verification (see [jwt-password-hashing](jwt-password-hashing.md)):
- Add `python-jose[cryptography]` for JWT
- Add `passlib[bcrypt]` for password hashing
- Replace fake hash with bcrypt
- Add token expiration