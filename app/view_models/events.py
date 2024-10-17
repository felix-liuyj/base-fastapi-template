import json
from datetime import timedelta

from bson import ObjectId
from fastapi import Request

from app import get_settings
from app.forms.events import *
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.custom import render_template
from app.libs.integration_api_controller import IntegrationApiCommonController
from app.models.account import UserTitleEnum
from app.models.events import *
from app.response.events import *
from app.view_models import (
    BaseViewModel, BaseEventOssViewModel, BaseOssViewModel
)

__all__ = (
    'EventQueryOverViewViewModel',
    'EventCreateViewModel',
    'EventUpdateViewModel',
    'EventDeleteViewModel',
    'EventOverviewQueryViewModel',
    'EventPuckRenderQueryViewModel',
    'EventPuckRenderPagesPathQueryViewModel',
    'EventPuckRenderUpdateViewModel',
    'EventPuckRenderPageDeleteViewModel',
    'EventAmountOverviewQueryViewModel',
    'EventVolunteerOverviewQueryViewModel',
    'EventTeamOverviewQueryViewModel',
    'EventApprovalViewModel',
    'EventStatusToggleViewModel',
)


class EventQueryOverViewViewModel(BaseOssViewModel):

    def __init__(self, email: str, needs_approval: bool = False, request: Request = None):
        super().__init__(request=request)
        self.event_creator_email = email
        self.needs_approval = needs_approval

    async def before(self):
        await self.query_event_list()

    async def query_event_list(self):
        extra_condition = [EventModel.deleted == False]
        if self.needs_approval:
            extra_condition.append(EventModel.status == EventStatusEnum.NEEDS_APPROVAL)
        match self.user_instance.title:
            case UserTitleEnum.ORGANIZATION:
                extra_condition.append(EventModel.affiliation.creator == self.user_instance.email)
            case UserTitleEnum.ADMIN:
                extra_condition.append(EventModel.affiliation.administrator == self.user_instance.email)
                if self.event_creator_email:
                    extra_condition.append(EventModel.affiliation.creator == self.event_creator_email)
        event_list = await EventModel.find(*extra_condition).to_list()
        self.operating_successfully(await self.fill_event_data_if_not_meet_requirements([
            await self.fill_event_data_once(event) for event in event_list
        ]))

    async def fill_event_data_if_not_meet_requirements(self, item_list: list):
        if (complementary_quantity := get_settings().FAKER_DATA_TARGET_NUMBER - len(item_list)) <= 0:
            return item_list
        return item_list + [await self.fill_event_data_once() for _ in range(complementary_quantity)]

    async def fill_event_data_once(self, event: EventModel = None) -> EventQueryResponseData:
        if not event:
            start_date = self.faker.date_between(start_date='-1y', end_date='today')
            return EventQueryResponseData(
                eventId=str(ObjectId()),
                eventName=self.faker.name(),
                totalFoundRaisingAmount=self.faker.pyfloat(
                    right_digits=2, positive=True, min_value=100.00, max_value=10000000.00
                ),
                status=EventStatusEnum.ONGOING,
                background=await self.gen_access_url('org-events/default.png'),
                volunteersCount=self.faker.random_int(10, 1000),
                startTime=start_date,
                endTime=start_date + timedelta(days=30),
                licenceValidity=self.faker.random_int(1, 100),
            )
        return EventQueryResponseData(
            eventId=str(event.id),
            eventName=event.name,
            status=event.status,
            background=await self.gen_access_url(event.background.file_path),
            totalFoundRaisingAmount=self.faker.pyfloat(
                right_digits=2, positive=True, min_value=100.00, max_value=10000000.00
            ),
            volunteersCount=self.faker.random_int(10, 1000),
            startTime=event.startTime,
            endTime=event.endTime,
            licenceValidity=self.faker.random_int(1, 100),
        )


class EventCreateViewModel(BaseEventOssViewModel):

    def __init__(self, form_data: EventCreateForm, request: Request = None):
        super().__init__(request=request)
        self.form_data = form_data

    async def before(self):
        await self.create_event()

    async def create_event(self):
        event = await EventModel.insert_one(EventModel(
            name=self.form_data.name,
            fundraisingLicenceNumber=self.form_data.fundraisingLicenceNumber,
            affiliation=EventAffiliationType(
                creator=self.user_instance.email, administrator=self.user_instance.affiliation
            ),
            startTime=self.form_data.startTime,
            endTime=self.form_data.endTime
        ))
        poster_render_resource = await self.gen_poster_render_resource(event)
        await event.update_fields(posterRenderResource=poster_render_resource)
        self.operating_successfully(EventCreateResponseData(
            eventId=str(event.id), background=await self.gen_access_url(event.background.file_path)
        ))

    async def gen_poster_render_resource(self, event: EventModel = None) -> PosterRenderResourceDataType:
        pages_render = await self.get_event_puck_render_pages(
            f'org-events/render/templates/{EventRenderTemplateEnum.DEFAULT.value}.json'
        )
        render_root_data = pages_render.pop('root', None)
        await self.update_event_puck_render_pages(f'{self.root}/render/{event.sid}.json', pages_render)
        return PosterRenderResourceDataType(
            pages_render_path=f'{self.root}/render/{event.sid}.json',
            root=PosterRenderResourceRootDataType(props=PosterRenderResourceRootPropsDataType(
                title="New Page", icon="org-events/logos/frsaas.ico", logo="org-events/logos/frsaas.png", items=[
                    PosterRenderResourceRootPropsItemDataType(
                        en="Home", hk="首頁", cn="首页", pathname="/", hidden="N"
                    ), PosterRenderResourceRootPropsItemDataType(
                        en="Products", hk="產品", cn="产品", pathname="/products", hidden="N"
                    ), PosterRenderResourceRootPropsItemDataType(
                        en="Contact", hk="聯絡我們", cn="联系我们", pathname="/contact", hidden="N"
                    ), PosterRenderResourceRootPropsItemDataType(
                        en="About", hk="關於我們", cn="关于我们", pathname="/about", hidden="N"
                    )
                ], description=PosterRenderResourceRootPropsDescriptionDataType(
                    en="This is a new page", hk="這是一個新頁面", cn="这是一个新页面"
                ), copyright=PosterRenderResourceRootPropsDescriptionDataType(
                    en="Copyright © 2024", hk="版權所有 © 2024", cn="版权所有 © 2024"
                )
            ))
        ) if not render_root_data else PosterRenderResourceDataType(
            pages_render_path=f'{self.root}/render/{event.sid}.json',
            root=PosterRenderResourceRootDataType.model_validate(render_root_data)
        )


class EventUpdateViewModel(BaseEventOssViewModel):

    def __init__(self, form_data: EventUpdateForm, request: Request = None):
        super().__init__(request=request)
        self.form_data = form_data

    async def before(self):
        await self.update_event()

    async def update_event(self):
        if not (event := await EventModel.get(self.form_data.eventId)):
            self.not_found('event not exist')
        elif event.deleted:
            self.forbidden('event already deleted, please restore it first')
        if self.form_data.posterRenderResource:
            await self.upload_event_poster_render_resource(event)
        update_field = self.form_data.model_dump(
            exclude=['eventId', 'posterRenderResource'], exclude_defaults=True, exclude_unset=True, exclude_none=True
        )
        await event.update_fields(*update_field)
        self.operating_successfully('event updated successfully')

    async def upload_event_poster_render_resource(self, event: EventModel):
        render_resource_path = f'{self.root}/{self.user_email}/{event.id}.json'
        async with AliCloudOssBucketController() as ob_c:
            upload_result = await ob_c.put_object_async(
                render_resource_path, self.form_data.posterRenderResource.encode()
            )
            if not upload_result:
                self.operating_failed('event poster resource upload failed')
            await event.update_fields(posterRenderResource=render_resource_path)
            self.operating_successfully('event poster resource upload successfully')


class EventDeleteViewModel(BaseViewModel):

    def __init__(self, event_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id

    async def before(self):
        await self.delete_event()

    async def delete_event(self):
        if not (event := await EventModel.get(self.event_id)):
            self.not_found('event not exist')
        await event.update_fields(deleted=True)
        self.operating_successfully('event deleted successfully')


class EventOverviewQueryViewModel(BaseOssViewModel):

    def __init__(self, event_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id

    async def before(self):
        await self.get_event_overview()

    async def get_event_overview(self):
        if not (event := await EventModel.get(self.event_id)):
            self.not_found('event not found')
        lowest_register_count = self.faker.random_int(1, 100)
        current_month_count = self.faker.random_int(lowest_register_count, 1000)
        self.operating_successfully(EventOverviewQueryResponseData(
            eventId=self.event_id,
            eventName=self.faker.name(),
            volunteerOverview=EventDetailQueryResponseDataVolunteerOverview(
                totalRegisterCount=self.faker.random_int(current_month_count, 1000),
                currentMonthRegisterCount=current_month_count,
                lastDayRegisterCount=lowest_register_count,
            ),
            teamCount=self.faker.random_int(1, 100),
            personalRanking=[EventDetailQueryResponseDataRankingData(
                ranking=i,
                email=self.faker.email(),
                avatar=await self.generate_object_access_url('account-avatar/default.png'),
                name=self.faker.name(),
                totalFoundRaisingAmount=amount
            ) for i, amount in enumerate(self.generate_ordered_float_sequence(
                [], 10, min_value=1000, max_value=10000, step=1000)
            )],
            teamRanking=[EventDetailQueryResponseDataRankingData(
                ranking=i,
                email=self.faker.email(),
                avatar=await self.generate_object_access_url('account-avatar/default.png'),
                name=self.faker.name(),
                totalFoundRaisingAmount=amount
            ) for i, amount in enumerate(self.generate_ordered_float_sequence(
                [], 10, min_value=10000, max_value=100000, step=1000)
            )],
        ))

    def generate_ordered_float_sequence(
            self, container: list[float], number: int,
            min_value: float = 0.0, max_value: float = 100000.00, step: float = 0
    ):
        if number <= 0:
            return container
        # 生成新的最大值，使新值总是递增
        new_max_value = self.faker.pyfloat(
            right_digits=2, positive=True, min_value=max_value - step if step else min_value, max_value=max_value
        )
        # 将生成的值添加到容器中
        container.append(new_max_value)
        # 递归调用，生成下一个数
        return self.generate_ordered_float_sequence(
            container, number - 1, min_value=min_value, max_value=new_max_value, step=step
        )


class EventPuckRenderQueryViewModel(BaseEventOssViewModel):

    def __init__(self, event_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id

    async def before(self):
        await self.get_event_render()

    async def get_event_render(self):
        if not (event := await EventModel.get(self.event_id)):
            self.not_found('event not found')
        icon, logo, *_ = await self.gen_access_url(
            [event.posterRenderResource.root.props.icon, event.posterRenderResource.root.props.logo]
        )
        response = QueryEventPuckRenderResponseData(
            eventId=event.sid,
            root=PosterRenderResourceRootDataType(props=PosterRenderResourceRootPropsDataType(
                title=event.posterRenderResource.root.props.title, icon=icon, logo=logo,
                items=event.posterRenderResource.root.props.items,
                description=event.posterRenderResource.root.props.description,
                copyright=event.posterRenderResource.root.props.copyright
            )),
            pages=await self.get_event_puck_render_pages(event.posterRenderResource.pages_render_path),
        )
        self.operating_successfully(response)


class EventPuckRenderPagesPathQueryViewModel(BaseEventOssViewModel):

    def __init__(self, event_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id

    async def before(self):
        await self.get_event_render_pages_path()

    async def get_event_render_pages_path(self):
        if not (event := await EventModel.get(self.event_id)):
            self.not_found('event not found')
        pages = await self.get_event_puck_render_pages(event.posterRenderResource.pages_render_path)
        self.operating_successfully([path.get('pathname', '') for path in pages.values()])


class EventPuckRenderUpdateViewModel(BaseEventOssViewModel):

    def __init__(self, form_data: EventPuckRenderUpdateForm, request: Request = None):
        super().__init__(request=request)
        self.form_data = form_data

    async def before(self):
        await self.update_event_render()

    async def update_event_render(self):
        if not (event := await EventModel.get(self.form_data.eventId)):
            self.not_found('event not found')
        page_render = await self.get_event_puck_render_pages(event.posterRenderResource.pages_render_path)
        page_render.update({self.form_data.pageId: self.form_data.data})
        event_render_source = event.posterRenderResource
        event_render_source.pages_render_path = f'{self.root}/render/{event.sid}.json'
        event_render_source.root = self.form_data.root
        await event.update_fields(posterRenderResource=event_render_source)
        new_event = await EventModel.get(self.form_data.eventId)
        update_result = await self.update_event_puck_render_pages(
            new_event.posterRenderResource.pages_render_path, page_render
        )
        if update_result.status != 200 and not update_result.crc:
            self.operating_failed(EventPuckRenderUpdateResponseData(ok=False))
        self.operating_successfully(EventPuckRenderUpdateResponseData(ok=True))


class EventPuckRenderPageDeleteViewModel(BaseEventOssViewModel):

    def __init__(self, event_id: str, page_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id
        self.page_id = page_id

    async def before(self):
        await self.delete_render_page()

    async def delete_render_page(self):
        if not (event := await EventModel.get(self.event_id)):
            self.not_found('event not found')
        page_render = await self.get_event_puck_render_pages(event.posterRenderResource.pages_render_path)
        if self.page_id not in page_render:
            self.illegal_parameters('page not exist')
        new_event = {key: val for key, val in page_render.items() if key != self.page_id}
        update_result = await self.update_event_puck_render_pages(event, new_event)
        if update_result.status != 200 and not update_result.crc:
            self.operating_failed(EventPuckRenderUpdateResponseData(ok=False))
        self.operating_successfully(EventPuckRenderUpdateResponseData(ok=True))

    @staticmethod
    async def update_event_puck_render_pages(event: EventModel, page_render: dict):
        async with AliCloudOssBucketController() as ob_c:
            return await ob_c.put_object_async(
                event.posterRenderResource.pages_render_path, json.dumps(page_render).encode()
            )


class EventAmountOverviewQueryViewModel(BaseOssViewModel):

    def __init__(self, event_id: str, overview_type: OverviewTypeEnum, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id
        self.overview_type = overview_type

    async def before(self):
        await self.query_event_amount_overview()

    async def query_event_amount_overview(self, event: EventModel = None):
        daily_amount_overview = {i: self.faker.pyfloat(
            right_digits=2, positive=True, min_value=100.00, max_value=100000.00
        ) for i in self.get_last_times(30, 'day')}
        month_amount = round(sum(daily_amount_overview.values()), 2)
        self.operating_successfully(EventAmountOverviewQueryResponseData(
            dailyAmountOverview=daily_amount_overview,
            overviewType=self.overview_type,
            currentMonthAmount=month_amount,
            totalAmount=self.faker.pyfloat(
                right_digits=2, positive=True, min_value=month_amount, max_value=100000000.00
            )
        ))


class EventVolunteerOverviewQueryViewModel(BaseOssViewModel):

    def __init__(self, event_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id

    async def before(self):
        await self.query_event_volunteer_overview()

    async def query_event_volunteer_overview(self, event: EventModel = None):
        daily_volunteer_overview = {i: self.faker.pyint(
            min_value=10, max_value=100
        ) for i in self.get_last_times(30, 'day')}
        month_volunteer = sum(daily_volunteer_overview.values())
        self.operating_successfully(EventVolunteerOverviewQueryResponseData(
            dailyOverview=daily_volunteer_overview,
            currentMonthVolunteer=month_volunteer,
            totalVolunteer=self.faker.pyint(min_value=month_volunteer, max_value=100000)
        ))


class EventTeamOverviewQueryViewModel(BaseOssViewModel):

    def __init__(self, event_id: str, request: Request = None):
        super().__init__(request=request)
        self.event_id = event_id

    async def before(self):
        await self.query_event_team_overview()

    async def query_event_team_overview(self, event: EventModel = None):
        daily_team_overview = {i: self.faker.pyint(
            min_value=1, max_value=10
        ) for i in self.get_last_times(30, 'day')}
        month_team = sum(daily_team_overview.values())
        self.operating_successfully(EventTeamOverviewQueryResponseData(
            dailyOverview=daily_team_overview,
            currentMonthTeam=month_team,
            totalTeam=self.faker.pyint(min_value=month_team, max_value=10000)
        ))


class EventApprovalViewModel(BaseViewModel):

    def __init__(self, form_data: EventApprovalForm, request: Request = None):
        super().__init__(request=request, access_title=[UserTitleEnum.ADMIN])
        self.form_data = form_data

    async def before(self):
        await self.approval_event()

    async def approval_event(self):
        if not (event := await EventModel.get(self.form_data.eventId)):
            self.not_found('event not exist')
        elif event.approved == self.form_data.result:
            self.forbidden('event application already approved or rejected')
        await event.update_fields(approved=self.form_data.result)
        self.operating_successfully('event application approval executed successfully')


class EventStatusToggleViewModel(BaseViewModel):

    def __init__(self, form_data: EventStatusToggleForm, request: Request = None):
        super().__init__(request=request, access_title=[UserTitleEnum.ADMIN])
        self.form_data = form_data

    async def before(self):
        await self.toggle_event_status()

    async def toggle_event_status(self):
        if not (event := await EventModel.get(self.form_data.eventId)):
            self.not_found('event not exist')
        elif not event.approved:
            self.forbidden('event application has not been approved')
        await event.update_fields(status=self.form_data.status)
        async with IntegrationApiCommonController() as isa_c:
            email_body = render_template(
                'email/event-modify-reason.html',
                email=event.affiliation.creator, affiliation=self.user_email,
                event_name=event.name, change_field='status', reason=self.form_data.remark
            )
            await isa_c.send_mail(event.affiliation.creator, f'{event.name} Status Changed', email_body)
        self.operating_successfully('event status updated successfully')
