from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from infrastructure.storage import Base
from core.security import Role
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON

"""
SQLAlchemy ORM models for the Epheminder application.

Includes:
- UserDB: users and roles
- ReminderDB: reminders with tags and expiration
- RefreshTokenDB: refresh tokens for session management
- LoginAttemptDB / RegisterAttemptDB: brute-force protection
- RevokedTokenDB: revoked JWT tokens

Used by repositories and services to persist and query application data.
"""

class UserDB(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)   # UUID
    username = Column(String(30), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    reminders = relationship("ReminderDB", back_populates="owner")

    @property
    def role_enum(self) -> Role:
        """Return the role as a Role Enum for runtime use, normalized and validated."""
        try:
            role_key = self.role.strip().upper()
            return Role[role_key]
        except KeyError:

            raise ValueError(f"Invalid role stored in DB: '{self.role}'")

    def __repr__(self):
        return f"<UserDB(id={self.id}, username={self.username}, role={self.role}, active={self.is_active})>"

class ReminderDB(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)   # UUID
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)

    owner = relationship("UserDB", back_populates="reminders")

class RefreshTokenDB(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # ⚡ RELATIONSHIP WITH USER
    user = relationship("UserDB", backref="refresh_tokens")
     
class LoginAttemptDB(Base):
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ip = Column(String(50), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    lock_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
class RegisterAttemptDB(Base):
    __tablename__ = "register_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(30), nullable=False)
    ip = Column(String(50), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    lock_until = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<LoginAttempt(user_id={self.user_id}, ip={self.ip}, attempts={self.attempts}, lock_until={self.lock_until})>"
    
class RevokedTokenDB(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String, primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False) 