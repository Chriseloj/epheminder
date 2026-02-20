from core.models import RefreshTokenDB
from core.security import hash_token
from core.middleware import revoke_access_token

def logout(refresh_token: str, access_token: str, db_session):
    # Only if have refresh_token
    if refresh_token:
        token_hash = hash_token(refresh_token)
        stored_token = db_session.query(RefreshTokenDB).filter_by(
            token_hash=token_hash,
            revoked=False
        ).first()
        if stored_token:
            stored_token.revoked = True
            db_session.commit()

    # Only if have access_token
    if access_token:
        revoke_access_token(access_token)

    return True