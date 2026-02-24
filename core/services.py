import uuid
import logging
from datetime import datetime, timedelta, timezone
from core.models import UserDB, ReminderDB, RegisterAttemptDB
from core.security import authorize, Role
from core.exceptions import (MissingDataError,
ReminderTextTooLongError,
InvalidExpirationError,
InvalidUserError,
UsernameTakenError,
InvalidUUIDError,
MaxRemindersReachedError,
AuthenticationRequiredError)
from core.passwords import validate_password, hash_password
from config import MAX_EXPIRATION_MINUTES, MAX_TEXT_LENGTH, MAX_REMINDERS_PER_USER
from infrastructure.repositories import UserRepository
from core.protection import check_rate_limit, apply_backoff, reset_attempts
from functools import wraps
from core.protection import (
    check_register_rate_limit,
    apply_register_backoff,
    reset_register_attempts
)

logger = logging.getLogger(__name__)

def rate_limited(user_param: str, ip_param: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            user_id = kwargs.get(user_param)
            ip = kwargs.get(ip_param)
            db_session = kwargs.get("db_session")

            if not db_session:
                raise ValueError("db_session is required")

            # username to UUID
            if isinstance(user_id, str):
                user_obj = db_session.query(UserDB).filter_by(username=user_id).first()
                
                if user_obj:

                    user_id = user_obj.id

                else:
    
                    user_id = user_id 

            check_rate_limit(user_id, ip, db_session=db_session)
    
            try:
                result = func(*args, **kwargs)
            except Exception:
                apply_backoff(user_id, ip, db_session=db_session)
                raise
            else:
                reset_attempts(user_id, ip, db_session=db_session)
                return result
        return wrapper
    return decorator

def register_rate_limited(user_param: str, ip_param: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = kwargs.get(user_param)
            ip = kwargs.get(ip_param)
            db_session = kwargs.get("db_session")

            if not db_session:
                raise ValueError("db_session is required")

            check_register_rate_limit(username, ip, db_session)

            try:
                result = func(*args, **kwargs)
            except Exception:
                apply_register_backoff(username, ip, db_session)
                raise
            else:
                reset_register_attempts(username, ip, db_session)
                return result

        return wrapper
    return decorator

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

        # save
        repo.add(user)

        logger.info(f"User created | Username={username} | Role={user.role} | ID={user_id}")

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
        Create a new reminder for a given user.

        - Validates reminder text length against MAX_TEXT_LENGTH.
        - Ensures the user does not exceed the maximum number of reminders.
        - Converts expiration time (amount + unit) into total minutes.
        - Generates a unique UUID for the reminder.
        - Sets created_at, updated_at, and expires_at timestamps automatically.
        - Persists the reminder in the provided repository.
        - Enforces deny-by-default authorization (user can only create reminders for themselves).
        - Logs creation for auditing purposes.

        Args:
            user (UserDB): The user creating the reminder.
            text (str): Content of the reminder.
            amount (int): Quantity of time for expiration.
            unit (str): Unit of time ("minutes", "hours", "days").
            reminder_repo: Reminder repository instance. Required.

        Returns:
            ReminderDB: The newly created reminder object.

        Raises:
            MissingDataError: If reminder_repo is not provided.
            InvalidExpirationError: If the expiration amount or unit is invalid.
            ReminderTextTooLongError: If the text exceeds MAX_TEXT_LENGTH.
            MaxRemindersReachedError: If the user already has the maximum allowed reminders.
        """

        if reminder_repo is None:
            raise MissingDataError()

        # Check maximum reminders per user
        current_count = len(ReminderService.list_reminders(user, reminder_repo=reminder_repo))
        if current_count >= MAX_REMINDERS_PER_USER:
            raise MaxRemindersReachedError(MAX_REMINDERS_PER_USER)

        authorize(user, "create", resource_owner_id=user.id)

        expires_in_minutes = ReminderService.parse_expiration(amount, unit)

        if len(text) > MAX_TEXT_LENGTH:
            raise ReminderTextTooLongError(len(text), MAX_TEXT_LENGTH)

        reminder_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        reminder_id = uuid.uuid4()  # without str()
        reminder = ReminderDB(
            id=reminder_id,
            owner_id=user.id,  # user.id is UUID
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
        reminder_uuid = uuid.UUID(reminder_id)
        reminder = reminder_repo.get_by_id(reminder_uuid)

        # 2️⃣ Fetch reminder from repository
    
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
        Update the text of an existing reminder for the given user.

        - Validates that `reminder_id` is a proper UUID.
        - Enforces deny-by-default authorization (user can only update their own reminders).
        - Validates that the new text does not exceed MAX_TEXT_LENGTH.
        - Updates the reminder's text and automatically sets `updated_at` to the current UTC time.
        - Persists changes via the provided repository.
        - Logs the update for auditing purposes.

        Args:
            user (UserDB): The user updating the reminder.
            reminder_id (str): UUID of the reminder to update.
            new_text (str): The updated reminder text.
            reminder_repo: Reminder repository instance. Required.

        Returns:
            ReminderDB: The updated reminder object if found.
            None: If the reminder does not exist.

        Raises:
            MissingDataError: If `reminder_repo` is not provided.
            ReminderTextTooLongError: If `new_text` exceeds MAX_TEXT_LENGTH.

        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Validate UUID format
        ReminderService._validate_uuid(reminder_id)
        reminder_uuid = uuid.UUID(reminder_id)
        reminder = reminder_repo.get_by_id(reminder_uuid)

        # 2️⃣ Fetch reminder from repository
        
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
        Delete a reminder by its ID for the given user.

        - Validates that `reminder_id` is a proper UUID.
        - Enforces deny-by-default authorization (user can only delete their own reminders).
        - Deletes the reminder from the repository.
        - Logs the deletion for auditing purposes.

        Args:
            user (UserDB): The user attempting to delete the reminder.
            reminder_id (str): UUID of the reminder to delete.
            reminder_repo: Reminder repository instance. Required.

        Returns:
            bool: True if the reminder was deleted, False if the reminder was not found.

        Raises:
            MissingDataError: If `reminder_repo` is not provided.
        """

        if reminder_repo is None:
            raise MissingDataError()

        # 1️⃣ Validate UUID format
        ReminderService._validate_uuid(reminder_id)
        reminder_uuid = uuid.UUID(reminder_id)
        reminder = reminder_repo.get_by_id(reminder_uuid)

        # 2️⃣ Fetch reminder from repository
        
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
        - Logs deletion for auditing purposes without exposing sensitive info.
    
        Returns:
            int: Number of reminders deleted.

        Raises:
            MissingDataError: if reminder_repo is missing
        """

        if reminder_repo is None:
            raise MissingDataError()

        # Delete expired reminders via repository
        expired = reminder_repo.delete_expired()
        count = len(expired)

        # Log generic info without sensitive data
        if count:
            logger.info(f"Auto-deleted {count} expired reminders.")

        return expired

    @staticmethod
    def list_reminders(user: "UserDB", reminder_repo=None):
        """
        Retrieve all active reminders for a given user.

        This method fetches all reminders associated with the specified user
        and filters out any reminders that have already expired. Expired
        reminders are determined by comparing the `expires_at` timestamp
        against the current UTC time. Both timezone-aware and naive
        datetimes are supported for compatibility with older records.

        Args:
            user (UserDB): The user whose reminders are being retrieved.
            reminder_repo: An instance of ReminderRepository used to fetch
                        reminders from the database. Raises MissingDataError
                        if not provided.

        Returns:
            List[ReminderDB]: A list of ReminderDB objects representing
                                all active (non-expired) reminders for the user.

        Raises:
            MissingDataError: If `reminder_repo` is not provided.
        """
        
        if reminder_repo is None:
            raise MissingDataError()

        reminders = reminder_repo.list_by_user(user.id)
        now = datetime.now(timezone.utc)  # aware

        # Return only non-expired reminders
        active = [
            r for r in reminders 
            if r.expires_at and r.expires_at.replace(tzinfo=timezone.utc) > now
        ]
        return active
    
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