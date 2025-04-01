from fastapi import Request

from app.libs.constants import CustomApiRouter
from app.response import create_event_stream_response
from app.response import ResponseModel
from app.view_models.notification import NotificationGenerateViewModel

__all__ = (
    'router',
)

router = CustomApiRouter(
    prefix='/auth', tags=['Account API'], dependencies=[]
)


@router.get(
    '/request/modify',
    description='Get list of modification requests 获取修改请求列表',
    response_model=ResponseModel[str]
)
async def get_modify_request_list(request: Request):
    return await create_event_stream_response(NotificationGenerateViewModel, request)
