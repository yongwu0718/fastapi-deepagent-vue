---
title: Full JWT + Password Hashing Authentication
impact: HIGH
impactDescription: The complete recommended pattern for JWT-based authentication with bcrypt password hashing in FastAPI
type: pattern
tags: [fastapi, security, jwt, oauth2, bcrypt, passlib]
---

# Full JWT + Password Hashing Authentication

**Pattern: Recommended** - This is the standard production-ready authentication setup for FastAPI applications using JWT tokens.

## Dependencies

```
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
```

## Complete Implementation

### 1. Configuration

```python
# config.py
from datetime import timedelta

SECRET_KEY = "your-secret-key-keep-it-secret"  # Use env var in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

### 2. Password Hashing

```python
# auth.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

### 3. User Model & DB (SQLModel)

```python
# models.py
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str | None = None
    full_name: str | None = None
    hashed_password: str
    disabled: bool = False
```

### 4. Token Creation & Verification

```python
# auth.py (continued)
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

### 5. OAuth2 Scheme & User Dependency

```python
# dependencies.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

### 6. Login Endpoint

```python
# main.py
from fastapi.security import OAuth2PasswordRequestForm

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

### 7. Protected Route

```python
@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user
```

## Key Rules

| Rule | Why |
|------|-----|
| Never store plain-text passwords | Always hash with bcrypt |
| Always include `WWW-Authenticate` header on 401 | Required by HTTP spec for Bearer auth |
| Set token expiration (`exp` claim) | Limits damage if token is leaked |
| Use `sub` claim for user identifier | JWT standard; typically username or user ID |
| Keep `SECRET_KEY` in environment variables | Never commit to version control |
| Use separate models for user input vs output | `UserIn` (password) vs `UserOut` (no password) vs `UserDB` (hashed_password) |