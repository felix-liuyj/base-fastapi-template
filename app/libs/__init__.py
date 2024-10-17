from pydantic import BaseModel

__all__ = (
    'BaseNotEmptyModel',
)


class BaseNotEmptyModel(BaseModel):
    @property
    def data(self):
        return self.model_dump(exclude_unset=True, exclude_none=True, exclude_defaults=True)
