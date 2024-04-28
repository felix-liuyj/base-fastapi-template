from aiokafka import AIOKafkaConsumer
from aiokafka.util import create_task

from app.config import get_settings

__all__ = (
    'BinaryOwlConsumer',
)


class BinaryOwlConsumer(AIOKafkaConsumer):
    def __init__(self):
        super().__init__(
            *get_settings().KAFKA_CLUSTER_TOPICS.split(','),
            bootstrap_servers=get_settings().KAFKA_CLUSTER_BROKERS,
            group_id=get_settings().KAFKA_CLUSTER_CONSUMER_GROUP
        )

    async def __aenter__(self):
        await super().__aenter__()
        create_task(self.consume())

    @staticmethod
    def check_exception(func):
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            finally:
                await self.stop()

        return wrapper

    @check_exception
    async def consume(self):
        async for msg in self:
            match msg.topic:
                case _:
                    print(f'consume: {msg.value}')
