import os

os.environ["SECRET_KEY"] = "a" * 64
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from core.models import Base, UserDB, ReminderDB, RefreshTokenDB
from core.passwords import hash_password
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

# ------------------------
# ENGINE
# ------------------------
@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

# ------------------------
# SESSION PER TEST
# ------------------------
@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans.parent and sess.is_active:
            sess.begin_nested()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()

# ------------------------
# FIXTURES
# ------------------------
@pytest.fixture
def sample_user(db_session):
    user = UserDB(
        username="testuser",
        role="USER",
        is_active=True,
        password_hash=hash_password("Password_0ne_hash")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def sample_reminder(db_session, sample_user):
    reminder = ReminderDB(
        text="Recordatorio de prueba",
        owner=sample_user,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(reminder)
    db_session.commit()
    return reminder

@pytest.fixture
def sample_refresh_token(db_session, sample_user):
    token = RefreshTokenDB(
        user_id=sample_user.id,
        token_hash="sampletokenhash",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        revoked=False,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(token)
    db_session.commit()
    return token

# ------------------------
# DISABLE RATE LIMITING GLOBAL
# ------------------------
@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    
    def passthrough_decorator(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper

    monkeypatch.setattr(
        "core.authentication_service.rate_limited",
        passthrough_decorator
    )

# ------------------------
# DISABLE RATE LIMITING GLOBAL PARA REGISTRATION
# ------------------------
@pytest.fixture(autouse=True)
def disable_rate_limiting_registration(monkeypatch):
    def passthrough_decorator(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper
    monkeypatch.setattr(
        "core.decorators.register_rate_limited",  # decorador register
        passthrough_decorator
    )


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test_secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")