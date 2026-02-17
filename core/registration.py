import logging
from core.services import rate_limited
from core.security import Role
from core.models import UserDB
from core.exceptions import MissingDataError
from core.services import UserService
import hashlib

logger = logging.getLogger(__name__)

def hash_sensitive(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


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

        # Delegate creation to UserService
        user = UserService.create_user(
            username=username,
            password=password,
            role=role,
            db_session=db_session
        )

        logger.info(f"Registered user | user_hash={hash_sensitive(username)}")

        return user