from datetime import datetime, timedelta

from beanie import Document, Update, after_event
from beanie.odm.operators.update.general import Set as _Set
from pydantic import Field

from app.config import get_settings

__all__ = (
    'Set',
    'BaseDBModel',
)


class Set(_Set):
    def __init__(self, expression):
        super().__init__(expression | {'updatedAt': datetime.now()})


class BaseDBModel(Document):
    createdAt: datetime = Field(default_factory=lambda: datetime.now())
    updatedAt: datetime = Field(default_factory=lambda: datetime.now())

    # class Settings:
    #     is_root = True
    #     use_revision = True
    #     use_state_management = True

    def keys(self):
        return list(self.model_fields.keys())

    def __getitem__(self, item):
        return getattr(self, item) if item != 'id' else str(self.id)

    @property
    def data_expired(self) -> bool:
        oldest_data_validity_time = datetime.now() - timedelta(seconds=get_settings().DATA_REFRESH_SECONDS)
        return self.updatedAt < oldest_data_validity_time.replace(tzinfo=self.updatedAt.tzinfo)

    @after_event(Update)
    async def refresh_update_at(self):
        self.updatedAt = datetime.now()

    async def update_fields(self, **kwargs):
        kwargs.update(updatedAt=datetime.now())
        await self.set(kwargs)
