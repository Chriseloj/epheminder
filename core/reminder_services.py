import uuid
import logging
from datetime import datetime, timedelta, timezone
from core.models import UserDB, ReminderDB
from core.security import authorize
from core.exceptions import (MissingDataError,
ReminderTextTooLongError,
InvalidExpirationError,
InvalidUUIDError,
MaxRemindersReachedError,
)
from config import MAX_EXPIRATION_MINUTES, MAX_TEXT_LENGTH, MAX_REMINDERS_PER_USER

logger = logging.getLogger(__name__)

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
        logger.info(
            "Reminder read | Role= %s | ReminderID= %s",
            user.role_enum.name,
            reminder.id
        )
        
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
    def _check_max_reminders(user, reminder_repo):
        # Check maximum reminders per user
        current_count = len(ReminderService.list_reminders(user, reminder_repo=reminder_repo))
        if current_count >= MAX_REMINDERS_PER_USER:
            raise MaxRemindersReachedError(MAX_REMINDERS_PER_USER)
    
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
        
        ReminderService._check_max_reminders(user, reminder_repo)

        authorize(user, "create", resource_owner_id=user.id)

        expires_in_minutes = ReminderService.parse_expiration(amount, unit)

        if len(text) > MAX_TEXT_LENGTH:
            raise ReminderTextTooLongError(len(text), MAX_TEXT_LENGTH)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        reminder_id = uuid.uuid4()
        reminder = ReminderDB(
            id=reminder_id,
            owner_id=user.id,  # user.id is UUID
            text=text,
            created_at=now,
            updated_at=now,
            expires_at=expires_at
        )

        reminder_repo.add(reminder)

        logger.info(
            "Reminder created | Role= %s | ReminderID= %s",
            user.role_enum.name,
            reminder.id
        )

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
        logger.info(
            "Reminder read | Role= %s | ReminderID= %s",
            user.role_enum.name, 
            reminder.id
        )

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
        logger.info(
            "Reminder updated | Role= %s | ReminderID= %s",
            user.role_enum.name,
            reminder.id
        )

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
        logger.info(
            "Reminder deleted | Role= %s | ReminderID= %s",
            user.role_enum.name,
            reminder.id
        )

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
            logger.info(
                "Auto-deleted reminders | count= %s",
                count
            )

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
        Convert expiration amount and unit to minutes.

        Validation is performed in the same unit provided by the user
        to produce clearer error messages.
        """

        unit = unit.lower()

        limits = {
            "minutes": {
                "min": 1,
                "max": max_minutes,
                "multiplier": 1
            },
            "hours": {
                "min": 1,
                "max": max_minutes // 60,
                "multiplier": 60
            },
            "days": {
                "min": 1,
                "max": max_minutes // 1440,
                "multiplier": 1440
            }
        }

        if unit not in limits:
            raise InvalidExpirationError(
                amount,
                max_minutes,
                log_message=f"Invalid unit '{unit}'"
            )

        min_value = limits[unit]["min"]
        max_value = limits[unit]["max"]
        multiplier = limits[unit]["multiplier"]

        if amount < min_value or amount > max_value:
            raise InvalidExpirationError(
                amount,
                max_value,
                log_message=f"{unit} must be between {min_value} and {max_value}"
            )

        return amount * multiplier
    
EXPIRATION_RULES = {
    "minutes": (1, MAX_EXPIRATION_MINUTES, 1),
    "hours": (1, MAX_EXPIRATION_MINUTES // 60, 60),
    "days": (1, MAX_EXPIRATION_MINUTES // 1440, 1440),
}