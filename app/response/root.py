from pydantic import BaseModel, Field

__all__ = (
    'StatusResponseData',
)


class StatusResponseData(BaseModel):
    name: str = Field(..., embed=True, description='Event name')
    sever: bool = Field(..., embed=True, description='Event Fundraising Licence Number')
    database: bool = Field(..., embed=True, description='Event start time')
    redis: bool = Field(..., embed=True, description='Event end time')
    kafka: bool = Field(..., embed=True, description='Event end time')
