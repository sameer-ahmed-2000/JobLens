import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
