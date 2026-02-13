from datetime import datetime, timedelta
from core.security import Role
from core.exceptions import ReminderTextTooLongError

class Reminder:
    MAX_TEXT_LENGTH = 100
    MAX_EXPIRATION_DAYS = 7 * 24 * 60 

    def __init__(self, owner_id, text: str, expires_in_minutes: int):
        if len(text) > self.MAX_TEXT_LENGTH:
            raise ReminderTextTooLongError(len(text), self.MAX_TEXT_LENGTH)
        
        self.owner_id = owner_id
        self.text = text
        self.created_at = datetime.now()

        requested_expiration = timedelta(minutes=expires_in_minutes)

        self.expires_at = self.created_at + requested_expiration

class User:
    def __init__(self, user_id, role: Role):
        self.user_id = user_id        
        self.role = role 