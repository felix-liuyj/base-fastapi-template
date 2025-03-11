import pathlib
import ssl

from aiokafka import AIOKafkaConsumer
from aiokafka.util import create_task

from app.config import get_settings

__all__ = (
    'BaseConsumer',
)


class BaseConsumer(AIOKafkaConsumer):
    def __init__(self):
        super().__init__(
            *get_settings().KAFKA_CLUSTER_TOPICS.split(','),
            bootstrap_servers=get_settings().KAFKA_CLUSTER_BROKERS,
            group_id=get_settings().KAFKA_CLUSTER_CONSUMER_GROUP,
            security_protocol='SASL_SSL', sasl_mechanism='PLAIN',
            sasl_plain_username=get_settings().KAFKA_CLUSTER_SASL_USERNAME,
            sasl_plain_password=get_settings().KAFKA_CLUSTER_SASL_PASSWORD,
            ssl_context=self.load_ssl_context()
        )

    async def __aenter__(self):
        await super().__aenter__()
        create_task(self.consume())

    @staticmethod
    def load_ssl_context() -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False
        context.load_verify_locations(
            f'{pathlib.Path(__file__).resolve().parent.parent.parent}/statics/certs/mix-4096-ca-cert.pem'
        )
        return context

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
