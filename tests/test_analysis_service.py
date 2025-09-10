"""
Unit tests for AnalysisService.
Tests nutrition information analysis functionality.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from decodeat.services.analysis_service import AnalysisService
from decodeat.api.models import DecodeStatus, NutritionInfo


class TestAnalysisService:
    """Test cases for AnalysisService."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create AnalysisService instance for testing."""
        with patch('decodeat.services.analysis_service.settings') as mock_settings:
            mock_settings.gemini_api_key = "test-api-key"
            with patch('decodeat.services.analysis_service.genai.configure'):
                with patch('decodeat.services.analysis_service.genai.GenerativeModel') as mock_model:
                    mock_model.return_value = MagicMock()
                    return AnalysisService()
    
    def test_normalize_product_name_basic(self, analysis_service):
        """Test basic product name normalization."""
        # Test removing spaces and special characters
        result = analysis_service._normalize_product_name("오리온 초코파이 (12개입)")
        assert result == "오리온초코파이12개입"
        
        # Test with English and numbers
        result = analysis_service._normalize_product_name("Coca Cola 500ml")
        assert result == "CocaCola500ml"
        
        # Test empty string
        result = analysis_service._normalize_product_name("")
        assert result == ""
        
        # Test None
        result = analysis_service._normalize_product_name(None)
        assert result == ""
    
    def test_normalize_product_name_special_cases(self, analysis_service):
        """Test product name normalization with special cases."""
        # Test with various special characters
        result = analysis_service._normalize_product_name("농심 신라면 (120g) - 매운맛!")
        assert result == "농심신라면120g매운맛"
        
        # Test with mixed Korean, English, numbers
        result = analysis_service._normalize_product_name("롯데 ABC초콜릿 50g")
        assert result == "롯데ABC초콜릿50g"
    
    def test_extract_nutrition_values_complete(self, analysis_service):
        """Test nutrition value extraction with complete data."""
        nutrition_data = {
            'energy': '250kcal',
            'carbohydrate': '30g',
            'sugar': '15g',
            'protein': '5g',
            'fat': '12g',
            'sat_fat': '6g',
            'trans_fat': '0g',
            'sodium': '200mg',
            'calcium': '100mg',
            'cholesterol': '10mg',
            'dietary_fiber': '2g'
        }
        
        result = analysis_service._extract_nutrition_values(nutrition_data)
        
        assert isinstance(result, NutritionInfo)
        assert result.energy == "250"
        assert result.carbohydrate == "30"
        assert result.sugar == "15"
        assert result.protein == "5"
        assert result.fat == "12"
        assert result.sat_fat == "6"
        assert result.trans_fat == "0"
        assert result.sodium == "200"
        assert result.calcium == "100"
        assert result.cholesterol == "10"
        assert result.dietary_fiber == "2"
    
    def test_extract_nutrition_values_missing_data(self, analysis_service):
        """Test nutrition value extraction with missing data."""
        nutrition_data = {
            'energy': '250kcal',
            'carbohydrate': 'null',
            'protein': '정보없음',
            'fat': '',
            'sodium': '200mg'
        }
        
        result = analysis_service._extract_nutrition_values(nutrition_data)
        
        assert result.energy == "250"
        assert result.carbohydrate is None
        assert result.protein is None
        assert result.fat is None
        assert result.sodium == "200"
        assert result.sugar is None  # Not provided in input
    
    def test_extract_nutrition_values_decimal_numbers(self, analysis_service):
        """Test nutrition value extraction with decimal numbers."""
        nutrition_data = {
            'energy': '250.5kcal',
            'fat': '12.3g',
            'protein': '5.7g'
        }
        
        result = analysis_service._extract_nutrition_values(nutrition_data)
        
        assert result.energy == "250.5"
        assert result.fat == "12.3"
        assert result.protein == "5.7"
    
    def test_parse_ingredients_basic(self, analysis_service):
        """Test basic ingredients parsing."""
        ingredients_text = "밀가루, 설탕, 식물성유지, 코코아분말"
        result = analysis_service._parse_ingredients(ingredients_text)
        
        assert result == ["밀가루", "설탕", "식물성유지", "코코아분말"]
    
    def test_parse_ingredients_various_delimiters(self, analysis_service):
        """Test ingredients parsing with various delimiters."""
        # Test with different comma types
        ingredients_text = "밀가루，설탕、식물성유지, 코코아분말"
        result = analysis_service._parse_ingredients(ingredients_text)
        
        assert result == ["밀가루", "설탕", "식물성유지", "코코아분말"]
    
    def test_parse_ingredients_empty_or_none(self, analysis_service):
        """Test ingredients parsing with empty or missing data."""
        # Test empty string
        result = analysis_service._parse_ingredients("")
        assert result is None
        
        # Test None
        result = analysis_service._parse_ingredients(None)
        assert result is None
        
        # Test "정보없음"
        result = analysis_service._parse_ingredients("정보없음")
        assert result is None
    
    def test_parse_ingredients_with_cleanup(self, analysis_service):
        """Test ingredients parsing with cleanup of common non-ingredients."""
        ingredients_text = "밀가루, 설탕, 식물성유지, 등, 기타"
        result = analysis_service._parse_ingredients(ingredients_text)
        
        assert result == ["밀가루", "설탕", "식물성유지"]
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_info_success_high_quality(self, analysis_service):
        """Test successful nutrition analysis with high quality."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "analysis_quality": "high",
            "product_name": "초코파이",
            "nutrition_info": {
                "energy": "250",
                "carbohydrate": "30",
                "protein": "5",
                "fat": "12",
                "sodium": "200"
            },
            "ingredients": "밀가루, 설탕, 식물성유지"
        })
        
        analysis_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        text = "초코파이 영양성분표 칼로리 250kcal 탄수화물 30g..."
        result = await analysis_service.analyze_nutrition_info(text)
        
        assert result["decodeStatus"] == DecodeStatus.COMPLETED
        assert result["product_name"] == "초코파이"
        assert result["nutrition_info"].energy == "250"
        assert result["nutrition_info"].carbohydrate == "30"
        assert result["ingredients"] == ["밀가루", "설탕", "식물성유지"]
        assert "successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_info_medium_quality(self, analysis_service):
        """Test nutrition analysis with medium quality."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "analysis_quality": "medium",
            "product_name": "초코파이",
            "nutrition_info": {
                "energy": "250",
                "carbohydrate": "정보없음",
                "protein": "5"
            },
            "ingredients": "밀가루, 설탕"
        })
        
        analysis_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        text = "흐린 초코파이 영양성분표..."
        result = await analysis_service.analyze_nutrition_info(text)
        
        assert result["decodeStatus"] == DecodeStatus.COMPLETED
        assert result["nutrition_info"].energy == "250"
        assert result["nutrition_info"].carbohydrate is None
        assert "missing information" in result["message"]
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_info_low_quality(self, analysis_service):
        """Test nutrition analysis with low quality."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "analysis_quality": "low",
            "product_name": "정보없음",
            "nutrition_info": {
                "energy": "정보없음"
            },
            "ingredients": "정보없음"
        })
        
        analysis_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        text = "매우 흐린 이미지 텍스트..."
        result = await analysis_service.analyze_nutrition_info(text)
        
        assert result["decodeStatus"] == DecodeStatus.FAILED
        assert result["product_name"] is None
        assert result["ingredients"] is None
        assert "too low" in result["message"]
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_info_empty_text(self, analysis_service):
        """Test nutrition analysis with empty text."""
        result = await analysis_service.analyze_nutrition_info("")
        
        assert result["decodeStatus"] == DecodeStatus.FAILED
        assert result["product_name"] is None
        assert result["nutrition_info"] is None
        assert result["ingredients"] is None
        assert "No text provided" in result["message"]
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_info_json_parse_error(self, analysis_service):
        """Test nutrition analysis with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.text = "Invalid JSON response"
        
        analysis_service.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        text = "Some nutrition text"
        result = await analysis_service.analyze_nutrition_info(text)
        
        assert result["decodeStatus"] == DecodeStatus.FAILED
        assert "Failed to parse" in result["message"]
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_info_api_error(self, analysis_service):
        """Test nutrition analysis with API error."""
        analysis_service.model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        text = "Some nutrition text"
        
        with pytest.raises(Exception) as exc_info:
            await analysis_service.analyze_nutrition_info(text)
        
        assert "Nutrition analysis failed" in str(exc_info.value)
    
    def test_init_without_api_key(self):
        """Test AnalysisService initialization without API key."""
        with patch('decodeat.services.analysis_service.settings') as mock_settings:
            mock_settings.gemini_api_key = None
            
            with pytest.raises(ValueError) as exc_info:
                AnalysisService()
            
            assert "GEMINI_API_KEY is required" in str(exc_info.value)