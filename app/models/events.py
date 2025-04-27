from datetime import datetime
from enum import IntEnum, Enum
from typing import Optional

from pydantic import Field, BaseModel, EmailStr
from pymongo import HASHED

from app.models import BaseDatabaseModel, SupportImageMIMEType
from app.models.account import CertificationItemFileType

__all__ = (
    'DomainModeEnum',
    'OverviewTypeEnum',
    'EventModel',
    'EventStatusEnum',
    'ExpiryHandlingModeEnum',
    'NotificationCategoryEnum',
    'EventAffiliationType',
    'PosterRenderResourceRootDataType',
    'PosterRenderResourceRootPropsDataType',
    'PosterRenderResourceDataType',
    'ExpiryHandlingDataType',
    'DomainSettingsType',
    'EventRenderTemplateEnum',
    'PosterRenderResourceRootPropsItemDataType',
    'PosterRenderResourceRootPropsLocaleDataType',
    'EventEmailConfigurationDataType',
    'EventEmailStatusEnum',
    'ExpiryHandlingModeEnum',
    'EventVolunteerConfigurationDataType',
    'DownloadModeEnum',
    'AutoSendModeEnum',
)


class DownloadModeEnum(Enum):
    DENY_DOWNLOAD = 'deny_download'
    ALLOW_DOWNLOAD = 'allow_download'


class AutoSendModeEnum(Enum):
    NOT_AUTO_SEND = 'not_auto_send'
    AUTO_SEND = 'auto_send'


class EventStatusEnum(Enum):
    NEEDS_APPROVAL = 'needs_approval'
    ONGOING = 'ongoing'
    PAUSED = 'paused'
    CLOSED = 'closed'
    DEPRECATED = 'deprecated'
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class ExpiryHandlingModeEnum(Enum):
    CLOSE = 'close'
    REDIRECT = 'redirect'
    KEEP_ACTIVE = 'keep_active'


class EventRenderTemplateEnum(Enum):
    DEFAULT = 'default'


class DomainModeEnum(str, Enum):
    NONE = 'none'
    PLATFORM = 'platform'
    CUSTOM = 'custom'


class NotificationCategoryEnum(Enum):
    EMAIL = 'email'
    REGISTER = 'register'
    DONATION_SUCCESS = 'donation_success'


class TeamDateType(BaseModel):
    name: str = Field(..., description='Team name'),
    avatar: str = Field(..., description='Team avatar')


class OverviewTypeEnum(IntEnum):
    PERSONAL = 0
    TEAM = 1


class EventAffiliationType(BaseModel):
    creator: Optional[EmailStr] = Field('', description='Event creator')
    administrator: Optional[EmailStr] = Field('', description='Organization administrator')
    orgId: str = Field(..., description='Org Id')


class EventBackgroundImageFileType(BaseModel):
    file_path: str
    file_type: SupportImageMIMEType


class EventI18nStrDataType(BaseModel):
    en: str
    tc: str
    sc: str


class PosterRenderResourceRootPropsItemDataType(BaseModel):
    en: str
    tc: str
    sc: str
    pathname: str
    hidden: str


class PosterRenderResourceRootPropsLocaleDataType(BaseModel):
    en: str
    tc: str
    sc: str


class PosterRenderResourceRootPropsDataType(BaseModel):
    title: str  # PosterRenderResourceRootPropsLocaleDataType || str
    titleTC: str
    titleSC: str
    icon: str
    logo: str
    items: list[PosterRenderResourceRootPropsItemDataType]
    contractTitle: PosterRenderResourceRootPropsLocaleDataType
    contractContent: PosterRenderResourceRootPropsLocaleDataType
    copyright: PosterRenderResourceRootPropsLocaleDataType


class PosterRenderResourceRootDataType(BaseModel):
    props: PosterRenderResourceRootPropsDataType


class PosterRenderResourceDataType(BaseModel):
    pages_render_path: str
    root: dict


class ExpiryHandlingDataType(BaseModel):
    expiryHandlingMode: ExpiryHandlingModeEnum = Field(..., description='Event expiry handling mode')
    redirectUrl: Optional[str] = Field('', description='Event redirect url')
    keepActiveDialogContent: Optional[str] = Field('', description='Event keep active dialog content')
    keepActiveAllowUserRegister: Optional[bool] = Field(False, description='Event keep active allow user register')


class DomainSettingsType(BaseModel):
    domainMode: DomainModeEnum = Field(..., description='Domain mode')
    domain: Optional[str] = Field('', description='Domain')
    subDomain: Optional[str] = Field('www', description='Subdomain')
    ruleId: Optional[str] = Field('', description='Domain rule ID')


class EventEmailStatusEnum(Enum):
    UNVERIFIED = 'unverified'
    FAILED = 'failed'
    VERIFIED = 'verified'
    DELETED = 'deleted'


class EventEmailConfigurationDataType(BaseModel):
    email: EmailStr = Field(..., description='Email')
    status: EventEmailStatusEnum = Field(..., description='Email status')

    def __dict__(self):
        return {
            'email': self.email,
            'status': self.status,
        }


class EventVolunteerConfigurationDataType(BaseModel):
    certificateFile: str = Field(..., description='Volunteer certificate file url')
    minimumDonationAmount: float = Field(..., description='Minimum donation amount')
    downloadMode: DownloadModeEnum = Field(..., description='Download mode')
    downloadTime: datetime = Field(..., description='Download time')
    autoSendMode: AutoSendModeEnum = Field(..., description='Auto send mode')
    autoSendTime: datetime = Field(..., description='Auto send time')


class EventModel(BaseDatabaseModel):
    name: str = Field(..., description='Event name')
    fundraisingLicenceNumber: Optional[str] = Field('', description='Event Fundraising Licence Number')
    background: Optional[EventBackgroundImageFileType] = Field(EventBackgroundImageFileType(
        file_path='org-events/default.png', file_type=SupportImageMIMEType.IMAGE_PNG
    ), description='Event background')
    approved: Optional[bool] = Field(False, description='Is Event application approved')
    posterRenderResource: Optional[PosterRenderResourceDataType] = Field(
        None, description='Event poster render resource oss path, resource content type: json'
    )
    puckTemplateId: Optional[str] = Field('', description='Puck template ID')
    image: Optional[str] = Field('', description='Event image URL')
    affiliation: Optional[EventAffiliationType | None] = Field(None, description='Event affiliation')
    fundraisingAmount: float = Field(0.0, description='Event fundraising amount')
    startTime: datetime = Field(..., description='Event start time')
    endTime: datetime = Field(..., description='Event end time')
    status: Optional[EventStatusEnum] = Field(EventStatusEnum.NEEDS_APPROVAL, description='Event status')
    deleted: Optional[bool] = Field(False, description='Is Event deleted')
    expiryHandling: Optional[ExpiryHandlingDataType] = Field(
        ExpiryHandlingDataType(
            expiryHandlingMode=ExpiryHandlingModeEnum.CLOSE), description='Event extra information'
    )
    domainSettings: Optional[DomainSettingsType] = Field(
        DomainSettingsType(domainMode=DomainModeEnum.NONE),
        description='Event domain settings'
    )
    emailConfiguration: Optional[list[EventEmailConfigurationDataType] | None] = Field(
        default_factory=lambda: list, description='Event email configuration list'
    )
    volunteerCertificateConfiguration: Optional[EventVolunteerConfigurationDataType] = Field(
        None, description='Volunteer certificate configuration'
    )
    identification_document: Optional[CertificationItemFileType | None] = Field(
        None, description='User identification document'
    )
    event_creation_licence_document: Optional[CertificationItemFileType | None] = Field(
        None, description='User event creation licence document'
    )
    business_registration_certificate: Optional[CertificationItemFileType | None] = Field(
        None, description='User business registration certificate'
    )

    class Settings:
        name = 'events'
        strict = False
        indexes = [
            [('_id', HASHED)],
        ]

    @property
    def active(self):
        now = datetime.now()
        return self.startTime < now < self.endTime and self.status == EventStatusEnum.ONGOING

    @property
    def closed(self):
        now = datetime.now()
        return now > self.endTime and self.status in [EventStatusEnum.ONGOING, EventStatusEnum.CLOSED]

    @property
    def prepared(self):
        now = datetime.now()
        return all([now < self.startTime, self.status == EventStatusEnum.ONGOING])

    @property
    def volunteer_quantity(self):
        return 0

    @property
    def team_quantity(self):
        return 0

    @property
    def information(self):
        return self.model_dump(exclude=['posterRenderResource']) | {
            'active': self.active, 'closed': self.closed, 'prepared': self.prepared
        }

    @property
    def in_place(self):
        return all([
            self.identification_document, self.event_creation_licence_document, self.business_registration_certificate
        ])
