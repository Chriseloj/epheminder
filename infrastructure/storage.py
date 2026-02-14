import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

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