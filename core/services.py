import uuid
import logging
from datetime import datetime, timedelta, timezone
from core.models import UserDB, ReminderDB
from core.security import authorize, Role
from core.exceptions import (MissingDataError,
ReminderTextTooLongError,
InvalidExpirationError,
InvalidUserError,
UsernameTakenError,
InvalidUUIDError)
from core.passwords import validate_password, hash_password
from core.utils import MAX_EXPIRATION_MINUTES, MAX_TEXT_LENGTH
from infrastructure.repositories import UserRepository

logger = logging.getLogger(__name__)

# 🔐 UserService
class UserService:

    @staticmethod
    def create_user(username: str, password: str, role: Role = Role.USER, db_session=None) -> "UserDB":
        """
        Create a new user in the database with validations.

        - username: alphanumeric string, 3-30 characters
        - password: must meet security requirements
        - role: user's role (Role enum)
        - db_session: SQLAlchemy Session instance

        Raises:
            InvalidUserError: if username is invalid
            UsernameTakenError: if username already exists
            MissingDataError: if db_session is missing
        """

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
        user_id = str(uuid.uuid4())
        user = UserDB(
            id=user_id,
            username=username,
            password_hash=password_hash,
            role=role.name,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )

        # save
        repo.add(user)

        logger.info(f"User created | Username={username} | Role={user.role} | ID={user_id}")

        return user
        
    @staticmethod
    def get_user_by_id(user_id: str, db_session=None) -> "UserDB":
        """
        Retrieve a user by their ID from the database.

        - user_id: UUID string identifying the user
        - db_session: SQLAlchemy Session instance

        Returns:
            UserDB object if found, otherwise None

        Raises:
            MissingDataError: if db_session is missing
        """

        if db_session is None:
            raise MissingDataError()

        # Repository
        repo = UserRepository(db_session)

        # Search Userr by ID
        user = repo.get_by_id(user_id)

        return user  

# 🔐 ReminderService
class ReminderService:

    @staticmethod
    def get_user_reminder(user, reminder_id, reminder_repo):
        """
        Retrieve a reminder by ID for a given user.
        - Deny-by-default: authorization is checked before returning the reminder.
        - Returns the reminder object or None if it does not exist.
        """

        # Validate that the reminder_id is a proper UUID
        ReminderService._validate_uuid(reminder_id)

        # Fetch reminder from the repository
        reminder = reminder_repo.get_by_id(reminder_id)
        if not reminder:
            return None

        # Enforce deny-by-default authorization
        authorize(user, "read", resource_owner_id=reminder.owner_id)

        # Logging for auditing purposes
        logger.info(f"Reminder read | Role={user.role_enum.name} | ReminderID={reminder.id}")
        
        return reminder

    @staticmethod
    def _validate_uuid(id_str: str):
        """
        Validate that a string is a proper UUID.
        - Raises InvalidUUIDError if the string is not a valid UUID.
        """
        try:
            uuid.UUID(id_str)
        except ValueError:
            raise InvalidUUIDError(id_str)
    
    @staticmethod
    def create_reminder(user: "UserDB", text: str, amount: int, unit: str, reminder_repo=None) -> "ReminderDB":
        """
        Create a new reminder for the given user.

        - Enforces deny-by-default authorization, ensuring the user can create a reminder for themselves.
        - Converts the provided expiration (amount + unit) into total minutes using parse_expiration().
        - Validates reminder text length against MAX_TEXT_LENGTH.
        - Generates a unique UUID for the reminder.
        - Sets created_at, updated_at, and expires_at timestamps.
        - Persists the reminder using the repository.
        - Logs the creation event for auditing purposes.

    Args:
        user (UserDB): The authenticated user creating the reminder.
        text (str): The reminder content.
        amount (int): Time quantity for expiration.
        unit (str): Time unit ("minutes", "hours", or "days").
        reminder_repo: Reminder repository instance.

    Returns:
        ReminderDB: The created reminder object.

    Raises:
        MissingDataError: If reminder_repo is not provided.
        InvalidExpirationError: If expiration amount or unit is invalid.
        ReminderTextTooLongError: If text exceeds MAX_TEXT_LENGTH.
    """

        if reminder_repo is None:
            raise MissingDataError()

        authorize(user, "create", resource_owner_id=user.id)

        expires_in_minutes = ReminderService.parse_expiration(amount, unit)

        if len(text) > MAX_TEXT_LENGTH:
            raise ReminderTextTooLongError(len(text), MAX_TEXT_LENGTH)

        reminder_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        reminder = ReminderDB(
            id=reminder_id,
            owner_id=user.id,
            text=text,
            created_at=now,
            updated_at=now,
            expires_at=expires_at
        )

        reminder_repo.add(reminder)

        logger.info(f"Reminder created | Role={user.role_enum.name} | ReminderID={reminder.id}")

        return reminder
    
    @staticmethod
    def read_reminder(user: "UserDB", reminder_id: str, reminder_repo=None) -> "ReminderDB":
        """
        Retrieve a reminder by ID for the given user from the database.

        - Validates that the ID is a proper UUID.
        - Enforces authorization (deny-by-default).
        - Returns the ReminderDB object or None if it does not exist.

        Raises:
            MissingDataError: if db_session is missing
        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Validate UUID format
        ReminderService._validate_uuid(reminder_id)

        # 2️⃣ Fetch reminder from repository
        reminder = reminder_repo.get_by_id(reminder_id)
        if not reminder:
            return None

        # 3️⃣ Authorization: deny-by-default
        authorize(user, "read", resource_owner_id=reminder.owner_id)

        # 4️⃣ Logging for audit purposes
        logger.info(f"Reminder read | Role={user.role_enum.name} | ReminderID={reminder.id}")

        return reminder
    
    @staticmethod
    def update_reminder(user: "UserDB", reminder_id: str, new_text: str, reminder_repo=None) -> "ReminderDB":
        """
        Update the text of a reminder for the given user.

        - Validates UUID format.
        - Enforces authorization (deny-by-default).
        - Validates text length.
        - Persists changes using ReminderRepository.
        - Returns the updated ReminderDB object or None if not found.

        Raises:
            MissingDataError: if db_session is missing
            ReminderTextTooLongError: to validate lenght


        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Validate UUID format
        ReminderService._validate_uuid(reminder_id)

        # 2️⃣ Fetch reminder from repository
        reminder = reminder_repo.get_by_id(reminder_id)
        if not reminder:
            return None

        # 3️⃣ Authorization: deny-by-default
        authorize(user, "update", resource_owner_id=reminder.owner_id)

        # 4️⃣ Validate text length
        if len(new_text) > MAX_TEXT_LENGTH:
            raise ReminderTextTooLongError(len(new_text), MAX_TEXT_LENGTH)

        # 5️⃣ Update fields
        reminder.text = new_text
        reminder.updated_at = datetime.now(timezone.utc)

        # 6️⃣ Persist changes
        reminder_repo.add(reminder)  # add() will commit and refresh

        # 7️⃣ Logging for audit
        logger.info(f"Reminder updated | Role={user.role_enum.name} | ReminderID={reminder.id}")

        return reminder
    
    @staticmethod
    def delete_reminder(user: "UserDB", reminder_id: str, reminder_repo=None) -> bool:
        """
        Delete a reminder by ID for the given user.

        - Validates UUID format.
        - Enforces authorization (deny-by-default).
        - Deletes the reminder from the database.
        - Returns True if deleted, False if not found.

        Raises:
            MissingDataError: if db_session is missing
        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Validate UUID format
        ReminderService._validate_uuid(reminder_id)

        # 2️⃣ Fetch reminder from repository
        reminder = reminder_repo.get_by_id(reminder_id)
        if not reminder:
            return False

        # 3️⃣ Authorization: deny-by-default
        authorize(user, "delete", resource_owner_id=reminder.owner_id)

        # 4️⃣ Delete from database
        reminder_repo.delete(reminder)

        # 5️⃣ Logging for audit
        logger.info(f"Reminder deleted | Role={user.role_enum.name} | ReminderID={reminder.id}")

        return True
    
    @staticmethod
    def auto_delete_expired_reminders(reminder_repo=None):
        """
        Delete all expired reminders from the database.

        - Uses ReminderRepository to fetch and delete expired reminders.
        - Logs each deletion for auditing.

        Raises:
            MissingDataError: if db_session is missing
        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Delete expired reminders via repository
        expired = reminder_repo.delete_expired()
        for r in expired:
            logger.info(f"Expired reminder auto-deleted | ReminderID={r.id} | OwnerID={r.owner_id}")

    @staticmethod
    def list_reminders(user: "UserDB", reminder_repo=None):
        """
        List all active reminders for a given user.

        - Automatically deletes expired reminders before listing.
        - Returns a list of ReminderDB objects.

        Raises:
            MissingDataError: if db_session is missing
        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Auto-delete expired reminders
        ReminderService.auto_delete_expired_reminders(reminder_repo=reminder_repo)

        # 2️⃣ Fetch all reminders for the user
        reminders = reminder_repo.list_by_user(user.id)

        return reminders
    
    @staticmethod
    def parse_expiration(amount: int, unit: str, max_minutes: int = MAX_EXPIRATION_MINUTES) -> int:
        """
        Convert a time amount and unit to total minutes.

        - unit: "minutes", "hours", or "days" (case-insensitive)
        - amount must be positive and within max_minutes
        - Raises InvalidExpirationError for invalid units or out-of-range values
        """

        if amount < 1:
            raise InvalidExpirationError(amount, max_minutes, log_message=f"Expiration must be at least 1 {unit}")

        unit = unit.lower()
        if unit == "minutes":
            minutes = amount
        elif unit == "hours":
            minutes = amount * 60
        elif unit == "days":
            minutes = amount * 24 * 60
        else:
            raise InvalidExpirationError(amount, max_minutes, log_message=f"Invalid unit '{unit}'")

        if minutes > max_minutes:
            raise InvalidExpirationError(minutes, max_minutes)

        return minutes