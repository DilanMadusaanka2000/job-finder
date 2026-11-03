from fastapi.testclient import TestClient

from app import main
from app.database import get_db


def test_dashboard_renders_template(monkeypatch):
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda **kwargs: None)
    monkeypatch.setattr(main, "search_jobs", lambda *args, **kwargs: ([], 0))
    monkeypatch.setitem(main.app.dependency_overrides, get_db, lambda: None)

    with TestClient(main.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "No saved jobs match your filters." in response.text
