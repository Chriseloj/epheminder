class ReminderError(Exception):
    """Base class for reminder-related errors"""
    def __init__(self, message: str = "An error occurred with the reminder"):
        super().__init__(message)


class PermissionDeniedError(ReminderError):
    """Raised when a user tries to perform an action without the proper permissions"""
    def __init__(self, role: str, action: str, message: str = None):
        self.role = role
        self.action = action
        if message is None:
            message = f"Permission denied for role '{role}' to perform '{action}'"
        super().__init__(message)


class InvalidExpirationError(ReminderError):
    """Raised when the expiration time of a reminder is invalid (too long, zero, or negative)"""
    def __init__(self, minutes: int, max_minutes: int = 7*24*60, message: str = None):
        self.minutes = minutes
        self.max_minutes = max_minutes
        if message is None:
            message = f"Invalid expiration time: {minutes} minute(s). Must be between 1 and {max_minutes}"
        super().__init__(message)


class ReminderTextTooLongError(ReminderError):
    """Raised when the reminder text exceeds the maximum allowed length"""
    def __init__(self, length: int, max_length: int = 100, message: str = None):
        self.length = length
        self.max_length = max_length
        if message is None:
            message = f"Reminder text too long: {length} characters (max {max_length})"
        super().__init__(message)