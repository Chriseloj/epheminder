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
    if DATABASE_FILE.exists() and platform.system() != "Windows":
        try:
            os.chmod(DATABASE_FILE, 0o600)
        except PermissionError:
            pass


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