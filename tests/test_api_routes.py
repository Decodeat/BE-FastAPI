"""
Tests for API routes.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from decodeat.main import app
from decodeat.api.models import DecodeStatus

client = TestClient(app)


class TestAnalyzeEndpoint:
    """Test cases for the /analyze endpoint."""
    
    def test_analyze_endpoint_exists(self):
        """Test that the analyze endpoint exists and accepts POST requests."""
        # Test with invalid request to check endpoint exists
        response = client.post("/api/v1/analyze", json={})
        # Should return 422 for validation error, not 404
        assert response.status_code == 422
    
    def test_analyze_request_validation(self):
        """Test request validation for the analyze endpoint."""
        # Test empty image_urls
        response = client.post("/api/v1/analyze", json={"image_urls": []})
        assert response.status_code == 422
        
        # Test too many image_urls
        response = client.post("/api/v1/analyze", json={
            "image_urls": ["url1", "url2", "url3"]
        })
        assert response.status_code == 422
        
        # Test invalid URL format
        response = client.post("/api/v1/analyze", json={
            "image_urls": ["not-a-url"]
        })
        assert response.status_code == 422
    
    @patch('decodeat.api.routes.ImageDownloadService')
    @patch('decodeat.api.routes.OCRService')
    @patch('decodeat.api.routes.ValidationService')
    @patch('decodeat.api.routes.AnalysisService')
    def test_analyze_single_image_success(self, mock_analysis, mock_validation, mock_ocr, mock_download):
        """Test successful single image analysis."""
        # This test verifies the endpoint structure but doesn't test the full flow
        # since that would require actual external API calls
        
        # Test with valid request structure
        response = client.post("/api/v1/analyze", json={
            "image_urls": ["https://example.com/image.jpg"]
        })
        
        # Should return 200 (endpoint exists and processes request)
        # The actual response will depend on external services
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "decodeStatus" in data
        assert "message" in data
        assert "product_name" in data
        assert "nutrition_info" in data
        assert "ingredients" in data
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nutrition-label-api"


if __name__ == "__main__":
    pytest.main([__file__])