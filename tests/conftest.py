import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.storage import Base
from infrastructure.repositories import UserRepository, ReminderRepository
from core.models import UserDB
from core.security import Role
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from core.models import ReminderDB 

import os
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
import core.protection as protection

@pytest.fixture
def ip():
    return "127.0.0.1"

# ---------------------------
# DATABASE (isolated per test)
# ---------------------------

@pytest.fixture(scope="function")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()  # 🔹 Force all close conections


@pytest.fixture(scope="function")
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# ---------------------------
# REPOSITORIES
# ---------------------------

@pytest.fixture
def user_repo(db_session):
    return UserRepository(db_session)


@pytest.fixture
def reminder_repo(db_session):
    return ReminderRepository(db_session)


# ---------------------------
# GLOBAL STATE CLEANUP
# ---------------------------

@pytest.fixture(autouse=True)
def mock_redis_client(monkeypatch):
    fake_client = MagicMock()
    fake_client.get.return_value = None
    fake_client.incr.return_value = 1
    fake_client.set.return_value = True
    fake_client.delete.return_value = True
    monkeypatch.setattr(protection, "get_redis_client", lambda: fake_client)
    monkeypatch.setattr(protection, "r", fake_client)
    return fake_client

@pytest.fixture(autouse=True)
def reset_fake_redis(mock_redis_client):
    mock_redis_client.reset_mock()
    yield

# ---------------------------
# SAMPLE USERS
# ---------------------------

@pytest.fixture
def user(db_session, user_repo):
    user = UserDB(
        id="11111111-1111-1111-1111-111111111111",
        username="testuser",
        password_hash="fakehash",
        role=Role.USER.name,
        is_active=True,
    )
    user_repo.add(user)
    return user


@pytest.fixture
def admin(db_session, user_repo):
    admin = UserDB(
        id="22222222-2222-2222-2222-222222222222",
        username="adminuser",
        password_hash="fakehash",
        role=Role.ADMIN.name,
        is_active=True,
    )
    user_repo.add(admin)
    return admin


@pytest.fixture
def reminders(user, reminder_repo):
    reminders = []
    for i in range(3):
        reminder = ReminderDB(
            id=str(i),
            owner_id=user.id,
            text=f"Reminder {i}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        reminder_repo.add(reminder)
        reminders.append(reminder)
    return reminders