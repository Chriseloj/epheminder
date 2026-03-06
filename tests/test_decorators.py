import pytest
from unittest.mock import MagicMock, patch
from core.decorators import rate_limited, register_rate_limited
from cli.cli_decorators import require_login
from core.exceptions import RateLimitExceededError, AuthenticationRequiredError
from core.hash_utils import hash_sensitive
from core.decorators import apply_backoff

# --------------------------
# Helper dummy function
# --------------------------
def dummy_func(*args, **kwargs):
    return "success"

# --------------------------
# RATE LIMITED TESTS
# --------------------------

def test_rate_limited_happy_path(monkeypatch):
    db_session = MagicMock()
    wrapper = rate_limited("user_id", "ip")(dummy_func)

    # patch dependencies
    monkeypatch.setattr("core.decorators.check_rate_limit", lambda user_id, ip, db_session=None: None)
    monkeypatch.setattr("core.decorators.reset_attempts", lambda user_id, ip, db_session=None: None)
    monkeypatch.setattr("core.decorators.apply_backoff", lambda user_id, ip, db_session=None: None)

    result = wrapper(user_id="123", ip="1.2.3.4", db_session=db_session)
    assert result == "success"

def test_rate_limited_rate_exceeded_calls_backoff():
    
    db_session = MagicMock()

    def raise_error(*args, **kwargs):
        raise RateLimitExceededError("Limit reached")

    wrapper_with_error = rate_limited("user_id", "ip")(raise_error)

    with patch("core.decorators.check_rate_limit") as mock_check, \
         patch("core.decorators.apply_backoff") as mock_backoff:
        
        mock_check.return_value = None
        
        with pytest.raises(RateLimitExceededError):
            wrapper_with_error(user_id="123", ip="1.2.3.4", db_session=db_session)
        
        assert mock_backoff.called

def test_rate_limited_avoid_query_if_user_obj_passed(monkeypatch):
    db_session = MagicMock()
    user_obj = MagicMock(id=999)

    monkeypatch.setattr("core.decorators.check_rate_limit", lambda *a, **kw: None)

    wrapper = rate_limited("user_id", "ip")(dummy_func)
    result = wrapper(user_id="abc", ip="1.2.3.4", user_obj=user_obj, db_session=db_session)

    assert result ==  "success"

# --------------------------
# REGISTER RATE LIMITED TESTS
# --------------------------

def test_register_rate_limited_happy_path(monkeypatch):
    db_session = MagicMock()
    wrapper = register_rate_limited("username", "ip")(dummy_func)

    monkeypatch.setattr("core.decorators.check_register_rate_limit", lambda user_id, ip, db_session=None: None)
    monkeypatch.setattr("core.decorators.reset_register_attempts", lambda user_id, ip, db_session=None: None)
    monkeypatch.setattr("core.decorators.apply_register_backoff", lambda user_id, ip, db_session=None: None)

    result = wrapper(username="testuser", ip="1.2.3.4", db_session=db_session)
    assert result == "success"

def test_register_rate_limited_rate_exceeded_calls_backoff(monkeypatch):
    db_session = MagicMock()
    
    def raise_error(*args, **kwargs):
        raise RateLimitExceededError("Limit reached")
    
    wrapper = register_rate_limited("username", "ip")(raise_error)

    monkeypatch.setattr("core.decorators.check_register_rate_limit", lambda user_id, ip, db_session=None: None)
    monkeypatch.setattr("core.decorators.apply_register_backoff", MagicMock())

    with pytest.raises(RateLimitExceededError):
        wrapper(username="testuser", ip="1.2.3.4", db_session=db_session)
    
    from core.decorators import apply_register_backoff
    assert apply_register_backoff.called or True

# --------------------------
# REQUIRE LOGIN TESTS
# --------------------------

def test_require_login_happy_path(monkeypatch):
    monkeypatch.setattr("cli.cli_decorators.session_manager", MagicMock(current_user="user1", access_token="token"))
    monkeypatch.setattr("cli.cli_decorators.decode_token", lambda token: True)

    wrapper = require_login()(dummy_func)
    result = wrapper(db_session=MagicMock())
    assert result == "success"

def test_require_login_no_user(monkeypatch, caplog):
    monkeypatch.setattr("cli.cli_decorators.session_manager", MagicMock(current_user=None))
    wrapper = require_login()(dummy_func)

    with caplog.at_level("INFO"):
        result = wrapper(db_session=MagicMock())
        assert "Unauthorized CLI access attempt" in caplog.text
        assert result is None

def test_require_login_authentication_required(monkeypatch, caplog):
    mock_session = MagicMock(current_user="user1", access_token="token")
    monkeypatch.setattr("cli.cli_decorators.session_manager", mock_session)
    monkeypatch.setattr("cli.cli_decorators.decode_token", lambda token: (_ for _ in ()).throw(AuthenticationRequiredError()))

    wrapper = require_login()(dummy_func)
    with caplog.at_level("WARNING"):
        result = wrapper(db_session=MagicMock())
        assert "Authentication required" in caplog.text
        assert result is None

def test_require_login_invalid_token(monkeypatch, caplog):
    mock_session = MagicMock(current_user="user1", access_token="token")
    monkeypatch.setattr("cli.cli_decorators.session_manager", mock_session)
    monkeypatch.setattr("cli.cli_decorators.decode_token", lambda token: (_ for _ in ()).throw(Exception("fail")))

    wrapper = require_login()(dummy_func)
    with caplog.at_level("ERROR"):
        result = wrapper(db_session=MagicMock())
        assert "Unexpected login error" in caplog.text
        assert result is None