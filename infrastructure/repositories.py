from sqlalchemy.orm import Session
from core.models import UserDB, ReminderDB
from datetime import datetime, timezone

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user: UserDB):
        """
        Add a new reminder or persist updates to an existing one.
        Works for both create and update operations.
        """
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str):
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if user:
            user.role = user.role_enum  # Transform string to Enum
        return user

    def get_by_username(self, username: str):
        return self.db.query(UserDB).filter(UserDB.username == username).first()


class ReminderRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, reminder: ReminderDB):
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_by_id(self, reminder_id: str):
        return self.db.query(ReminderDB).filter(ReminderDB.id == reminder_id).first()

    def list_by_user(self, user_id: str):
        return self.db.query(ReminderDB).filter(ReminderDB.owner_id == user_id).all()

    def delete(self, reminder: ReminderDB):
        self.db.delete(reminder)
        self.db.commit()

    def delete_expired(self):
    
        expired = self.db.query(ReminderDB).filter(ReminderDB.expires_at <= datetime.now(timezone.utc)).all()
        for r in expired:
            self.db.delete(r)
        self.db.commit()
        return expired