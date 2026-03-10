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
        return user

    def get_by_username(self, username: str):
        return self.db.query(UserDB).filter(UserDB.username == username).first()


class ReminderRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, reminder: ReminderDB):
        """
        Persist a new reminder or update an existing one in the database.

        This method handles saving the reminder object to the database and 
        refreshing it after commit. It does NOT enforce business rules 
        such as maximum reminders per user or text length validation — 
        those are handled by the ReminderService.

        Args:
            reminder (ReminderDB): The reminder object to be persisted.

        Returns:
            ReminderDB: The persisted reminder object with updated state 
                        from the database (e.g., timestamps, IDs).
    """
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

    def delete_expired(self, now=None):
    
        if now is None:
            now = datetime.now(timezone.utc)

        expired = self.db.query(ReminderDB).filter(ReminderDB.expires_at <= now).all()
    
        for r in expired:
            self.db.delete(r)
        self.db.commit()
        return expired