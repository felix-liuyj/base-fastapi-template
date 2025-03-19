from fastapi import Request

from app.models.account import UserProfile
from app.view_models import BaseViewModel

__all__ = (
    'NotificationGenerateViewModel',
)


class NotificationGenerateViewModel(BaseViewModel):

    def __init__(self, request: Request, user_profile: UserProfile = None):
        super().__init__(request=request, user_profile=user_profile)

    async def before(self):
        await super().before()
        self.generate_notification()

    def generate_notification(self):
        self.operating_successfully('logged out successfully')
