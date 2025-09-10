"""Tests for OCR service."""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock

from decodeat.services.ocr_service import OCRService


class TestOCRService:
    """Test cases for OCR service."""
    
    @pytest.fixture
    def ocr_service(self):
        """Create OCR service instance for testing."""
        return OCRService()
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Load sample image bytes for testing."""
        test_image_path = os.path.join("assets", "test_image.jpg")
        if os.path.exists(test_image_path):
            with open(test_image_path, "rb") as f:
                return f.read()
        else:
            # Return a minimal valid JPEG header for testing
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00'
    
    def test_ocr_service_initialization(self, ocr_service):
        """Test OCR service initialization."""
        assert ocr_service is not None
        assert ocr_service._client is None  # Client should be lazy-loaded
        assert ocr_service._executor is not None
    
    @pytest.mark.asyncio
    async def test_extract_text_empty_bytes(self, ocr_service):
        """Test extract_text with empty bytes raises ValueError."""
        with pytest.raises(ValueError, match="Image bytes cannot be empty"):
            await ocr_service.extract_text(b"")
    
    @pytest.mark.asyncio
    async def test_extract_text_none_bytes(self, ocr_service):
        """Test extract_text with None bytes raises ValueError."""
        with pytest.raises(ValueError, match="Image bytes cannot be empty"):
            await ocr_service.extract_text(None)
    
    @pytest.mark.asyncio
    @patch('decodeat.services.ocr_service.ImageAnnotatorClient')
    async def test_extract_text_success(self, mock_client_class, ocr_service, sample_image_bytes):
        """Test successful text extraction."""
        # Mock the Vision API response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        mock_response.text_annotations = [Mock(description="Sample extracted text")]
        mock_client.document_text_detection.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = await ocr_service.extract_text(sample_image_bytes)
        
        assert result == "Sample extracted text"
        mock_client.document_text_detection.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('decodeat.services.ocr_service.ImageAnnotatorClient')
    async def test_extract_text_no_text_detected(self, mock_client_class, ocr_service, sample_image_bytes):
        """Test text extraction when no text is detected."""
        # Mock the Vision API response with no text
        mock_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        mock_response.text_annotations = []
        mock_client.document_text_detection.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = await ocr_service.extract_text(sample_image_bytes)
        
        assert result == ""
        mock_client.document_text_detection.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('decodeat.services.ocr_service.ImageAnnotatorClient')
    async def test_extract_text_api_error(self, mock_client_class, ocr_service, sample_image_bytes):
        """Test text extraction when Vision API returns an error."""
        # Mock the Vision API response with error
        mock_client = Mock()
        mock_response = Mock()
        mock_response.error.message = "API quota exceeded"
        mock_client.document_text_detection.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with pytest.raises(RuntimeError, match="Google Cloud Vision API error"):
            await ocr_service.extract_text(sample_image_bytes)
    
    @pytest.mark.asyncio
    @patch('decodeat.services.ocr_service.ImageAnnotatorClient')
    async def test_extract_text_from_multiple_images(self, mock_client_class, ocr_service, sample_image_bytes):
        """Test extracting text from multiple images."""
        # Mock the Vision API response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        mock_response.text_annotations = [Mock(description="Sample text")]
        mock_client.document_text_detection.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        images = [sample_image_bytes, sample_image_bytes]
        results = await ocr_service.extract_text_from_multiple_images(images)
        
        assert len(results) == 2
        assert all(result == "Sample text" for result in results)
        assert mock_client.document_text_detection.call_count == 2
    
    @pytest.mark.asyncio
    async def test_extract_text_from_multiple_images_empty_list(self, ocr_service):
        """Test extract_text_from_multiple_images with empty list raises ValueError."""
        with pytest.raises(ValueError, match="Images bytes list cannot be empty"):
            await ocr_service.extract_text_from_multiple_images([])
    
    @pytest.mark.asyncio
    async def test_context_manager(self, sample_image_bytes):
        """Test OCR service as async context manager."""
        with patch('decodeat.services.ocr_service.ImageAnnotatorClient') as mock_client_class:
            # Mock the Vision API response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.error.message = ""
            mock_response.text_annotations = [Mock(description="Test text")]
            mock_client.document_text_detection.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            async with OCRService() as ocr_service:
                result = await ocr_service.extract_text(sample_image_bytes)
                assert result == "Test text"
    
    @pytest.mark.asyncio
    async def test_close_service(self, ocr_service):
        """Test closing the OCR service."""
        # This should not raise any exceptions
        await ocr_service.close()
        
        # Executor should be shutdown
        assert ocr_service._executor._shutdown


if __name__ == "__main__":
    # Run a simple integration test if executed directly
    async def integration_test():
        """Simple integration test with real Google Cloud Vision API."""
        try:
            # Load test image
            test_image_path = os.path.join("assets", "test_image.jpg")
            if not os.path.exists(test_image_path):
                print("Test image not found, skipping integration test")
                return
            
            with open(test_image_path, "rb") as f:
                image_bytes = f.read()
            
            # Test OCR service
            async with OCRService() as ocr_service:
                text = await ocr_service.extract_text(image_bytes)
                print(f"Extracted text: {text[:200]}...")  # Print first 200 chars
                
        except Exception as e:
            print(f"Integration test failed: {e}")
    
    # Run integration test
    asyncio.run(integration_test())