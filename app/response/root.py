from pydantic import BaseModel, Field

__all__ = (
    'StatusResponseData',
)


class StatusResponseData(BaseModel):
    name: str = Field(..., description='Event name')
    sever: bool = Field(..., description='Event Fundraising Licence Number')
    database: bool = Field(..., description='Event start time')
    redis: bool = Field(..., description='Event end time')
    kafka: bool = Field(..., description='Event end time')
