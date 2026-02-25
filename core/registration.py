import logging
from core.decorators import register_rate_limited
from core.security import Role
from core.models import UserDB
from core.exceptions import MissingDataError
from core.passwords import validate_password
from core.user_services import UserService
from core.security import hash_sensitive

logger = logging.getLogger(__name__)


class RegistrationService:

    @staticmethod
    @register_rate_limited(user_param="username", ip_param="ip")
    def register(username: str, password: str, ip: str, role: Role = Role.USER, db_session=None) -> UserDB:

        if db_session is None:
            raise MissingDataError()

        # Validate password
        validate_password(password)

        # Create usuer (without recursion)
        user = UserService.create_user(
            username=username,
            password=password,
            role=role,
            db_session=db_session
        )

        logger.info(f"Registered user | user_hash={hash_sensitive(username)}")

        return user