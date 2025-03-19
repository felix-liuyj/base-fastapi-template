import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel, ValidationError, Field, EmailStr

from app.config import get_settings
from app.libs.ctrl.db import RedisCacheController
from app.libs.sso import OptionalOAuth2AuthorizationCodeBearer

oauth2_scheme = OptionalOAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/authorize",
    tokenUrl=f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/token",
)


class AzureSSOUser(BaseModel):
    id: str = Field(..., description="User unique identifier 用户唯一标识符")
    displayName: Optional[str] = Field('', description="User display name 用户显示名")
    givenName: Optional[str] = Field('', description="User first name 用户名")
    surname: Optional[str] = Field('', description="User last name 用户姓")
    userPrincipalName: EmailStr = Field(..., description="User principal name 用户主体名称（UPN）")
    mail: Optional[EmailStr] = Field(None, description="User primary email 用户主要邮箱")
    otherMails: Optional[list[EmailStr]] = Field([], description="User other emails 用户的其他电子邮件地址列表")
    accountEnabled: bool = Field(..., description="Account enabled status 账户是否启用")
    userType: Optional[str] = Field('', description="User type (Member/Guest) 用户类型（成员/来宾）")
    jobTitle: Optional[str] = Field('', description="User job title 用户职位")
    department: Optional[str] = Field('', description="User department 用户所在部门")
    companyName: Optional[str] = Field('', description="User associated company 用户关联的公司")
    country: Optional[str] = Field('', description="User country 用户所在国家/地区")
    city: Optional[str] = Field('', description="User city 用户所在城市")
    state: Optional[str] = Field('', description="User state 用户所在省份")
    streetAddress: Optional[str] = Field('', description="User street address 用户街道地址")
    postalCode: Optional[str] = Field('', description="User postal code 用户邮政编码")
    officeLocation: Optional[str] = Field('', description="User office location 用户办公室位置")
    mobilePhone: Optional[str] = Field('', description="User mobile phone 用户手机号")
    businessPhones: Optional[list[str]] = Field([], description="User business phone numbers 用户办公电话")
    ageGroup: Optional[str] = Field('', description="User age group 用户年龄组 (Minor/NotAdult/Adult)")
    consentProvidedForMinor: Optional[str] = Field('', description="Consent status for minors 未成年人同意状态")
    hireDate: Optional[datetime] = Field(None, description="User hire date 用户雇佣日期")
    employeeId: Optional[str] = Field('', description="User employee ID 用户员工编号")
    employeeType: Optional[str] = Field('', description="User employee type 用户雇员类型")
    usageLocation: Optional[str] = Field('', description="User usage location 用户使用位置")
    signInActivity: Optional[datetime] = Field(None, description="Last sign-in time 上次登录时间")
    createdDateTime: Optional[datetime] = Field(None, description="Account creation date 账户创建时间")
    lastPasswordChangeDateTime: Optional[datetime] = Field(
        None, description="Last password change date 上次密码修改时间"
    )
    refreshTokensValidFromDateTime: Optional[datetime] = Field(
        None, description="Refresh token validity timestamp 刷新令牌生效时间"
    )
    signInSessionsValidFromDateTime: Optional[datetime] = Field(
        None, description="Sign-in session validity timestamp 登录会话有效时间"
    )
    licenseAssignmentStates: Optional[list[str]] = Field([], description="User assigned licenses 用户分配的许可证")
    assignedPlans: Optional[list[str]] = Field([], description="User assigned plans 用户分配的计划")
    proxyAddresses: Optional[list[str]] = Field([], description="User proxy addresses 用户代理地址列表")
    preferredLanguage: Optional[str] = Field('', description="User preferred language 用户首选语言")
    preferredDataLocation: Optional[str] = Field('',
                                                 description="User preferred data location 用户首选数据存储位置")
    passwordPolicies: Optional[str] = Field('', description="User password policies 用户密码策略")
    passwordProfile: Optional[dict] = Field(None, description="User password profile 用户密码配置文件")

    class Config:
        schema_extra = {
            "example": {
                "id": "12345678-90ab-cdef-1234-567890abcdef",
                "displayName": "张三",
                "givenName": "三",
                "surname": "张",
                "userPrincipalName": "zhangsan@example.com",
                "mail": "zhangsan@example.com",
                "accountEnabled": True,
                "userType": "Member",
                "jobTitle": "软件工程师",
                "department": "IT",
                "companyName": "Cambria Tech",
                "country": "CN",
                "city": "深圳",
                "state": "广东",
                "streetAddress": "科技园路 100 号",
                "postalCode": "518000",
                "officeLocation": "A2-1001",
                "mobilePhone": "+86 139 0000 0000",
                "businessPhones": ["+86 755 1234 5678"],
                "ageGroup": "Adult",
                "consentProvidedForMinor": "NotRequired",
                "hireDate": "2022-01-01T00:00:00Z",
                "employeeId": "E123456",
                "employeeType": "Employee",
                "usageLocation": "CN",
                "signInActivity": "2025-03-19T08:00:00Z",
                "createdDateTime": "2020-06-15T12:00:00Z",
                "lastPasswordChangeDateTime": "2024-03-10T10:30:00Z",
                "refreshTokensValidFromDateTime": "2024-01-01T00:00:00Z",
                "signInSessionsValidFromDateTime": "2024-01-01T00:00:00Z",
                "licenseAssignmentStates": ["Microsoft 365 E5"],
                "assignedPlans": ["Exchange Online"],
                "proxyAddresses": ["SMTP:zhangsan@example.com"],
                "preferredLanguage": "zh-CN",
                "preferredDataLocation": "China",
                "passwordPolicies": "DisablePasswordExpiration",
                "passwordProfile": {"forceChangePasswordNextSignIn": False}
            }
        }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: Optional[str] = None


async def generate_sso_login_url() -> str:
    state = str(uuid.uuid4())
    async with RedisCacheController() as cache:
        await cache.set(str(state), 1, 60 * 5)
    auth_params = {
        "client_id": get_settings().SSO_AZURE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": get_settings().SSO_AZURE_REDIRECT_URI,
        "response_mode": "query",
        "scope": "User.Read",
        "state": state,
        "prompt": "select_account",
    }
    return f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/authorize?{urlencode(auth_params)}"


async def get_user_profile(access_token: Optional[str] = Depends(oauth2_scheme)) -> AzureSSOUser | None:
    if not access_token:
        return None
    try:
        async with RedisCacheController() as cache:
            if admin_profile_json := await cache.get(access_token):
                return AzureSSOUser.model_validate_json(admin_profile_json)
            async with httpx.AsyncClient() as client:
                response = await client.get("https://graph.microsoft.com/v1.0/me", headers={
                    "Authorization": f"Bearer {access_token}"
                })
                admin_profile = AzureSSOUser.model_validate(response.raise_for_status().json())
                await cache.set(access_token, admin_profile.model_dump_json(), ex=60 * 60 * 12)
                return admin_profile
    except HTTPException:
        return None
    except HTTPStatusError:
        return None
    except ValidationError:
        return None
