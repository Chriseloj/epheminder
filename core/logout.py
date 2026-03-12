from core.models import RefreshTokenDB
from core.security import hash_token
from core.middleware import revoke_access_token
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def logout(refresh_token: str, access_token: str, db_session: Session):
    """
     Revoke session tokens (refresh_token y access_token).
    """
    try:
        # refresh_token
        if refresh_token:
            token_hash = hash_token(refresh_token)
            stored_token = db_session.query(RefreshTokenDB).filter_by(
                token_hash=token_hash,
                revoked=False
            ).first()

            if stored_token:
                stored_token.revoked = True
                db_session.commit() 
                logger.info("Refresh token revoked successfully.")
            else:
                logger.warning("Refresh token not found or already revoked.")

        # access_token
        if access_token:
            revoke_access_token(access_token, db_session=db_session)
            logger.info("Access token revoked successfully.")
        
        return True

    except Exception as e:
        logger.error(
            "Error during logout: %s",
            str(e)
        )
        db_session.rollback()  # Error, return session
        return False