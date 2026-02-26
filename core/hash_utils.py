import os
from dotenv import load_dotenv
import uuid
import hashlib

load_dotenv() 
HASH_SALT = os.getenv("HASH_SALT")

if not HASH_SALT:
    raise RuntimeError("HASH_SALT not defined")

def hash_sensitive(data) -> str:
    """Hash a sensitive value (UUID, str, etc.) uses SHA256 + secure salt ."""
    if isinstance(data, uuid.UUID):
        data = str(data)
    elif not isinstance(data, str):
        data = str(data)

    salted = f"{HASH_SALT}{data}"  # salt
    return hashlib.sha256(salted.encode()).hexdigest()