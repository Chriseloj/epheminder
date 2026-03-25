import logging
from config import (
    MAX_REMINDERS_PER_USER,
    MAX_TEXT_LENGTH,
    MAX_EXPIRATION_MINUTES,
    MIN_LENGTH,
    MIN_UPPER,
    MIN_LOWER,
    MIN_DIGITS,
    MIN_SYMBOLS,
    SYMBOLS,
    MAX_ATTEMPTS,
    RATE_LIMIT_SECONDS,
)
from core.hash_utils import hash_sensitive
logger = logging.getLogger(__name__)

# ------------------------------
# Base Reminder Error
# ------------------------------
class ReminderError(Exception):
    """Base class for reminder-related errors"""
    def __init__(self, log_message: str = "An error occurred with the reminder"):
        super().__init__(log_message)
        self.public_message = "An unexpected error occurred while processing the reminder"
        logger.error(log_message) 

# ------------------------------
# Permission & Authentication
# ------------------------------
class PermissionDeniedError(ReminderError):
    """Raised when a user tries to perform an action without proper permissions"""
    def __init__(self, role: str, action: str, log_message: str = None):
        self.role = role
        self.action = action
        if log_message is None:
            log_message = "Permission denied"
        super().__init__(log_message)
        self.public_message = "You do not have permission to perform this action"

class AuthenticationRequiredError(ReminderError):
    """Raised when authentication is required to perform an action"""
    def __init__(self, log_message: str = "Authentication required"):
        super().__init__(log_message)
        self.public_message = "Authentication is required to perform this action"

# ------------------------------
# Reminder-specific Errors
# ------------------------------
class ReminderTextTooLongError(ReminderError):
    """Raised when the reminder text exceeds maximum allowed length"""
    def __init__(self, length: int | None = None, log_message: str = None):
        self.length = length
        self.max_length = MAX_TEXT_LENGTH
        if log_message is None:
            if length is not None:
                log_message = f"Reminder text exceeded max length: {self.max_length}"
            else:
                log_message = f"Reminder text too long (max {self.max_length})"
        super().__init__(log_message)
        self.public_message = f"Reminder text exceeds {self.max_length} characters"

class InvalidExpirationError(ReminderError):
    """Raised when a reminder expiration is invalid (0, negative, or exceeds max allowed)"""
    def __init__(self, minutes: int, max_minutes: int = MAX_EXPIRATION_MINUTES, log_message: str = None):
        self.minutes = minutes
        self.max_minutes = max_minutes
        if log_message is None:
            log_message = f"Invalid expiration time: {minutes} minutes. Allowed: 1-{max_minutes} minutes"
        super().__init__(log_message)
        self.public_message = f"Expiration must be between 1 and {self.max_minutes} minutes"

class MaxRemindersReachedError(ReminderError):
    """Raised when user exceeds max number of reminders"""
    def __init__(self, max_reminders_per_user: int = MAX_REMINDERS_PER_USER, log_message: str = None):
        self.max_reminders_per_user = max_reminders_per_user
        if log_message is None:
            log_message = f"User attempted to exceed max reminders ({max_reminders_per_user})"
        super().__init__(log_message)
        self.public_message = f"You have reached the maximum of {self.max_reminders_per_user} reminders."

class MissingDataError(ReminderError):
    """Raised when repository/db is missing"""
    def __init__(self, log_message: str = "An error occurred with the reminder"):
        super().__init__(log_message)
        self.public_message = "Internal error: missing reminder repository"

# ------------------------------
# User/Authentication Errors
# ------------------------------
class InvalidPasswordError(ReminderError):
    """Raised when a password does not meet security requirements"""
    def __init__(self, log_message: str = None):
        if log_message is None:
            log_message = (
                f"Password must be at least {MIN_LENGTH} characters, "
                f"include {MIN_UPPER} uppercase, {MIN_LOWER} lowercase, "
                f"{MIN_DIGITS} digits, and {MIN_SYMBOLS} symbols from {SYMBOLS}"
            )
        super().__init__(log_message)
        self.public_message =  (
            f"Password must be at least {MIN_LENGTH} characters and include "
            f"{MIN_UPPER} uppercase, {MIN_LOWER} lowercase, {MIN_DIGITS} digit(s), and {MIN_SYMBOLS} symbol(s)."
        )

class InvalidUserError(ReminderError):
    """Raised when the username is invalid"""
    def __init__(
        self,
        username: str,
        reason: str = "Username must be 3-30 characters and contain only letters and numbers",
        log_message: str = None
    ):
        self.username = username
        self.reason = reason

        # Internal log message
        if log_message is None:
            log_message = f"Invalid username attempt: {username}"

        super().__init__(log_message)

        # Message safe for the user
        self.public_message = f"Invalid username '{username}': {reason}"
        
class UsernameTakenError(ReminderError):
    """Raised when trying to register an existing username"""
    def __init__(self, username: str, log_message: str = None):
        self.username = username
        if log_message is None:
            log_message = f"Attempt to register already taken username: {hash_sensitive(username)}"
        super().__init__(log_message)
        self.public_message = "Invalid credentials"

class InvalidUUIDError(ReminderError):
    """Raised when a UUID string is invalid"""
    def __init__(self, uuid_str: str, log_message: str = None):
        self.uuid_str = uuid_str
        if log_message is None:
            log_message = f"Invalid UUID format detected: {hash_sensitive(uuid_str)}"
        super().__init__(log_message)
        self.public_message = "Identifier is invalid"

# ------------------------------
# Optional: Rate limiting / login errors
# ------------------------------
class MaxLoginAttemptsError(ReminderError):
    """Raised when user exceeds login attempts"""
    def __init__(self, max_attempts: int = MAX_ATTEMPTS, log_message: str = None):
        if log_message is None:
            log_message = f"Maximum login attempts ({max_attempts}) reached. Try again later."
        super().__init__(log_message)
        self.public_message = "Too many login attempts. Please try again later"

class RateLimitExceededError(ReminderError):
    """Raised when rate-limited"""
    def __init__(self, rate_limit_seconds: int = RATE_LIMIT_SECONDS, log_message: str = None):
        if log_message is None:
            log_message = f"Action blocked due to rate limit ({rate_limit_seconds}s)."
        super().__init__(log_message)
        self.public_message = f"Please wait {rate_limit_seconds} seconds before retrying"

# ------------------------------
# USER EXISTS
# ------------------------------

class UserAlreadyExistsError(ReminderError):
    """Raised when trying to register a user that already exists."""
    def __init__(self, username: str, log_message: str = None):
        self.username = username

        if log_message is None:
            log_message = "Attempt to register already taken username"

        super().__init__(log_message)

        self.public_message = "Invalid credentials"

# ------------------------------
# REMINDER NOT FOUND
# ------------------------------

class ReminderNotFoundError(ReminderError):
    """Raised when a reminder is not found"""
    def __init__(self, reminder_id: int, log_message: str = None):
        self.reminder_id = reminder_id
        if log_message is None:
            log_message = f"Reminder not found: {reminder_id}"
        super().__init__(log_message)
        self.public_message = "Reminder not found."

# ------------------------------
# INVALID CREDENTIAL
# ------------------------------

class InvalidCredentialsError(ReminderError):
    def __init__(self, log_message: str = "Invalid credentials"):
        super().__init__(log_message)
        self.public_message = "Invalid username or password"