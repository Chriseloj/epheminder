from core.services import UserService
from datetime import datetime, timedelta, timezone
from core.refresh import refresh
from core.models import RefreshTokenDB
from core.security import create_refresh_token, hash_token
import uuid


def test_refresh_token_rotation(db_session):
    user = UserService.create_user("testuser", "Password1234@#!", db_session=db_session)
    refresh_token = create_refresh_token(user)

    # Persistir refresh token como si hubieras hecho login
    refresh_db = RefreshTokenDB(
        id=uuid.uuid4(),         # UUID para el token
        user_id=user.id,         # ya es UUID
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False
    )
    db_session.add(refresh_db)
    db_session.commit()

    # Rotación
    tokens = refresh(refresh_token, db_session=db_session)

    # Deben ser nuevos tokens
    assert tokens["access_token"] is not None
    assert tokens["refresh_token"] is not None
    assert tokens["refresh_token"] != refresh_token

    # Antiguo refresh token revocado
    old_token = db_session.query(RefreshTokenDB).filter_by(token_hash=hash_token(refresh_token)).first()
    assert old_token.revoked is True