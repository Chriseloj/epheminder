import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.storage import Base
from infrastructure.repositories import UserRepository, ReminderRepository
from core.models import UserDB
from core.security import Role
from core.protection import FAILED_ATTEMPTS


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


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()  

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
def clean_failed_attempts():
    FAILED_ATTEMPTS.clear()
    yield
    FAILED_ATTEMPTS.clear()


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