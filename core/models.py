from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from infrastructure.storage import Base
from core.security import Role

class UserDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # UUID
    username = Column(String(30), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reminders = relationship("ReminderDB", back_populates="owner")

    @property
    def role_enum(self) -> Role:
        """Return the role as a Role Enum for runtime use."""
        return Role[self.role]

    def __repr__(self):
        return f"<UserDB(id={self.id}, username={self.username}, role={self.role}, active={self.is_active})>"

class ReminderDB(Base):
    __tablename__ = "reminders"

    id = Column(String, primary_key=True)  # UUID
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)

    owner = relationship("UserDB", back_populates="reminders")