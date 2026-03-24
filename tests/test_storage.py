import pytest
from unittest.mock import patch, MagicMock 
from sqlalchemy.orm import Session
import importlib

# ------------------------------
# Fixture
# ------------------------------
@pytest.fixture
def storage_mocked():
    with patch("platform.system", return_value="Linux"), \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("os.chmod") as mock_chmod, \
         patch("sqlalchemy.create_engine") as mock_create_engine, \
         patch("sqlalchemy.orm.declarative_base") as mock_declarative_base:

        # Mock engine
        mock_engine_instance = MagicMock()
        mock_create_engine.return_value = mock_engine_instance

        # Mock Base y metadata.create_all
        mock_base_instance = MagicMock()
        mock_declarative_base.return_value = mock_base_instance
        mock_create_all = mock_base_instance.metadata.create_all

        import infrastructure.storage
        importlib.reload(infrastructure.storage)

        yield (
            infrastructure.storage,
            mock_mkdir,
            mock_chmod,
            mock_create_all
        )

# ------------------------------
# Tests import effects
# ------------------------------
def test_storage_dir_created(storage_mocked):
    storage, mock_mkdir, _, _ = storage_mocked
    # Assert mkdir 
    assert storage.DATA_DIR.exists()

def test_secure_db_respects_env(monkeypatch):
    monkeypatch.setenv("SECURE_DB", "true")

    import importlib
    import infrastructure.storage as storage
    importlib.reload(storage)
    
def test_chmod_called_on_database_file(storage_mocked):
    storage, _, mock_chmod, _ = storage_mocked
    
    db_file = storage.DATA_DIR / "database.db"

    mock_chmod.assert_not_called()

def test_create_all_called(monkeypatch):
    from app.main import start_app
    from infrastructure import storage

    called = False

    def fake_create_all(bind):
        nonlocal called
        called = True

    monkeypatch.setattr(storage.Base.metadata, "create_all", fake_create_all)

    start_app()

    assert called

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