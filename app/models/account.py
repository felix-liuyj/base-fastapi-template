from enum import Enum
from typing import Annotated, Optional

from beanie import Indexed
from pydantic import Field, EmailStr, HttpUrl, BaseModel
from pymongo import ASCENDING

from app.libs.ctrl.db.mongodb import BaseDatabaseModel
from app.models import SupportImageMIMEType

__all__ = (
    'UserModel',
    'UserProfile',
    'TokenEndpointAuthMethodsSupported',
    'ResponseTypesSupported',
    'GrantTypesSupported',
    'SubjectTypesSupported',
    'IPCompanyDataType',
    'IPCompanyNameDataType',
    'UserStatusEnum',
    'UserTypeEnum',
    'UserModifyStatusEnum',
    'CertificationItemFileType',
    'SupportCertificateMIMEType',
    'ImageFileType',
    'AdminPaymentGatewayType',
    'AdminModel',
    'AdminRoleEnum',
    'AdminProfile',
)


class AdminRoleEnum(Enum):
    SUPER = 'super'
    GENERAL = 'general'


class AdminProfile(BaseModel):
    id: str = Field(...)
    email: EmailStr = Field(..., alias='mail')
    displayName: str = Field(...)
    givenName: str = Field(...)
    surname: str = Field(...)
    userPrincipalName: str = Field(...)


class UserStatusEnum(Enum):
    NEEDS_APPROVAL = 'needs_approval'
    ACTIVE = 'active'
    DISABLED = 'disabled'


class UserModifyStatusEnum(Enum):
    PENDING = 'pending'
    EXECUTED = 'executed'
    REJECTED = 'rejected'


class UserTypeEnum(Enum):
    SELLER = 'seller'
    BUYER = 'buyer'


class SupportCertificateMIMEType(Enum):
    IMAGE_PNG = 'image/png'
    IMAGE_JPG = 'image/jpeg'
    IMAGE_JPEG = 'image/jpeg'
    APPLICATION_PDF = 'application/pdf'

    @classmethod
    def check_value_exists(cls, value: str) -> 'SupportCertificateMIMEType':
        for member in cls:
            if member.value == value:
                return cls(value)


class ImageFileType(BaseModel):
    file_path: str
    file_type: SupportImageMIMEType


class CertificationItemFileType(BaseModel):
    file_path: str
    file_type: SupportCertificateMIMEType


class AdminPaymentGatewayType(BaseModel):
    name: str
    image: str
    enable: bool = True


class TokenEndpointAuthMethodsSupported(Enum):
    CLIENT_SECRET_BASIC = "client_secret_basic"
    CLIENT_SECRET_POST = "client_secret_post"
    CLIENT_SECRET_JWT = "client_secret_jwt"
    PRIVATE_KEY_JWT = "private_key_jwt"


class ResponseTypesSupported(Enum):
    CODE = "code"


class GrantTypesSupported(Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"


class SubjectTypesSupported(Enum):
    PUBLIC = "public"


class IDTokenSigningAlgValuesSupported(Enum):
    RS256 = "RS256"


class ScopesSupported(Enum):
    OPENID = "openid"


class IPCompanyNameDataType(BaseModel):
    en: str
    tc: str
    sc: str

    def __init__(self, *args, **kwargs):
        en, tc, sc = kwargs.pop('en'), kwargs.pop('tc'), kwargs.pop('sc')
        if not tc and not sc:
            tc, sc = en, en
        super().__init__(*args, en=en, tc=tc, sc=sc, **kwargs)


# AccountStatusDataType
class AccountStatusDataType(BaseModel):
    status: str
    commentForStatusChange: str


# BasicProfileMobilePhoneDataType
class BasicProfileMobilePhoneDataType(BaseModel):
    countryCode: str
    number: str


# BasicProfileDataType
class BasicProfileDataType(BaseModel):
    title: Optional[str]
    firstName: str
    lastName: str
    emailId: str
    isEmailIdVerified: bool
    mobilePhone: Optional[BasicProfileMobilePhoneDataType]
    countryCode: Optional[str]
    stateOrProvinceCode: Optional[str]
    cityCode: Optional[str]
    isEuDirectMarketingConsentChecked: bool
    isAccountNatureCompany: bool
    isMobileNumberOtpLoginEnabled: bool
    isMobileNumberVerified: bool
    company: Optional[str]


# ExtendedProfilePersonalDetailsDataType
class ExtendedProfilePersonalDetailsDataType(BaseModel):
    position: Optional[str]
    profilePic: Optional[str]


# ExtendedProfileCompanyInfoAddressDataType
class ExtendedProfileCompanyInfoAddressDataType(BaseModel):
    line1: Optional[str]
    line2: Optional[str]
    line3: Optional[str]
    line4: Optional[str]
    postalCode: Optional[str]
    countryCode: str
    stateOrProvinceCode: str
    cityCode: str


# ExtendedProfileCompanyInfoTelFaxDataType
class ExtendedProfileCompanyInfoTelFaxDataType(BaseModel):
    countryCode: str
    areaCode: Optional[str]
    number: Optional[str]
    ext: Optional[str] = None


# ExtendedProfileCompanyInfoDataType
class ExtendedProfileCompanyInfoDataType(BaseModel):
    tel: Optional[ExtendedProfileCompanyInfoTelFaxDataType]
    fax: Optional[ExtendedProfileCompanyInfoTelFaxDataType]
    companyHqCountryCode: Optional[str]
    email: Optional[str]
    address: Optional[ExtendedProfileCompanyInfoAddressDataType]
    website: Optional[str]
    background: Optional[str]
    numOfStaff: Optional[str]
    yearOfEstablishment: Optional[str]
    natureOfBiz: list[str]
    industryProductServiceCategory: Optional[list[str]]


# ExtendedProfilePreferenceDataType
class ExtendedProfilePreferenceDataType(BaseModel):
    interestedProductService: list[str]
    interestedRegion: list[str]
    interestedTopic: list[str]


# ExtendedProfileDataType
class ExtendedProfileDataType(BaseModel):
    personalDetails: Optional[ExtendedProfilePersonalDetailsDataType]
    companyInfo: Optional[ExtendedProfileCompanyInfoDataType]
    preference: Optional[ExtendedProfilePreferenceDataType]


# Main UserProfile Model
class UserProfile(BaseModel):
    accountStatus: AccountStatusDataType
    altEmail: Optional[str]
    basicProfile: BasicProfileDataType
    createdBy: str
    createdByAppClient: str
    createdDate: str
    extendedProfile: Optional[ExtendedProfileDataType]
    hasPassword: bool
    identities: list[str]
    modifiedBy: str
    modifiedByAppClient: str
    modifiedDate: str
    ssouid: str
    tagLine: Optional[str]
    allowMobileNumberVerificationAction: Optional[bool]


class IPCompanyDataType(BaseModel):
    companyName: IPCompanyNameDataType = Field(..., description="Company name 公司名称")
    companyLogo: HttpUrl = Field(..., description="Company logo 公司logo")
    companyProfile: Optional[str] = Field('', description="Company description 公司介绍")
    companyCountry: str = Field(..., description="Company country/region 公司所在国家/地区")
    companyWebsite: HttpUrl = Field(..., description="Company website 公司官网")
    companyBoothNo: str = Field(..., description="Company booth number 公司展位号")


class UserModel(BaseDatabaseModel):
    # special string type that validates the email as a string
    ssoUid: Annotated[str, Indexed(str, unique=True)] = Field(..., description='User SSO ID')
    email: Annotated[EmailStr, Indexed(EmailStr, unique=True)] = Field(..., description='User email')
    name: str = Field(..., description='User name (administrator name, organization name or volunteer name)')
    username: str = Field(..., description='User display name')
    userType: UserTypeEnum = Field(default=UserTypeEnum.BUYER, description='User user type')
    affiliation: Optional[str] = Field(None, description='User affiliation, source from user email or team id')
    status: UserStatusEnum = Field(default=UserStatusEnum.NEEDS_APPROVAL, description='User status')
    company: Optional[IPCompanyDataType | None] = Field(None, description='User payment gateway configuration')

    class Settings:
        name = 'users'
        strict = False
        indexes = [
            [('_id', ASCENDING)],
        ]

    @property
    def information(self):
        result = {
            'email': self.email,
            'name': self.name,
            'username': self.username,
            'userType': self.userType.name.title(),
        }
        return result


class AdminModel(BaseDatabaseModel):
    email: Annotated[EmailStr, Indexed(EmailStr, unique=True)] = Field(..., description='User email')
    role: AdminRoleEnum = Field(default=AdminRoleEnum.GENERAL, description='Admin role')

    class Settings:
        name = 'administrators'
        strict = False
        indexes = [
            [('_id', ASCENDING)],
        ]
