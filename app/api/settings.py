from fastapi import APIRouter

from app.forms.settings import *
from app.view_models.common.settings import *

router = APIRouter(
    prefix='/settings', tags=['Settings API'], dependencies=[]
)


@router.post('/set-password')
async def set_password(form_data: SetPasswordForm):
    async with SetPasswordViewModel(form_data) as response:
        return response
