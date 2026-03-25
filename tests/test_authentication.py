import pytest
from unittest.mock import Mock, patch
from core.models import UserDB
from core.authentication import authenticate
from core.exceptions import AuthenticationRequiredError, MissingDataError, InvalidCredentialsError

# ------------------------
# FIXTURE
# ------------------------
@pytest.fixture
def sample_user(db_session):
    user = UserDB(username="alice", password_hash="correct_password_hash", role="ADMIN", is_active=True)
    db_session.add(user)
    db_session.commit()
    return user

# ------------------------
# TESTS CASES
# ------------------------
def test_authenticate_success(db_session, sample_user):
    with patch("core.authentication.UserRepository") as mock_repo_cls, \
         patch("core.authentication.verify_password") as mock_verify, \
         patch("core.authentication.check_lock") as mock_lock, \
         patch("core.authentication.check_rate_limit") as mock_rate, \
         patch("core.authentication.apply_backoff"), \
         patch("core.authentication.reset_attempts") as mock_reset:

        mock_repo = Mock()
        mock_repo.get_by_username.return_value = sample_user
        mock_repo_cls.return_value = mock_repo
        mock_verify.return_value = True

        mock_lock.return_value = None
        mock_rate.return_value = None

        user = authenticate(username="alice", password="secret", db_session=db_session, ip="127.0.0.1")
        assert user.username == "alice"
        mock_reset.assert_called_once()

def test_authenticate_invalid_password(db_session, sample_user):
    with patch("core.authentication.UserRepository") as mock_repo_cls, \
         patch("core.authentication.verify_password") as mock_verify, \
         patch("core.authentication.apply_backoff") as mock_backoff, \
         patch("core.authentication.check_lock") as mock_lock, \
         patch("core.authentication.check_rate_limit") as mock_rate:

        mock_repo = Mock()
        mock_repo.get_by_username.return_value = sample_user
        mock_repo_cls.return_value = mock_repo
        mock_verify.return_value = False

        mock_lock.return_value = None
        mock_rate.return_value = None

        with pytest.raises(InvalidCredentialsError):
            authenticate(username="alice", password="wrong", db_session=db_session, ip="127.0.0.1")

        mock_backoff.assert_called_once()

def test_authenticate_user_not_found(db_session):
    with patch("core.authentication.UserRepository") as mock_repo_cls, \
         patch("core.authentication.verify_password") as mock_verify, \
         patch("core.authentication.apply_backoff") as mock_backoff, \
         patch("core.authentication.check_lock") as mock_lock, \
         patch("core.authentication.check_rate_limit") as mock_rate:

        mock_repo = Mock()
        mock_repo.get_by_username.return_value = None
        mock_repo_cls.return_value = mock_repo
        mock_verify.return_value = False

        mock_lock.return_value = None
        mock_rate.return_value = None

        with pytest.raises(InvalidCredentialsError):
            authenticate(username="nonexistent", password="secret", db_session=db_session, ip="127.0.0.1")

        mock_backoff.assert_called_once()

def test_authenticate_inactive_user(db_session, sample_user):
    sample_user.is_active = False
    db_session.commit()

    with patch("core.authentication.UserRepository") as mock_repo_cls, \
         patch("core.authentication.verify_password") as mock_verify, \
         patch("core.authentication.apply_backoff") as mock_backoff, \
         patch("core.authentication.check_lock") as mock_lock, \
         patch("core.authentication.check_rate_limit") as mock_rate:

        mock_repo = Mock()
        mock_repo.get_by_username.return_value = sample_user
        mock_repo_cls.return_value = mock_repo
        mock_verify.return_value = True

        mock_lock.return_value = None
        mock_rate.return_value = None

        with pytest.raises(InvalidCredentialsError):
            authenticate(username="alice", password="secret", db_session=db_session, ip="127.0.0.1")

        mock_backoff.assert_called_once()

def test_authenticate_missing_ip(db_session, sample_user):
    with pytest.raises(MissingDataError):
        authenticate(username="alice", password="secret", db_session=db_session)

def test_authenticate_missing_db_session():
    with pytest.raises(MissingDataError):
        authenticate(username="alice", password="secret", db_session=None, ip="127.0.0.1")