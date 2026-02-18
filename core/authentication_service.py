import logging
import uuid
from core.services import rate_limited
from core.exceptions import MissingDataError, InvalidUserError
from core.services import UserService 
import hashlib
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_token
)
from core.models import RefreshTokenDB
from datetime import datetime, timedelta, timezone
from core.authentication import authenticate

logger = logging.getLogger(__name__)

def hash_sensitive(data) -> str:
   
    if isinstance(data, uuid.UUID):
        data = str(data)
    return hashlib.sha256(data.encode()).hexdigest()

class AuthenticationService:

    @staticmethod
    @rate_limited(user_param="username", ip_param="ip")
    def login(username: str, password: str, ip: str, db_session=None):
        if db_session is None:
            raise MissingDataError()

        username = username.strip().lower()
        user = authenticate(username, password, db_session=db_session, ip=ip)

        logger.info(f"Successful login | user_hash={hash_sensitive(user.id)} | ip={ip}")

        # 1️⃣ JWT access token
        access_token = create_access_token(user)

        # 2️⃣ Refresh token
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        token_value = uuid.uuid4().hex
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()

        refresh_token_db = RefreshTokenDB(
            id=uuid.uuid4(),  # UUID real
            user_id=user.id,  # UUID del user
            token_hash=token_hash,
            expires_at=expire,
            revoked=False,
            created_at=datetime.now(timezone.utc)
        )

        db_session.add(refresh_token_db)
        db_session.commit()

        # 3️⃣ Return both tokens
        return {
            "access_token": access_token,
            "refresh_token": token_value,  # devolvemos el token plano
            "token_type": "bearer"
        }