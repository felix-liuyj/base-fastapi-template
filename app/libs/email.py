from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiosmtplib import SMTP, SMTPException
from pydantic import EmailStr, Field

from app.config import get_settings

__all__ = (
    'EmailController',
)


class EmailController(SMTP):
    def __init__(
            self,
            from_email: EmailStr = Field(..., description="Sender's email address 发送者的电子邮件地址"),
            to_email: EmailStr = Field(..., description="Recipient's email address 收件人的电子邮件地址"),
            subject: str = Field(..., description='Email Subject 邮件主题'),
            email_body: str = Field(..., description='HTML content of the email 电子邮件的 HTML 内容'),
            use_tls: bool = Field(False, description='Use TLS or not 是否使用 TLS')
    ):
        super().__init__(
            hostname=get_settings().SMTP_HOST, port=get_settings().SMTP_PORT, use_tls=use_tls
        )
        self.from_email = from_email
        self.to_email = to_email
        self.subject = subject
        self.email_body = email_body
        self.use_tls = use_tls
        self.message = self.__generate_email_message(from_email, to_email, subject, email_body)

    async def send_email_with_ssl(self) -> bool:
        try:
            print(f'Send mail to {self.to_email}')
            await self.login(get_settings().SMTP_USERNAME, get_settings().SMTP_PASSWORD)
            await self.sendmail(self.from_email, self.to_email, self.message.as_string())
            return True
        except SMTPException:
            return False

    def __generate_email_message(self):
        message = MIMEMultipart('alternative')
        message['From'] = self.from_email
        message['To'] = self.to_email
        message['Subject'] = self.subject
        message.attach(MIMEText(self.email_body, 'html'))
        return message
