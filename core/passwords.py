import re
import bcrypt
from core.exceptions import InvalidPasswordError

# 🔐 Password rules
MIN_LENGTH = 15
MIN_UPPER = 1
MIN_LOWER = 1
MIN_DIGITS = 1
MIN_SYMBOLS = 1
SYMBOLS = r"!@#$%^&*()\-_=+\[\]{};:'\",.<>/?"

def validate_password(password: str) -> None:
    """
    Validate that a password meets security requirements:
    - Minimum length 15
    - At least 1 uppercase letters
    - At least 1 lowercase letters
    - At least 1 digits
    - At least 1 symbols
    """
    if len(password) < MIN_LENGTH:
        raise InvalidPasswordError(f"Password must be at least {MIN_LENGTH} characters")

    if len(re.findall(r'[A-Z]', password)) < MIN_UPPER:
        raise InvalidPasswordError(f"Password must contain at least {MIN_UPPER} uppercase letters")

    if len(re.findall(r'[a-z]', password)) < MIN_LOWER:
        raise InvalidPasswordError(f"Password must contain at least {MIN_LOWER} lowercase letters")

    if len(re.findall(r'[0-9]', password)) < MIN_DIGITS:
        raise InvalidPasswordError(f"Password must contain at least {MIN_DIGITS} digits")

    if len(re.findall(f"[{re.escape(SYMBOLS)}]", password)) < MIN_SYMBOLS:
        raise InvalidPasswordError(f"Password must contain at least {MIN_SYMBOLS} symbols")

def hash_password(password: str) -> str:
    """
    Generate a bcrypt hash for the password
    """
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against the stored bcrypt hash
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))