import pytest
from app import app as flask_app
import json


@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200


def test_about(client):
    response = client.get("/about")
    assert response.status_code == 200


def test_webhook_no_pr(client):
    """Test webhook endpoint with non-PR payload"""
    response = client.post(
        "/webhook", 
        data=json.dumps({"action": "opened"}),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "Not a PR event"


def test_webhook_with_pr(client):
    """Test webhook endpoint with PR payload"""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 1,
            "title": "Test PR",
            "user": {"login": "test-user"},
            "base": {"ref": "main"},
            "head": {"ref": "feature"},
            "html_url": "https://github.com/test/test/pull/1",
            "diff_url": "https://github.com/test/test/pull/1.diff",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z"
        },
        "repository": {
            "full_name": "test/test"
        }
    }
    
    response = client.post(
        "/webhook", 
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "Processing PR"


def test_relationships_get(client):
    """Test getting relationships"""
    response = client.get("/api/relationships")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "repositories" in data
    assert "relationships" in data


def test_relationships_post(client):
    """Test adding a relationship"""
    data = {
        "source": "test/repo1",
        "target": "test/repo2",
        "relationship_type": "depends-on"
    }
    
    response = client.post(
        "/api/relationships",
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert response_data["status"] == "Relationship added"
