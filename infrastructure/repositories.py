from sqlalchemy.orm import Session
from core.models import UserDB, ReminderDB
from datetime import datetime, timezone

class UserRepository:
    """
    Repository for interacting with the `UserDB` table.

    Responsibilities:
    - Add new users or persist updates to existing users.
    - Fetch users by ID or username.

    Args:
        db (Session): SQLAlchemy session instance.
    """

    def __init__(self, db: Session):
        self.db = db

    def add(self, user: UserDB):
        """
        Persist a new user or update an existing one.

        - Commits the transaction and refreshes the user object from the DB.
        - Does not enforce business rules (e.g., unique username), which are handled elsewhere.

        Args:
            user (UserDB): The user object to persist.

        Returns:
            UserDB: The persisted user with updated fields (e.g., ID, timestamps).
        """

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str):
        """
        Retrieve a user by their UUID.

        Args:
            user_id (str): UUID of the user to fetch.

        Returns:
            UserDB | None: The user object if found, else None.
        """

        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        return user

    def get_by_username(self, username: str):
        """
        Retrieve a user by username.

        Args:
            username (str): The username to search for.

        Returns:
            UserDB | None: The user object if found, else None.
        """
        return self.db.query(UserDB).filter(UserDB.username == username).first()


class ReminderRepository:
    """
    Repository for interacting with the `ReminderDB` table.

    Responsibilities:
    - Persist new reminders and updates.
    - Fetch reminders by ID or by user.
    - Count, list, and delete reminders.
    - Delete expired reminders efficiently.

    Args:
        db (Session): SQLAlchemy session instance.
    """

    def __init__(self, db: Session):
        self.db = db

    def add(self, reminder: ReminderDB):
        """
        Persist a new reminder or update an existing one.

        - Commits the transaction and refreshes the reminder object.
        - Business rules (max reminders, text length, expiration) are handled by ReminderService.

        Args:
            reminder (ReminderDB): Reminder object to persist.

        Returns:
            ReminderDB: The persisted reminder object.
        """
        
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_by_id(self, reminder_id: str):
        """
        Retrieve a reminder by UUID.

        Args:
            reminder_id (str): UUID of the reminder to fetch.

        Returns:
            ReminderDB | None: The reminder object if found, else None.
        """

        return self.db.query(ReminderDB).filter(ReminderDB.id == reminder_id).first()
    
    def count_by_user(self, user_id: str) -> int:
        """
        Count the total number of reminders for a given user.

        - Used to enforce MAX_REMINDERS_PER_USER in ReminderService.

        Args:
            user_id (str): UUID of the user.

        Returns:
            int: Number of reminders owned by the user.
        """

        return self.db.query(ReminderDB).filter(ReminderDB.owner_id == user_id).count()

    def list_by_user(self, user_id: str):
        """
        List all reminders for a given user.

        Args:
            user_id (str): UUID of the user.

        Returns:
            list[ReminderDB]: List of all reminders owned by the user.
        """

        return self.db.query(ReminderDB).filter(ReminderDB.owner_id == user_id).all()

    def delete(self, reminder: ReminderDB):
        """
        Delete a specific reminder from the database.

        Args:
            reminder (ReminderDB): Reminder object to delete.
        """

        self.db.delete(reminder)
        self.db.commit()

    def delete_expired(self, now=None):
        """
        Delete all reminders that have expired.

        - Uses current UTC time if `now` is not provided.
        - Returns a list of deleted reminders for auditing/logging purposes.

        Args:
            now (datetime, optional): Reference datetime for checking expiration.

        Returns:
            list[ReminderDB]: List of reminders that were deleted.
        """

    
        if now is None:
            now = datetime.now(timezone.utc)

        expired = self.db.query(ReminderDB).filter(ReminderDB.expires_at <= now).all()
    
        for r in expired:
            self.db.delete(r)
        self.db.commit()
        return expired