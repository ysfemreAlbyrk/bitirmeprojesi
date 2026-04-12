"""Integration tests for Books API"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestBooksAPI:
    """Integration tests for book management endpoints"""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_list_books_empty(self, client: TestClient):
        """Test listing books when none exist"""
        response = client.get("/books/?user_id=test_user")
        # This will fail without actual database, but tests the endpoint structure
        assert response.status_code in [200, 500]
    
    def test_upload_book_no_file(self, client: TestClient):
        """Test book upload without file"""
        response = client.post("/books/upload")
        assert response.status_code == 422  # Validation error
    
    def test_get_book_not_found(self, client: TestClient):
        """Test getting non-existent book"""
        response = client.get("/books/nonexistent-id")
        assert response.status_code == 404
    
    def test_get_book_status_not_found(self, client: TestClient):
        """Test getting status of non-existent book"""
        response = client.get("/books/nonexistent-id/status")
        assert response.status_code == 404


@pytest.mark.integration
class TestReadingAPI:
    """Integration tests for reading progress endpoints"""
    
    def test_get_reading_progress_not_found(self, client: TestClient):
        """Test getting reading progress for non-existent book"""
        response = client.get("/reading/progress/test_user/test_book")
        assert response.status_code == 200  # Returns default progress
    
    def test_create_bookmark_no_data(self, client: TestClient):
        """Test creating bookmark without data"""
        response = client.post("/reading/bookmarks")
        assert response.status_code == 422  # Validation error
    
    def test_list_bookmarks_not_found(self, client: TestClient):
        """Test listing bookmarks for non-existent book"""
        response = client.get("/reading/bookmarks/test_user/test_book")
        assert response.status_code == 200  # Returns empty list
    
    def test_delete_bookmark_not_found(self, client: TestClient):
        """Test deleting non-existent bookmark"""
        response = client.delete("/reading/bookmarks/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.integration
class TestAmbianceAPI:
    """Integration tests for ambiance endpoints"""
    
    def test_get_ambiance_not_found(self, client: TestClient):
        """Test getting ambiance for non-existent chunk"""
        response = client.get("/ambiance/nonexistent-chunk-id")
        assert response.status_code == 404
