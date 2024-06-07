from typing import Optional

from fastapi import APIRouter, Request, Query, File, UploadFile

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


@router.post('/file')
async def upload_organization_certificate(
        category: str = Query(
            ..., embed=True,
            description='certificate category, only support identification_document/event_creation_licence_document/business_registration_certificate'
        ),
        upload_file: UploadFile = File(..., description='certificate file body'),
        request: Request = None
):
    async with UploadFileViewModel(category, upload_file, request) as response:
        return response


@router.get('/file')
async def get_organization_certificate(
        category: str = Query(
            ..., embed=True, example='identification_document',
            description='certificate category, only support identification_document/event_creation_licence_document/business_registration_certificate'
        ),
        download_file: Optional[bool] = Query(
            default=False, embed=True,
            description='download file or not, if it is true, the response will be a download url'
        ),
        request: Request = None
):
    async with GetFileViewModel(category, download_file, request) as response:
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
