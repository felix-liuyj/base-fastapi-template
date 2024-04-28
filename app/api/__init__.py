from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(
    prefix='', tags=['Root API'], dependencies=[]
)


@router.get("/status")
async def check_runtime_status(settings: Annotated[Settings, Depends(get_settings)]):
    return {
        'name': settings.APP_NAME,
        'sever': True,
    }
