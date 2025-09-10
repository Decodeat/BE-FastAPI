"""
Unit tests for ValidationService.
Tests the AI validation functionality for single images and image pairs.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decodeat.services.validation_service import ValidationService


class TestValidationService:
    """Test cases for ValidationService."""
    
    @pytest.fixture
    def validation_service(self):
        """Create a ValidationService instance for testing."""
        with patch('decodeat.services.validation_service.settings') as mock_settings:
            mock_settings.gemini_api_key = "test-api-key"
            with patch('decodeat.services.validation_service.genai.configure'):
                with patch('decodeat.services.validation_service.genai.GenerativeModel') as mock_model:
                    mock_model.return_value = MagicMock()
                    return ValidationService()
    
    @pytest.mark.asyncio
    async def test_validate_single_image_with_nutrition_info(self, validation_service):
        """Test validation of single image containing nutrition information."""
        # Mock Gemini AI response
        mock_response = MagicMock()
        mock_response.text = "true"
        validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Test text with nutrition information
        nutrition_text = """
        영양성분 (1회 제공량 250ml당)
        열량 150kcal
        나트륨 55mg (3%)
        탄수화물 20g (6%)
        당류 18g (18%)
        지방 8g (15%)
        트랜스지방 0g
        포화지방 5g (33%)
        콜레스테롤 30mg (10%)
        단백질 3g (5%)
        """
        
        result = await validation_service.validate_single_image(nutrition_text)
        assert result is True
        validation_service.model.generate_content_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_single_image_with_ingredients(self, validation_service):
        """Test validation of single image containing ingredient information."""
        # Mock Gemini AI response
        mock_response = MagicMock()
        mock_response.text = "true"
        validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Test text with ingredient information
        ingredient_text = """
        원재료명: 정제수, 백설탕, 혼합분유(탈지분유, 유청분말), 
        식물성유지(팜유, 코코넛유), 코코아분말, 바닐라향
        """
        
        result = await validation_service.validate_single_image(ingredient_text)
        assert result is True
        validation_service.model.generate_content_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_single_image_irrelevant_content(self, validation_service):
        """Test validation of single image with irrelevant content."""
        # Mock Gemini AI response
        mock_response = MagicMock()
        mock_response.text = "false"
        validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Test text with irrelevant content
        irrelevant_text = """
        안녕하세요. 오늘 날씨가 좋네요.
        이것은 영양성분과 관련없는 텍스트입니다.
        """
        
        result = await validation_service.validate_single_image(irrelevant_text)
        assert result is False
        validation_service.model.generate_content_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_single_image_empty_text(self, validation_service):
        """Test validation with empty text."""
        result = await validation_service.validate_single_image("")
        assert result is False
        
        result = await validation_service.validate_single_image("   ")
        assert result is False
        
        result = await validation_service.validate_single_image(None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_single_image_api_error(self, validation_service):
        """Test handling of API errors during single image validation."""
        # Mock API error
        validation_service.model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(Exception, match="Validation failed: API Error"):
            await validation_service.validate_single_image("test text")
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_same_product(self, validation_service):
        """Test validation of image pair from the same product."""
        # Mock Gemini AI response
        mock_response = MagicMock()
        mock_response.text = "true"
        validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Test texts from the same product
        text1 = """
        코카콜라 제로
        영양성분 (1회 제공량 250ml당)
        열량 0kcal
        나트륨 15mg
        """
        
        text2 = """
        코카콜라 제로
        원재료명: 정제수, 이산화탄소, 카라멜색소, 
        인산, 아스파탐, 아세설팜칼륨
        """
        
        result = await validation_service.validate_image_pair(text1, text2)
        assert result is True
        validation_service.model.generate_content_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_different_products(self, validation_service):
        """Test validation of image pair from different products."""
        # Mock Gemini AI response
        mock_response = MagicMock()
        mock_response.text = "false"
        validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Test texts from different products
        text1 = """
        코카콜라 제로
        영양성분 (1회 제공량 250ml당)
        열량 0kcal
        """
        
        text2 = """
        펩시콜라
        원재료명: 정제수, 이산화탄소, 설탕
        """
        
        result = await validation_service.validate_image_pair(text1, text2)
        assert result is False
        validation_service.model.generate_content_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_empty_texts(self, validation_service):
        """Test validation with empty texts."""
        result = await validation_service.validate_image_pair("", "test")
        assert result is False
        
        result = await validation_service.validate_image_pair("test", "")
        assert result is False
        
        result = await validation_service.validate_image_pair("", "")
        assert result is False
        
        result = await validation_service.validate_image_pair(None, "test")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_api_error(self, validation_service):
        """Test handling of API errors during image pair validation."""
        # Mock API error
        validation_service.model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(Exception, match="Image pair validation failed: API Error"):
            await validation_service.validate_image_pair("text1", "text2")
    
    def test_validation_service_init_without_api_key(self):
        """Test ValidationService initialization without API key."""
        with patch('decodeat.services.validation_service.settings') as mock_settings:
            mock_settings.gemini_api_key = None
            
            with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
                ValidationService()
    
    @pytest.mark.asyncio
    async def test_validate_single_image_case_insensitive_response(self, validation_service):
        """Test that validation handles case-insensitive responses from AI."""
        # Test various case responses
        test_cases = [
            ("TRUE", True),
            ("True", True),
            ("true", True),
            ("FALSE", False),
            ("False", False),
            ("false", False),
        ]
        
        for ai_response, expected_result in test_cases:
            mock_response = MagicMock()
            mock_response.text = ai_response
            validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
            
            result = await validation_service.validate_single_image("test text")
            assert result is expected_result
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_case_insensitive_response(self, validation_service):
        """Test that image pair validation handles case-insensitive responses from AI."""
        # Test various case responses
        test_cases = [
            ("TRUE", True),
            ("True", True),
            ("true", True),
            ("FALSE", False),
            ("False", False),
            ("false", False),
        ]
        
        for ai_response, expected_result in test_cases:
            mock_response = MagicMock()
            mock_response.text = ai_response
            validation_service.model.generate_content_async = AsyncMock(return_value=mock_response)
            
            result = await validation_service.validate_image_pair("text1", "text2")
            assert result is expected_result