from datetime import datetime

from fastapi import Request

from app.forms.account import *
from app.models.account import UserTitleEnum
from app.models.common import UserModel
from app.models.account.team import TeamAffiliationDataType, TeamConfigurationModel
from app.response.account import TeamCreateResponseData
from app.view_models import BaseAccountAvatarOssViewModel

__all__ = (
    'CreateTeamViewModel',
    'UpdateTeamViewModel',
)


class CreateTeamViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, form_data: TeamCreateForm, request: Request):
        super().__init__(request=request)
        self.form_data = form_data

    async def before(self):
        await self.create_team()

    async def create_team(self):
        if await UserModel.find_one(UserModel.name == self.form_data.name):
            self.operating_failed('team name already exists')
        team_info = await UserModel.insert_one(UserModel(
            email=f'{int(datetime.now().timestamp())}-{self.user_instance.email}',
            name=self.form_data.name, username=self.form_data.name, title=UserTitleEnum.TEAM,
            affiliation=self.user_instance.email
        ))
        await TeamConfigurationModel.insert_one(TeamConfigurationModel(
            affiliation=TeamAffiliationDataType(
                administrator=self.user_instance.affiliation,
                organization=self.user_instance.email,
                eventId=self.form_data.eventId
            )
        ))
        self.operating_successfully(TeamCreateResponseData(ok=True, teamId=team_info.sid))


class UpdateTeamViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request)

    async def before(self):
        admin_list = await UserModel.find(UserModel.title == UserTitleEnum.ADMIN).to_list()
        self.operating_successfully([
            admin.information | {'avatar': await self.gen_access_url(admin.avatar.file_path)} for admin in admin_list
        ])
