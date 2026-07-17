import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Setup SQLite database for isolated dashboard testing
test_engine = create_engine("sqlite:///test_dashboard.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 2. Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 3. Monkey-patch SessionLocal globally before importing main application
import app.database
app.database.SessionLocal = TestSessionLocal

import app.repositories.uow
app.repositories.uow.SessionLocal = TestSessionLocal

from app.main import app
from app.database import Base
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty

# 4. Initialize TestClient and apply authentication headers globally
from fastapi.testclient import TestClient
client = TestClient(app)
client.headers.update({"Authorization": "Bearer default-user-token"})


@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """Create tables and seed database before running module tests."""
    Base.metadata.create_all(bind=test_engine)
    # Seed the test SQLite database
    seed_if_empty(uow_factory=UnitOfWork)
    yield
    Base.metadata.drop_all(bind=test_engine)
    # Cleanup test db file
    if os.path.exists("test_dashboard.db"):
        try:
            os.remove("test_dashboard.db")
        except Exception:
            pass


def test_dashboard_metrics():
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    
    metrics = res.json()
    
    expected_keys = [
        "saved",
        "applied",
        "assessments",
        "interviews",
        "offers",
        "rejected",
        "withdrawn",
        "total",
        "success_rate",
        "average_match_score",
        "average_confidence",
        "avg_days_in_pipeline"
    ]
    
    for key in expected_keys:
        assert key in metrics
        assert isinstance(metrics[key], (int, float))
