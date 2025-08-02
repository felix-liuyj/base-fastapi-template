from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message, CustomApiRouter
from app.libs.sso.azure import get_user_profile
from app.models.account import UserProfile
from app.models.common import UserModel
from app.response import ResponseModel
from app.response.root import StatusResponseData

__all__ = (
    'router',
)

router = CustomApiRouter()


@router.get("/status", response_model=ResponseModel[StatusResponseData])
async def check_runtime_status(
        settings: Annotated[Settings, Depends(get_settings)],
        user_profile: Annotated[UserProfile, Depends(get_user_profile)]
):
    user_instance = await UserModel.find_one(UserModel.email == user_profile.altEmail)
    data = StatusResponseData(
        name=settings.APP_NAME, sever=True, database=user_instance is not None, redis=True, kafka=True
    )
    return ResponseModel(
        category=get_settings().APP_NO,
        code=ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value,
        message=get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY),
        data=data
    )
