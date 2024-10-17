from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.models.common import UserModel
from app.response import ResponseModel
from app.response.root import StatusResponseData
from app.view_models import get_current_user_config

router = APIRouter(
    prefix='', tags=['Root API'], dependencies=[]
)


@router.get("/status", response_model=ResponseModel[StatusResponseData])
async def check_runtime_status(
        settings: Annotated[Settings, Depends(get_settings)],
        user_instance: Annotated[UserModel, Depends(get_current_user_config)]
):
    data = StatusResponseData(
        name=settings.APP_NAME, sever=True, database=user_instance is not None, redis=True, kafka=True
    )
    return ResponseModel(
        category=get_settings().APP_NO,
        code=ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value,
        message=get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY),
        data=data
    )
