from fastapi import APIRouter, Request, Query, UploadFile, File, Form

from app.forms.account import *
from app.response import ResponseModel
from app.response.account import AccountLoginResponseData
from app.view_models.account.common import *

router = APIRouter(
    prefix='', tags=['Account API'], dependencies=[]
)


@router.post(
    '/register',
    response_model=ResponseModel[str],
    description='Register account for organization registration'
)
async def register_account(
        email: str = Form(..., description='account email'),
        name: str = Form(..., description='organization name'),
        username: str = Form(..., description='user display name'),
        password: str = Form(..., description='user password'),
        v_code: str = Form(..., alias='vCode', alias_priority=1000, description='Email verification code'),
        avatar: UploadFile = File(..., description='certificate file body'),
):
    async with RegisterViewModel(email, name, username, password, v_code, avatar) as response:
        return response


@router.post(
    '/login',
    response_model=ResponseModel[AccountLoginResponseData | str],
    description='Login account'
)
async def login_user(form_data: LoginForm):
    async with UserLoginViewModel(form_data) as response:
        return response


@router.post('/logout')
async def logout_user(request: Request):
    async with UserLogoutViewModel(request) as response:
        return response


@router.get('/user')
async def get_user_info(request: Request):
    async with GetUserInfoViewModel(request) as response:
        return response


@router.get('/users')
async def get_user_info_list(request: Request):
    async with GetUserInfoListViewModel(request) as response:
        return response


@router.get('/v-code')
async def send_verification_code(email: str = Query(..., embed=True)):
    async with SendVerificationCodeViewModel(email) as response:
        return response
