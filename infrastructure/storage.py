import os
import platform
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator
from contextlib import contextmanager
from config import DATABASE_URL, DATA_DIR
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},  # Required for scheduler threads
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

def _secure_database_file():
    """
    Restrict database file access to the current user.
    On POSIX systems uses chmod 0600.
    On Windows uses ACL to allow only the current user.
    """
    db_file = DATA_DIR / "database.db"

    if not db_file.exists():
        return
    
    if platform.system() == "Windows":
        # Allow only the current user to read/write
        # Equivalent to running in CMD: icacls "database.db" /inheritance:r /grant:r "%USERNAME%:F"
        try:
            import subprocess
            username = os.getlogin()
            subprocess.run(
                ["icacls", str(db_file), "/inheritance:r", "/grant:r", f"{username}:F"],
                check=True
            )
        except Exception as e:
           logger.warning("Could not secure database file, check permissions.")

    else:
        # POSIX systems: owner read/write only
        try:

            if os.getenv("SECURE_DB", "false") == "true":
                os.chmod(db_file, 0o600)

        except PermissionError:
            logger.warning("Could not secure database file")

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()