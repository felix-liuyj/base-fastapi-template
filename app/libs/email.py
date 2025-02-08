import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum

from fastapi.params import Depends
from pydantic import EmailStr, Field

from app.config import get_settings, Settings

__all__ = (
    'send_email_with_radica',
    'send_email_with_ssl',
    'SMTPServiceNameEnum',
    'SMTPMailTypeEnum',
)


class SMTPServiceNameEnum(Enum):
    """定义邮件服务名称"""
    USER_MANAGEMENT = 'User_Management'
    ORDER_SERVICE = 'Order_Service'
    PAYMENT_SERVICE = 'Payment_Service'
    MARKETING = 'Marketing'
    SUPPORT_SERVICE = 'Support_Service'
    NOTIFICATION_SYSTEM = 'Notification_System'


class SMTPMailTypeEnum(Enum):
    """定义邮件类型"""
    # 用户管理
    USER_REGISTRATION = 'User_Registration'
    USER_PASSWORD_RESET = 'Password_Reset'

    # 订单服务
    ORDER_CONFIRMATION = 'Order_Confirmation'
    ORDER_SHIPPED = 'Order_Shipped'

    # 支付服务
    PAYMENT_RECEIPT = 'Payment_Receipt'

    # 营销推广
    MARKETING_PROMOTION_EMAIL = 'Promotion_Email'

    # 客服支持
    SUPPORT_TICKET_OPENED = 'Ticket_Opened'
    SUPPORT_TICKET_RESOLVED = 'Ticket_Resolved'

    # 系统通知
    NOTIFICATION_SYSTEM_ALERT = 'System_Alert'


def send_email_with_radica(
        from_email: EmailStr = Field(..., description="Sender's email address"),
        to_email: list[EmailStr] | EmailStr = Field(..., description='List of recipient email addresses'),
        subject: str = Field(..., description='Email Subject'),
        email_body: str = Field(..., description='HTML content of the email'),
        service_name: SMTPServiceNameEnum = Field(..., description='Service name identifier'),
        mail_type: SMTPMailTypeEnum = Field(..., description='Mail type identifier'),
) -> bool:
    """
    发送带有 Radica 头部信息的 HTML 邮件。
    :param from_email: 发件人邮箱地址
    :param to_email: 收件人邮箱列表
    :param subject: 邮件标题
    :param email_body: 邮件正文（HTML 格式）
    :param service_name: 邮件服务类型（SV_XXX）
    :param mail_type: 邮件类型（MT_XXX）
    :return: 发送成功返回 True，否则返回 False
    """
    settings = get_settings()
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = ', '.join(to_email) if isinstance(to_email, list) else to_email
        msg['Subject'] = subject

        # 添加 Radica 头部
        msg['X-Dpc-APP_NAME'] = settings.APP_NAME
        msg['X-Dpc-SERVICE'] = f'SV_{service_name.value}'
        msg['X-Dpc-MAILTYPE'] = f'MT_{mail_type.value}'
        msg['X-Dpc-ENV'] = f'{settings.APP_NAME}_{settings.APP_ENV.upper()}'

        msg.attach(MIMEText(email_body, 'html'))

        with smtplib.SMTP(settings.SMTP_API_HOST, settings.SMTP_API_PORT) as server:
            server.starttls()
            print(f'Sending email with {settings.SMTP_API_USER}...')
            print(f'From: {from_email}')
            print(f'To: {to_email}')
            print(f'Subject: {subject}')
            print(f'BODY: {email_body}')
            print(f'X-Dpc-APP_NAME: {settings.APP_NAME}')
            print(f'X-Dpc-SERVICE: SV_{service_name.value}')
            print(f'X-Dpc-MAILTYPE: MT_{mail_type.value}')
            print(f'X-Dpc-ENV: {settings.APP_NAME}_{settings.APP_ENV.upper()}')
            server.login(settings.SMTP_API_USER, settings.SMTP_API_KEY)
            result = server.sendmail(from_email, to_email, msg.as_string())

        print(f'✅ 邮件发送成功！{result}')
        return True
    except smtplib.SMTPException as e:
        print(f'❌ 邮件发送失败: {e}')
        return False


def send_email_with_ssl(
        from_email: EmailStr = Field(..., description="Sender's email address"),
        to_email: EmailStr = Field(..., description="Recipient's email address"),
        subject: str = Field(..., description='Email Subject'),
        email_body: str = Field(..., description='HTML content of the email'),
        settings: Settings = Depends(get_settings)
) -> bool:
    try:
        message = MIMEMultipart('alternative')
        message['From'] = from_email
        message['To'] = to_email
        message['Subject'] = subject
        message.attach(MIMEText(email_body, 'html'))
        context = ssl.create_default_context()
        context.set_ciphers('DEFAULT')
        with smtplib.SMTP_SSL(settings.SMTP_API_HOST, settings.SMTP_API_PORT, context=context) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_API_KEY)
            server.sendmail(from_email, to_email, message.as_string())
        return True
    except smtplib.SMTPException:
        return False
