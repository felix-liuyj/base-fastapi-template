from fastapi import APIRouter, Request

from app.forms.common import *
from app.view_models.common import *

router = APIRouter(
    prefix='/common', tags=['Common API'], dependencies=[]
)


@router.post('/register')
async def register_account(form_data: RegisterAccountForm):
    async with RegisterViewModel(form_data) as response:
        return response


@router.post('/login')
async def login_user(form_data: LoginForm):
    async with UserLoginViewModel(form_data) as response:
        return response


@router.get('/logout')
async def logout_user(request: Request):
    async with UserLogoutViewModel(request) as response:
        return response


@router.get('/user-info')
async def get_user_info_account(request: Request):
    async with GetUserInfoViewModel(request) as response:
        return response


@router.post('/send-v-code')
async def send_verification_code(form_data: ValidateEmailForm):
    async with SendVerificationCodeViewModel(form_data) as response:
        return response


@router.post('/verify-email')
async def verify_email(form_data: VerifyEmailForm):
    async with VerifyEmailViewModel(form_data) as response:
        return response
