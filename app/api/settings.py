from fastapi import APIRouter, Request, UploadFile, File

from app.forms.settings import *
from app.view_models.settings import *

router = APIRouter(
    prefix='/settings', tags=['Settings API'], dependencies=[]
)


@router.put('/user')
async def update_user(form_data: UpdateUserForm, request: Request = None):
    async with UpdateUserViewModel(form_data, request) as response:
        return response


@router.put('/user/avatar')
async def upload_user_avatar(
        avatar_file: UploadFile = File(..., description='User avatar file body'),
        request: Request = None
):
    async with UploadUserAvatarViewModel(avatar_file, request) as response:
        return response


@router.put('/password')
async def set_password(form_data: SetPasswordForm):
    async with SetPasswordViewModel(form_data) as response:
        return response
