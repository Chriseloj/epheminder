import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
import importlib

# ------------------------------
# Fixture
# ------------------------------
@pytest.fixture(scope="module")
def storage_mocked():
    # Create mock of Base with metadata.create_all
    mock_create_all = MagicMock()
    mock_base = MagicMock()
    mock_base.metadata.create_all = mock_create_all

    # declarative_base, os.makedirs and os.chmod before import storage
    with patch("sqlalchemy.orm.declarative_base", return_value=mock_base), \
         patch("os.makedirs") as mock_makedirs, \
         patch("os.chmod") as mock_chmod:

        import infrastructure.storage as storage
        importlib.reload(storage)  # patch apply on import

        yield storage, mock_makedirs, mock_chmod, mock_create_all

# ------------------------------
# Tests import effects
# ------------------------------
def test_storage_dir_created(storage_mocked):
    storage, mock_makedirs, _, _ = storage_mocked
    mock_makedirs.assert_called_with(storage.STORAGE_DIR, exist_ok=True)

def test_chmod_called_on_database_file(storage_mocked):
    storage, _, mock_chmod, _ = storage_mocked
    mock_chmod.assert_called_with(storage.DATABASE_FILE, 0o600)

def test_base_metadata_create_all_called_on_import(storage_mocked):
    storage, _, _, mock_create_all = storage_mocked
    mock_create_all.assert_called_with(bind=storage.engine)

# ------------------------------
# SessionLocal
# ------------------------------
def test_session_local_returns_session():
    import infrastructure.storage as storage
    session = storage.SessionLocal()
    assert isinstance(session, Session)
    session.close()

# ------------------------------
# get_db_session context manager
# ------------------------------
def test_get_db_session_commits(monkeypatch):
    import infrastructure.storage as storage
    mock_session = MagicMock()
    monkeypatch.setattr(storage, "SessionLocal", lambda: mock_session)

    with storage.get_db_session() as session:
        assert session == mock_session
        session.add("dummy")

    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()

def test_get_db_session_rollbacks_on_exception(monkeypatch):
    import infrastructure.storage as storage
    mock_session = MagicMock()
    monkeypatch.setattr(storage, "SessionLocal", lambda: mock_session)

    with pytest.raises(ValueError):
        with storage.get_db_session() as session:
            raise ValueError("fail")

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()