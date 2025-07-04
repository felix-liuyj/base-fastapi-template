from inspect import isclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field
from sqlmodel import SQLModel, select

from app.config import get_settings

__all__ = (
    'BaseDatabaseModel',
    'User',
    'get_session',
    'initialize_database',
)
settings = get_settings()
DATABASE_URL = (
    f"mysql+asyncmy://{settings.MYSQL_USERNAME}:{settings.MYSQL_PASSWORD}"
    f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


def load_models_class(module):
    class_list = []
    for model in module.__all__:
        module_class = getattr(module, model)
        if (
                module_class
                and isclass(module_class)
                and issubclass(module_class, BaseDatabaseModel)
        ):
            class_list.append(module_class)
    return class_list


async def test_models_class(model_classes):
    async with async_session() as session:
        for model in model_classes:
            stmt = select(model).limit(1)
            await session.execute(stmt)
            print(f"{model.__name__} test passed")


async def initialize_database():
    import app.models.account as user_models

    model_classes = [
        *load_models_class(user_models),
    ]

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    print("Database Test...")
    await test_models_class(model_classes)
    print("Database Init Complete", end="\n\n")


class BaseDatabaseModel(SQLModel):
    pass


class User(BaseDatabaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
