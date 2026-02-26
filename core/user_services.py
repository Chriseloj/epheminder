import uuid
import logging
from datetime import datetime, timezone
from core.models import UserDB
from core.security import Role
from core.exceptions import (
    MissingDataError,
    InvalidUserError,
    UsernameTakenError
)
from core.passwords import validate_password, hash_password
from infrastructure.repositories import UserRepository
from core.hash_utils import hash_sensitive

logger = logging.getLogger(__name__)

# 🔐 UserService
class UserService:

    @staticmethod
    def create_user(username: str, password: str, role: Role = Role.USER, db_session=None) -> "UserDB":
        """
        Create a new user in the database with validation.

        - Validates username (alphanumeric, 3-30 characters).
        - Validates password according to security rules.
        - Ensures username is unique.
        - Generates user ID and created_at timestamp automatically.
        - Persists the user in the provided database session.

        Args:
            username (str): Desired username for the new user.
            password (str): User password to be hashed and stored.
            role (Role, optional): User role; defaults to Role.USER.
            db_session: SQLAlchemy Session instance. Required.

        Returns:
            UserDB: The newly created user object.

        Raises:
            MissingDataError: If db_session is not provided.
            InvalidUserError: If username is invalid.
            UsernameTakenError: If username already exists.
        """
        username = username.strip().lower()
        
        if db_session is None:
            raise MissingDataError()
        
        # Validate username
        if not 3 <= len(username) <= 30 or not username.isalnum():
            raise InvalidUserError(username)
        
        # Repository
        repo = UserRepository(db_session)

        # Verify unique username
        if repo.get_by_username(username):
            raise UsernameTakenError(username)
        
        # Validate password
        validate_password(password)
        password_hash = hash_password(password)

        # Create UserDB
        user_id = uuid.uuid4()
        user = UserDB(
            id=user_id,
            username=username,
            password_hash=password_hash,
            role=role.name,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )

        # Save user
        repo.add(user)

        logger.info(f"User created | Username={hash_sensitive(username)} | Role={user.role} | ID={hash_sensitive(user_id)}")

        return user
        
    @staticmethod
    def get_user_by_id(user_id, db_session=None):
        if db_session is None:
            raise MissingDataError()

        if isinstance(user_id, uuid.UUID):
            user_uuid = user_id
        else:
            try:
                user_uuid = uuid.UUID(user_id)
            except (ValueError, TypeError):
                return None

        repo = UserRepository(db_session)
        return repo.get_by_id(user_uuid)
    
    @staticmethod
    def get_user_by_username(username: str, db_session=None) -> "UserDB":
        """
        Retrieve a user by username.

        Args:
            username (str): username to search
            db_session: SQLAlchemy session

        Returns:
            UserDB if found, else None
        """
        if db_session is None:
            raise MissingDataError()
        repo = UserRepository(db_session)
        return repo.get_by_username(username)