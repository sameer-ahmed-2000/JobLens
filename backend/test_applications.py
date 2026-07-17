import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Setup SQLite database for isolated applications testing
test_engine = create_engine("sqlite:///test_apps.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 2. Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 3. Monkey-patch SessionLocal globally before importing main application
import app.database
app.database.SessionLocal = TestSessionLocal

import app.repositories.uow
app.repositories.uow.SessionLocal = TestSessionLocal

from app.main import app
from app.database import Base, get_db
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.models.orm import InterviewNoteORM

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
    if os.path.exists("test_apps.db"):
        try:
            os.remove("test_apps.db")
        except Exception:
            pass


def test_save_application():
    # Attempt to save a job (we assume job exists from seeder)
    res = client.get("/api/postings")
    assert res.status_code == 200
    postings = res.json()
    assert len(postings) > 0
    job_id = postings[0]["posting"]["id"]

    # Delete if it already exists from a previous test run
    apps_res = client.get("/api/applications")
    apps = apps_res.json()
    for a in apps:
        if a["job_id"] == job_id:
            client.delete(f"/api/applications/{a['id']}")

    # Save
    res = client.post("/api/applications", json={"job_id": job_id})
    assert res.status_code == 201
    app_data = res.json()
    assert app_data["job_id"] == job_id
    assert app_data["status"] == "Saved"

    # Save again should fail (409)
    res = client.post("/api/applications", json={"job_id": job_id})
    assert res.status_code == 409

    return app_data["id"]

def test_update_status():
    app_id = test_save_application()
    
    # Update to Applied
    res = client.patch(f"/api/applications/{app_id}", json={"status": "Applied"})
    assert res.status_code == 200
    assert res.json()["status"] == "Applied"

    # Update to Invalid status
    res = client.patch(f"/api/applications/{app_id}", json={"status": "NotAStatus"})
    assert res.status_code == 400

    return app_id

def test_notes_crud():
    app_id = test_update_status()

    # Add Note
    res = client.post(f"/api/applications/{app_id}/notes", json={"content": "Great recruiter."})
    assert res.status_code == 201
    note = res.json()
    assert note["content"] == "Great recruiter."
    note_id = note["id"]

    # Get Notes
    res = client.get(f"/api/applications/{app_id}/notes")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Update Note
    res = client.patch(f"/api/notes/{note_id}", json={"content": "Very great recruiter."})
    assert res.status_code == 200
    assert res.json()["content"] == "Very great recruiter."

    # Delete Note
    res = client.delete(f"/api/notes/{note_id}")
    assert res.status_code == 204

    # Verify deleted
    res = client.get(f"/api/applications/{app_id}/notes")
    assert not any(n["id"] == note_id for n in res.json())

def test_delete_application():
    app_id = test_update_status()
    
    res = client.delete(f"/api/applications/{app_id}")
    assert res.status_code == 204

    res = client.get(f"/api/applications/{app_id}")
    assert res.status_code == 404
