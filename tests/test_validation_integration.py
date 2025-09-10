"""
Integration tests for ValidationService.
These tests require actual API keys and will be skipped if not available.
"""
import pytest
import os
from decodeat.services.validation_service import ValidationService


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), 
    reason="GEMINI_API_KEY not available for integration testing"
)
class TestValidationServiceIntegration:
    """Integration tests for ValidationService with real API calls."""
    
    @pytest.fixture
    def validation_service(self):
        """Create a ValidationService instance for integration testing."""
        return ValidationService()
    
    @pytest.mark.asyncio
    async def test_validate_single_image_real_nutrition_text(self, validation_service):
        """Test validation with real nutrition information text."""
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
    
    @pytest.mark.asyncio
    async def test_validate_single_image_real_ingredient_text(self, validation_service):
        """Test validation with real ingredient information text."""
        ingredient_text = """
        원재료명: 정제수, 백설탕, 혼합분유(탈지분유, 유청분말), 
        식물성유지(팜유, 코코넛유), 코코아분말, 바닐라향, 
        유화제(레시틴), 안정제(카라기난), 비타민C
        """
        
        result = await validation_service.validate_single_image(ingredient_text)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_single_image_real_irrelevant_text(self, validation_service):
        """Test validation with irrelevant text."""
        irrelevant_text = """
        안녕하세요. 오늘은 날씨가 좋네요.
        이것은 영양성분과 전혀 관련이 없는 일반적인 텍스트입니다.
        컴퓨터 프로그래밍에 대해 이야기해보겠습니다.
        """
        
        result = await validation_service.validate_single_image(irrelevant_text)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_real_same_product(self, validation_service):
        """Test validation with real texts from the same product."""
        text1 = """
        코카콜라 제로
        영양성분 (1회 제공량 250ml당)
        열량 0kcal
        나트륨 15mg (1%)
        탄수화물 0g
        당류 0g
        지방 0g
        단백질 0g
        """
        
        text2 = """
        코카콜라 제로
        원재료명: 정제수, 이산화탄소, 카라멜색소, 
        인산, 아스파탐, 아세설팜칼륨, 천연향료
        제조사: 한국코카콜라
        """
        
        result = await validation_service.validate_image_pair(text1, text2)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_image_pair_real_different_products(self, validation_service):
        """Test validation with real texts from different products."""
        text1 = """
        코카콜라 제로
        영양성분 (1회 제공량 250ml당)
        열량 0kcal
        나트륨 15mg
        """
        
        text2 = """
        펩시콜라
        원재료명: 정제수, 이산화탄소, 설탕, 
        카라멜색소, 인산, 천연향료
        제조사: 롯데칠성음료
        """
        
        result = await validation_service.validate_image_pair(text1, text2)
        assert result is False