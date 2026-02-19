import pytest
from unittest.mock import patch, MagicMock
from core.services import UserService
from core.security import create_access_token
from core.middleware import get_current_user, revoke_access_token
from core.exceptions import AuthenticationRequiredError


def test_get_current_user_valid_and_revoked(db_session):
    # Crear usuario
    user = UserService.create_user("testuser", "Password1234@#!", db_session=db_session)
    access_token = create_access_token(user)

    mock_redis = MagicMock()

    with patch("core.middleware.get_redis", return_value=mock_redis):

        # 🔹 Token NO revocado
        mock_redis.get.return_value = None

        current_user = get_current_user(access_token, db_session=db_session)
        assert current_user.id == user.id

        # 🔹 Revocar token
        revoke_access_token(access_token)

        # Verificamos que Redis.set fue llamado
        assert mock_redis.set.called

        # 🔹 Ahora simulamos token revocado
        mock_redis.get.return_value = True

        with pytest.raises(AuthenticationRequiredError):
            get_current_user(access_token, db_session=db_session)