import os
# -----------------------------
# Set environment variables
# -----------------------------
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "supersecretkey_muy_segura_32chars!")

import pytest
import uuid
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.storage import Base
from infrastructure.repositories import UserRepository, ReminderRepository
from core.models import UserDB, ReminderDB
from core.security import Role

# -----------------------------
# IP Fixture
# -----------------------------
@pytest.fixture
def ip():
    return "127.0.0.1"

# -----------------------------
# DATABASE (isolated per test)
# -----------------------------
@pytest.fixture(scope="function")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

# -----------------------------
# REPOSITORIES
# -----------------------------
@pytest.fixture
def user_repo(db_session):
    return UserRepository(db_session)

@pytest.fixture
def reminder_repo(db_session):
    return ReminderRepository(db_session)

# ---------------------------------------------
# REDIS MOCK (tests)
# ---------------------------------------------
@pytest.fixture(autouse=True)
def mock_redis_client(monkeypatch):
    store = {}
    mock_redis = MagicMock()

    mock_redis.get.side_effect = lambda k: store.get(k)

    def set_side_effect(k, v, ex=None, nx=False):
        if nx and k in store:
            return False
        store[k] = v
        return True
    mock_redis.set.side_effect = set_side_effect

    def incr_side_effect(k):
        store[k] = str(int(store.get(k, "0")) + 1)
        return int(store[k])
    mock_redis.incr.side_effect = incr_side_effect

    mock_redis.delete.side_effect = lambda k: store.pop(k, None)
    mock_redis.expire.side_effect = lambda k, s: True

    import core.protection as protection
    import core.middleware as middleware

    monkeypatch.setattr(protection, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(middleware, "get_redis", lambda: mock_redis)

    return mock_redis

# -----------------------------
# Reset mock after each test
# -----------------------------
@pytest.fixture(autouse=True)
def reset_fake_redis(mock_redis_client):
    mock_redis_client.reset_mock()
    yield

# -----------------------------
# SAMPLE USERS
# -----------------------------
@pytest.fixture
def user(db_session, user_repo):
    user = UserDB(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
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
        id=uuid.UUID("22222222-2222-2222-222222222222"),
        username="adminuser",
        password_hash="fakehash",
        role=Role.ADMIN.name,
        is_active=True,
    )
    user_repo.add(admin)
    return admin

@pytest.fixture
def reminders(user, reminder_repo):
    reminders_list = []
    for i in range(3):
        reminder = ReminderDB(
            id=uuid.uuid4(),
            owner_id=user.id,
            text=f"Reminder {i+1}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        reminder_repo.add(reminder)
        reminders_list.append(reminder)
    return reminders_list
# -----------------------------
# DISABLE RATE LIMIT FOR TESTS
# -----------------------------
@pytest.fixture(autouse=True)
def disable_rate_limit(monkeypatch):
    monkeypatch.setattr("core.services.check_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr("core.authentication.check_rate_limit", lambda *a, **k: None)