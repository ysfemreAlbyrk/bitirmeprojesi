"""Integration test configuration"""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session")
def client():
    """Create test client for FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {"Authorization": "Bearer test_token"}
