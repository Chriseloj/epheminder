from datetime import datetime, timezone
from core.models import RefreshTokenDB
import logging

logger = logging.getLogger(__name__)

class TokenService:

    @staticmethod
    def cleanup_expired_tokens(session):
        """
        Delete all expired refresh tokens from the database.

        Args:
            session (Session): SQLAlchemy session, required.

        Returns:
            int: Number of refresh tokens deleted.

        Raises:
            ValueError: If session is not provided.
        """
        if session is None:
            raise ValueError("Session is required")

        now = datetime.now(timezone.utc)
        deleted = session.query(RefreshTokenDB)\
                         .filter(RefreshTokenDB.expires_at < now)\
                         .delete()
        session.commit()

        logger.info(f"Deleted {deleted} expired refresh tokens")
        return deleted