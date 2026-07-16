# Database Integration

FastAPI works with any database library. The recommended stack is SQLModel (built on SQLAlchemy + Pydantic).

## SQLModel Setup

```python
from sqlmodel import Field, Session, SQLModel, create_engine, select

DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
```

## Table Model

```python
class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
```

## Session Dependency (Yield Pattern)

```python
from typing import Annotated
from fastapi import Depends

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
```

## CRUD Operations

```python
@app.post("/heroes/", response_model=HeroPublic)
def create_hero(hero: HeroCreate, session: SessionDep):
    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

@app.get("/heroes/", response_model=list[HeroPublic])
def read_heroes(
    session: SessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes

@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def read_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero

@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero_data = hero.model_dump(exclude_unset=True)
    db_hero.sqlmodel_update(hero_data)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}
```

## Key Rules

| Rule | Why |
|------|-----|
| Use `yield` for session lifecycle | Ensures session is closed after request |
| Always `commit()` after writes | Changes aren't persisted until committed |
| Use `refresh()` after commit | Syncs instance with DB-generated values (id, defaults) |
| Use `model_dump(exclude_unset=True)` for PATCH | Only updates fields the client sent |
| Separate table models from API models | `Hero` (table) vs `HeroCreate`/`HeroPublic`/`HeroUpdate` (API) |
| Use `select()` not raw SQL | Type-safe, Pydantic-compatible queries |

## Model Separation Pattern

```python
# Table model (database)
class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int | None = None

# API models
class HeroCreate(SQLModel):
    name: str
    secret_name: str
    age: int | None = None

class HeroUpdate(SQLModel):
    name: str | None = None
    secret_name: str | None = None
    age: int | None = None

class HeroPublic(SQLModel):
    id: int
    name: str
    age: int | None = None
    # Note: secret_name NOT included — filtered from responses
```

## Database URL per Environment

```python
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db"  # Default for development
)
```

## Testing with Separate Database

```python
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL)

def get_test_session():
    with Session(test_engine) as session:
        yield session

# In tests:
app.dependency_overrides[get_session] = get_test_session
```