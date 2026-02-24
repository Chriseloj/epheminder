import pytest
from unittest.mock import MagicMock, patch
from core.logout import logout
from core.models import RefreshTokenDB

# ------------------------------
# Fixtures
# ------------------------------
@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_refresh_token():
    return 'refresh-token'

@pytest.fixture
def mock_access_token():
    return 'access-token'

# ------------------------------
# Test 1: refresh token is None
# ------------------------------
def test_logout_with_no_refresh_token(mock_db_session):
    result = logout(None, 'access-token', mock_db_session)
    assert result is True
    mock_db_session.query.assert_not_called()

# ------------------------------
# Test 2: access token is None
# ------------------------------
@patch('core.logout.revoke_access_token')
def test_logout_with_no_access_token(mock_revoke, mock_db_session, mock_refresh_token):
    # Simulate DB return one token
    token_obj = MagicMock(spec=RefreshTokenDB)
    mock_db_session.query().filter_by().first.return_value = token_obj

    result = logout(mock_refresh_token, None, mock_db_session)

    assert result is True
    # Must revoke refresh token
    assert token_obj.revoked is True
    mock_db_session.commit.assert_called_once()
    # revoke_access_token mustn't called
    mock_revoke.assert_not_called()

# ------------------------------
# Test 3: refresh token not exist on DB
# ------------------------------
@patch('core.logout.revoke_access_token')
def test_logout_refresh_token_not_found(mock_revoke, mock_db_session, mock_refresh_token, mock_access_token):
    # DB return None
    mock_db_session.query().filter_by().first.return_value = None

    result = logout(mock_refresh_token, mock_access_token, mock_db_session)

    assert result is True
    # commit mustn't called
    mock_db_session.commit.assert_not_called()
    # revoke_access_token must called with both access_token and db_session
    mock_revoke.assert_called_once_with(mock_access_token, db_session=mock_db_session)


# ------------------------------
# Test 4: both tokens valids
# ------------------------------
@patch('core.logout.revoke_access_token')
def test_logout_success(mock_revoke, mock_db_session, mock_refresh_token, mock_access_token):
    token_obj = MagicMock(spec=RefreshTokenDB)
    mock_db_session.query().filter_by().first.return_value = token_obj

    result = logout(mock_refresh_token, mock_access_token, mock_db_session)

    assert result is True
    assert token_obj.revoked is True
    mock_db_session.commit.assert_called_once()
    # revoke_access_token must called with both access_token and db_session
    mock_revoke.assert_called_once_with(mock_access_token, db_session=mock_db_session)

# ------------------------------
# Test 5: hash_token 
# ------------------------------
@patch('core.logout.hash_token', return_value='hashed-token')
@patch('core.logout.revoke_access_token')
def test_logout_calls_hash_token(mock_revoke, mock_hash, mock_db_session, mock_refresh_token, mock_access_token):
    token_obj = MagicMock(spec=RefreshTokenDB)
    mock_db_session.query().filter_by().first.return_value = token_obj

    logout(mock_refresh_token, mock_access_token, mock_db_session)
    mock_hash.assert_called_once_with(mock_refresh_token)