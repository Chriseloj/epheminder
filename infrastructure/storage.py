import os
import platform
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator
from contextlib import contextmanager


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR # Compatibility with tests
DATABASE_FILE = BASE_DIR / "database.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

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
Base.metadata.create_all(bind=engine)


def _secure_database_file():
    """
    Restrict database file access to the current user.
    On POSIX systems uses chmod 0600.
    On Windows uses ACL to allow only the current user.
    """
    if not DATABASE_FILE.exists():
        return

    if platform.system() == "Windows":
        # Allow only the current user to read/write
        # Equivalent to running in CMD: icacls "database.db" /inheritance:r /grant:r "%USERNAME%:F"
        try:
            import subprocess
            username = os.getlogin()
            subprocess.run(
                ["icacls", str(DATABASE_FILE), "/inheritance:r", "/grant:r", f"{username}:F"],
                check=True
            )
        except Exception as e:
            print(f"⚠ Could not restrict database file on Windows: {e}")

    else:
        # POSIX systems: owner read/write only
        try:
            os.chmod(DATABASE_FILE, 0o600)
        except PermissionError:
            print("⚠ Could not restrict database file on POSIX")

_secure_database_file()


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