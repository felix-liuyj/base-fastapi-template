import bcrypt
from requests import ReadTimeout

from app.forms.settings import SetPasswordForm
from app.view_models import BaseViewModel

__all__ = (
    'SetPasswordViewModel',
)


class SetPasswordViewModel(BaseViewModel):
    def __init__(self, form_data: SetPasswordForm):
        super().__init__(need_auth=False)
        self.form_data = form_data

    async def before(self):
        try:
            await self.set_password()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    async def set_password(self):
        user = await self.get_user_instance(self.form_data.email.lower())
        await self.check_verification_code(self.form_data.email, self.form_data.vCode)
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(self.form_data.password.encode('utf-8'), salt)
        await user.update_fields(password=hashed_password.decode('utf-8'), isVerified=True)
        self.operating_successfully('password set successfully')
