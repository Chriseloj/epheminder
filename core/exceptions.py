class ReminderError(Exception):
    """Base class for reminder-related errors"""
    def __init__(self, log_message: str = "An error occurred with the reminder"):
        super().__init__(log_message)
        self.public_message = "An unexpected error occurred while processing the reminder"

class PermissionDeniedError(ReminderError):
    """Raised when a user tries to perform an action without the proper permissions"""
    def __init__(self, role: str, action: str, log_message: str = None):
        self.role = role
        self.action = action
        if log_message is None:
            log_message = f"Permission denied for role '{role}' to perform '{action}'"
        super().__init__(log_message)
        self.public_message = "You do not have permission to perform this action"


class InvalidExpirationError(ReminderError):
    """Raised when the expiration time of a reminder is invalid (too long, zero, or negative)"""
    def __init__(self, minutes: int, max_minutes: int = 7*24*60, log_message: str = None):
        self.minutes = minutes
        self.max_minutes = max_minutes
        if log_message is None:
            log_message = f"Invalid expiration time: {minutes} minute(s). Allowed range: 1-{max_minutes} minutes"
        super().__init__(log_message)
        self.public_message = "Expiration time is not valid"


class ReminderTextTooLongError(ReminderError):
    """Raised when the reminder text exceeds the maximum allowed length"""
    def __init__(self, length: int, max_length: int = 100, log_message: str = None):
        self.length = length
        self.max_length = max_length
        if log_message is None:
            log_message = f"Reminder text too long: {length} characters (max {max_length})"
        super().__init__(log_message)
        self.public_message = "Reminder text is too long"

class AuthenticationRequiredError(ReminderError):
    def __init__(self, log_message: str = "Authentication required"):
        super().__init__(log_message)
        self.public_message = "Authentication is required to perform this action"

class InvalidPasswordError(ReminderError):
    """Raised when a password does not meet security requirements."""
    pass

class InvalidUserError(ReminderError):
    """Raised when a username is invalid (length, characters, etc.)"""
    def __init__(self, username: str, reason: str = "Invalid username", log_message: str = None):
        self.username = username
        self.reason = reason
        if log_message is None:
            log_message = f"Invalid username attempt: {username}, reason: {reason}"  
        super().__init__(log_message)
        self.public_message = "Invalid credentials"


class UsernameTakenError(ReminderError):
    """Raised when trying to create a user with a username that already exists"""
    def __init__(self, username: str, log_message: str = None):
        self.username = username
        if log_message is None:
            log_message = f"Attempt to register already taken username: {username}"
        super().__init__(log_message)
        self.public_message = "Invalid credentials"


class InvalidUUIDError(ReminderError):
    """Raised when a UUID string is not valid"""
    def __init__(self, uuid_str: str, log_message: str = None):
        self.uuid_str = uuid_str
        if log_message is None:
            log_message = f"Invalid UUID format detected: {uuid_str}"
        super().__init__(log_message)
        self.public_message = "Identifier is invalid"

class MissingDataError(ReminderError):
    "Raised when db is missing"
    def __init__(self, log_message: str = "An error occurred with the reminder"):
                    
        super().__init__(log_message)
        self.public_message = "Internal error: missing reminder repository"

class MaxRemindersReachedError(ReminderError):
    """Raised when a user tries to create more reminders than allowed."""
    
    def __init__(self, log_message: str = "User attempted to exceed max reminders"):
        super().__init__(log_message)
        self.public_message = "You have reached the maximum number of allowed reminders"