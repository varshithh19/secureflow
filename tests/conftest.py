"""SecureFlow Pytest Test Configuration & Shared Fixtures."""
import sys
from pathlib import Path

# Add src and project root to Python search path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secureflow.core.config import Settings, get_settings
from secureflow.core.security import create_access_token, hash_password
from secureflow.main import app
from secureflow.models import User
from secureflow.models.base import Base
from secureflow.repositories.database import get_db
from scripts.seed import seed_database

# In-memory SQLite Database for isolated, fast test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh in-memory database schema for each test function."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session):
    """FastAPI TestClient with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Helper factory generating Authorization headers for any given role and user ID."""
    def _make_headers(user_id: str, role: str) -> dict:
        token = create_access_token(subject=user_id, role=role)
        return {"Authorization": f"Bearer {token}"}
    return _make_headers
