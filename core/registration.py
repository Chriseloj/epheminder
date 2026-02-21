import logging
from core.services import rate_limited
from core.security import Role
from core.models import UserDB
from core.exceptions import MissingDataError
from core.services import UserService
from core.passwords import validate_password
from core.exceptions import InvalidPasswordError
from core.security import hash_sensitive
logger = logging.getLogger(__name__)


class RegistrationService:

    @staticmethod
    @rate_limited(user_param="username", ip_param="ip")
    def register(username: str, password: str, ip: str, role: Role = Role.USER, db_session=None) -> UserDB:
        """
        Register new user with rate limiting and logging.
        Delegates user creation to UserService.
        """

        if db_session is None:
            raise MissingDataError()

        # ✅ Validate password
        try:
            validate_password(password)
        except InvalidPasswordError as e:
            # Message for CLI 
            raise e

        # Delegate creation to UserService
        user = UserService.create_user(
            username=username,
            password=password,
            role=role,
            db_session=db_session
        )

        logger.info(f"Registered user | user_hash={hash_sensitive(username)}")

        return user