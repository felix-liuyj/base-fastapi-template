from datetime import datetime
from inspect import isclass
from typing import Any, ClassVar, Iterable

from beanie import Document, Update, after_event
from beanie import init_beanie
from beanie.odm.operators.update.general import Set as _Set
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import Field, model_validator

from app.config import get_settings
from app.libs.custom import encrypt, decrypt, update_dict_value_recursively

__all__ = (
    'Set',
    'BaseDatabaseModel',
    'initialize_database',
)


class Set(_Set):
    def __init__(self, expression):
        super().__init__(expression | {'updatedAt': datetime.now()})


class BaseDatabaseModel(Document):
    # 子类只需在此列出需要加密的字段名
    __encrypted_fields__: ClassVar[Iterable[str]] = []

    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    def keys(self):
        return list(self.model_fields.keys())

    def __getitem__(self, item):
        return getattr(self, item) if item != 'id' else str(self.id)

    @property
    def sid(self) -> str:
        return str(self.id)

    @after_event(Update)
    async def refresh_update_at(self):
        self.updatedAt = datetime.now()

    async def update_fields(self, encrypt_fields: dict = None, **kwargs):
        if encrypt_fields and isinstance(encrypt_fields, dict):
            kwargs.update({key: encrypt(val, get_settings().ENCRYPT_KEY) for key, val in encrypt_fields.items()})

        kwargs.update(updatedAt=datetime.now())
        return await self.set(kwargs)

    async def get_encrypted_fields(self, encrypted_field: str) -> Any | None:
        if not getattr(self, encrypted_field):
            return None
        return decrypt(getattr(self, encrypted_field), get_settings().ENCRYPT_KEY)

    @model_validator(mode='before')
    def decrypt_model_data(cls, values: dict) -> str:
        for field in cls.__encrypted_fields__:
            update_dict_value_recursively(
                values, field,
                func=lambda x: decrypt(x, get_settings().ENCRYPT_KEY) if x and x.startswith('gAAAA') else None
            )
        return values


async def test_models_class(module):
    for model in module:
        await model.find().to_list()
        print(f'{model.__name__} test passed')


def load_models_class(module):
    class_list = []
    for model in module.__all__:
        module_class = getattr(module, model)
        if module_class and isclass(module_class) and issubclass(module_class, BaseDatabaseModel):
            class_list.append(module_class)

    return class_list


async def initialize_database() -> AsyncIOMotorClient:
    import app.models.account as user_models

    mongo_client = AsyncIOMotorClient(
        host=get_settings().MONGODB_URI,
        port=get_settings().MONGODB_PORT,
        username=get_settings().MONGODB_USERNAME,
        password=get_settings().MONGODB_PASSWORD,
        authSource=get_settings().MONGODB_AUTHENTICATION_SOURCE
    )
    model_classes = [
        *load_models_class(user_models),
    ]
    await init_beanie(
        database=getattr(mongo_client, get_settings().MONGODB_DB),
        document_models=model_classes
    )
    print('Database Test...')
    await test_models_class(model_classes)
    print('Database Init Complete', end='\n\n')
    return mongo_client
