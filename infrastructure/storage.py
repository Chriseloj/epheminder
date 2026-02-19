import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator
from contextlib import contextmanager

STORAGE_DIR = "infrastructure/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

DATABASE_FILE = os.path.join(STORAGE_DIR, "database.db")
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

try:
    os.chmod(DATABASE_FILE, 0o600)
except FileNotFoundError:
   
    pass

Base.metadata.create_all(bind=engine)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()