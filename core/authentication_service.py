import logging
from core.services import rate_limited
from core.exceptions import MissingDataError, InvalidUserError
from core.services import UserService 
import hashlib

logger = logging.getLogger(__name__)


def hash_sensitive(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

class AuthenticationService:

    @staticmethod
    @rate_limited(user_param="username", ip_param="ip")
    def login(username: str, password: str, ip: str, db_session=None):
        """
        Authenticate user with rate limiting and logging.
        Delegates user retrieval to UserService.
        """

        if db_session is None:
            raise MissingDataError()

        username = username.strip().lower()  # normalize

        # Search usuer with UserService
        user = UserService.get_user_by_username(username, db_session=db_session)

        # Validation
        if not user or not user.is_active:
            raise InvalidUserError(username)

        from core.passwords import verify_password
        if not verify_password(password, user.password_hash):
            raise InvalidUserError(username)

        logger.info(f"Successful login | user_hash={hash_sensitive(username)}")

        return user