from beanie.odm.operators.find.logical import Or
from fastapi import Request, UploadFile
from pydantic import EmailStr

from app.models.account import UserTitleEnum
from app.models.common import UserModel
from app.models.account.volunteer import VolunteerConfigurationModel
from app.response.account import *
from app.view_models import BaseAccountAvatarOssViewModel

__all__ = (
    'GetVolunteerViewModel',
    'CreateVolunteerViewModel',
    'UpdateVolunteerViewModel',
)


class GetVolunteerViewModel(BaseAccountAvatarOssViewModel):
    def __init__(
            self, event_id: str, keyword: str, screening: str, page_no: int = 1, page_size: int = 10,
            request: Request = None
    ):
        super().__init__(request=request)
        self.event_id = event_id
        self.keyword = keyword
        self.screening = screening
        self.page_no = page_no
        self.page_size = page_size

    async def before(self):
        await self.get_volunteer_list()

    async def get_volunteer_list(self):
        condition = [UserModel.title == UserTitleEnum.VOLUNTEER]
        if self.keyword:
            condition.append(Or(
                self.keyword in UserModel.name,
                self.keyword in UserModel.username,
                self.keyword in UserModel.email
            ))
        if self.screening:
            condition.append(UserModel.affiliation == self.screening)
        user_list = await UserModel.find(*condition).sort('createdAt').to_list()
        volunteer_list = sorted([
            volunteer_info
            for volunteer in user_list[(self.page_no - 1) * self.page_size: self.page_no * self.page_size]
            if (volunteer_info := await self.fill_volunteer_info(volunteer))
        ])
        self.operating_successfully(VolunteerQueryResponseData(
            volunteerList=volunteer_list, total=len(volunteer_list)
        ))

    async def fill_volunteer_info(self, user: UserModel) -> VolunteerQueryResponseDataVolunteerItem:
        if not (team := await UserModel.get(user.affiliation)):
            return None
        if not (vol_config := await VolunteerConfigurationModel.find_one(
                VolunteerConfigurationModel.affiliation.volunteerId == user.sid
        )):
            return None
        vol_avatar, team_avatar = await self.gen_access_url([user.avatar.file_path, team.avatar.file_path])
        return VolunteerQueryResponseDataVolunteerItem(
            name=user.name, username=user.username, email=user.email, avatar=vol_avatar,
            team=VolunteerQueryResponseDataVolunteerListTeam(name=team.name, avatar=team_avatar),
            amount=self.faker.pyfloat(left_digits=2, min_value=100.00, positive=True),
            registerDate=int(user.createdAt.timestamp() * 1000),
            phoneNumber=vol_config.phoneNumber,
        )


class CreateVolunteerViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request)

    async def before(self):
        admin_list = await UserModel.find(UserModel.title == UserTitleEnum.ADMIN).to_list()
        self.operating_successfully([
            admin.information | {'avatar': await self.gen_access_url(admin.avatar.file_path)}
            for admin in admin_list
        ])


class UpdateVolunteerViewModel(BaseAccountAvatarOssViewModel):
    def __init__(
            self, event_id: str, avatar_file: UploadFile | None, name: str, email: EmailStr | None, request: Request
    ):
        super().__init__(request=request)

    async def before(self):
        admin_list = await UserModel.find(UserModel.title == UserTitleEnum.ADMIN).to_list()
        self.operating_successfully([
            admin.information | {'avatar': await self.gen_access_url(admin.avatar.file_path)} for admin in
            admin_list
        ])
