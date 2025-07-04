from inspect import isclass

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings
from app.models import BaseDatabaseModel

__all__ = (
    'initialize_mongodb_client',
)


async def init_db(mongo_client: AsyncIOMotorClient):
    import app.models.account as user_models
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


async def initialize_mongodb_client() -> AsyncIOMotorClient:
    mongo_client = AsyncIOMotorClient(
        host=get_settings().MONGODB_URI,
        port=get_settings().MONGODB_PORT,
        username=get_settings().MONGODB_USERNAME,
        password=get_settings().MONGODB_PASSWORD,
        authSource=get_settings().MONGODB_AUTHENTICATION_SOURCE
    )
    await init_db(mongo_client)
    return mongo_client
