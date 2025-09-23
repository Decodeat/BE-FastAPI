"""
Tests for EnhancedVectorService
"""
import pytest
from unittest.mock import Mock, AsyncMock
from decodeat.services.enhanced_vector_service import EnhancedVectorService, NutritionDataError


class TestEnhancedVectorService:
    """Test cases for EnhancedVectorService"""
    
    @pytest.fixture
    def enhanced_vector_service(self):
        """Create EnhancedVectorService instance for testing"""
        service = EnhancedVectorService()
        service.client = Mock()
        service.collection = Mock()
        service.model = Mock()
        return service
    
    def test_calculate_nutrition_ratios_normal_data(self, enhanced_vector_service):
        """Test nutrition ratio calculation with normal data"""
        nutrition_info = {
            'energy': '200',
            'carbohydrate': '30',  # 30g * 4kcal/g = 120kcal
            'protein': '10',       # 10g * 4kcal/g = 40kcal
            'fat': '5'            # 5g * 9kcal/g = 45kcal
        }
        
        ratios = enhanced_vector_service.calculate_nutrition_ratios(nutrition_info)
        
        # Total calculated calories: 120 + 40 + 45 = 205kcal
        # But we use provided energy (200kcal) as base
        expected_carb_ratio = (120 / 200) * 100  # 60%
        expected_protein_ratio = (40 / 200) * 100  # 20%
        expected_fat_ratio = (45 / 200) * 100  # 22.5%
        
        assert ratios['carbohydrate_ratio'] == expected_carb_ratio
        assert ratios['protein_ratio'] == expected_protein_ratio
        assert ratios['fat_ratio'] == expected_fat_ratio
        assert ratios['total_calories'] == 200
    
    def test_calculate_nutrition_ratios_missing_energy(self, enhanced_vector_service):
        """Test nutrition ratio calculation when energy is missing"""
        nutrition_info = {
            'carbohydrate': '20',  # 20g * 4kcal/g = 80kcal
            'protein': '15',       # 15g * 4kcal/g = 60kcal
            'fat': '10'           # 10g * 9kcal/g = 90kcal
        }
        
        ratios = enhanced_vector_service.calculate_nutrition_ratios(nutrition_info)
        
        # Should use calculated calories: 80 + 60 + 90 = 230kcal
        expected_carb_ratio = (80 / 230) * 100
        expected_protein_ratio = (60 / 230) * 100
        expected_fat_ratio = (90 / 230) * 100
        
        assert abs(ratios['carbohydrate_ratio'] - expected_carb_ratio) < 0.01
        assert abs(ratios['protein_ratio'] - expected_protein_ratio) < 0.01
        assert abs(ratios['fat_ratio'] - expected_fat_ratio) < 0.01
        assert ratios['total_calories'] == 230
    
    def test_calculate_nutrition_ratios_invalid_data(self, enhanced_vector_service):
        """Test nutrition ratio calculation with invalid data"""
        nutrition_info = {
            'energy': 'invalid',
            'carbohydrate': '-10',
            'protein': 'abc',
            'fat': '5'
        }
        
        ratios = enhanced_vector_service.calculate_nutrition_ratios(nutrition_info)
        
        # Should return zero ratios for invalid data
        assert ratios['carbohydrate_ratio'] == 0
        assert ratios['protein_ratio'] == 0
        assert ratios['fat_ratio'] == 0
        assert ratios['total_calories'] == 0
    
    def test_calculate_nutrition_ratios_empty_data(self, enhanced_vector_service):
        """Test nutrition ratio calculation with empty data"""
        ratios = enhanced_vector_service.calculate_nutrition_ratios({})
        
        assert ratios['carbohydrate_ratio'] == 0
        assert ratios['protein_ratio'] == 0
        assert ratios['fat_ratio'] == 0
        assert ratios['total_calories'] == 0
    
    def test_extract_main_ingredients_normal_data(self, enhanced_vector_service):
        """Test main ingredients extraction with normal data"""
        ingredients = ['밀가루', '설탕', '버터', '계란', '우유', '소금', '바닐라']
        
        main_ingredients = enhanced_vector_service.extract_main_ingredients(ingredients, max_count=5)
        
        assert len(main_ingredients) == 5
        assert main_ingredients == ['밀가루', '설탕', '버터', '계란', '우유']
    
    def test_extract_main_ingredients_with_duplicates(self, enhanced_vector_service):
        """Test main ingredients extraction with duplicates"""
        ingredients = ['밀가루', '설탕', '밀가루', '버터', '설탕', '계란']
        
        main_ingredients = enhanced_vector_service.extract_main_ingredients(ingredients)
        
        # Should remove duplicates and maintain order
        assert len(main_ingredients) == 4
        assert main_ingredients == ['밀가루', '설탕', '버터', '계란']
    
    def test_extract_main_ingredients_empty_data(self, enhanced_vector_service):
        """Test main ingredients extraction with empty data"""
        main_ingredients = enhanced_vector_service.extract_main_ingredients([])
        
        assert main_ingredients == []
    
    def test_extract_main_ingredients_with_empty_strings(self, enhanced_vector_service):
        """Test main ingredients extraction with empty strings"""
        ingredients = ['밀가루', '', '설탕', None, '  ', '버터']
        
        main_ingredients = enhanced_vector_service.extract_main_ingredients(ingredients)
        
        # Should filter out empty/None values
        assert main_ingredients == ['밀가루', '설탕', '버터']
    
    @pytest.mark.asyncio
    async def test_store_product_with_id_success(self, enhanced_vector_service):
        """Test successful product storage with ID"""
        # Mock ChromaDB availability
        enhanced_vector_service.is_chromadb_available = Mock(return_value=True)
        enhanced_vector_service.delete_product_vector = AsyncMock(return_value=True)
        enhanced_vector_service.generate_product_vector = AsyncMock(return_value=[0.1] * 384)
        
        # Mock collection.get to simulate no existing data
        enhanced_vector_service.collection.get.return_value = {'ids': []}
        enhanced_vector_service.collection.add = Mock()
        
        product_data = {
            'product_name': '테스트 제품',
            'nutrition_info': {
                'energy': '200',
                'carbohydrate': '30',
                'protein': '10',
                'fat': '5'
            },
            'ingredients': ['밀가루', '설탕', '버터']
        }
        
        result = await enhanced_vector_service.store_product_with_id(12345, product_data)
        
        assert result is True
        enhanced_vector_service.collection.add.assert_called_once()
        
        # Check that metadata includes nutrition ratios
        call_args = enhanced_vector_service.collection.add.call_args
        metadata = call_args[1]['metadatas'][0]
        assert metadata['product_id'] == 12345
        assert metadata['product_name'] == '테스트 제품'
        assert 'carbohydrate_ratio' in metadata
        assert 'protein_ratio' in metadata
        assert 'fat_ratio' in metadata
        assert metadata['main_ingredients'] == '밀가루, 설탕, 버터'
    
    @pytest.mark.asyncio
    async def test_store_product_with_id_chromadb_unavailable(self, enhanced_vector_service):
        """Test product storage when ChromaDB is unavailable"""
        enhanced_vector_service.is_chromadb_available = Mock(return_value=False)
        
        product_data = {'product_name': '테스트 제품'}
        
        result = await enhanced_vector_service.store_product_with_id(12345, product_data)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_product_by_id_success(self, enhanced_vector_service):
        """Test successful product retrieval by ID"""
        enhanced_vector_service.is_chromadb_available = Mock(return_value=True)
        
        # Mock collection response
        mock_metadata = {
            'product_id': 12345,
            'product_name': '테스트 제품',
            'carbohydrate_ratio': 60.0,
            'protein_ratio': 20.0,
            'fat_ratio': 20.0,
            'total_calories': 200,
            'main_ingredients': '밀가루, 설탕, 버터',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        
        enhanced_vector_service.collection.get.return_value = {
            'ids': ['12345'],
            'metadatas': [mock_metadata],
            'embeddings': [[0.1] * 384]
        }
        
        result = await enhanced_vector_service.get_product_by_id(12345)
        
        assert result is not None
        assert result['product_id'] == 12345
        assert result['product_name'] == '테스트 제품'
        assert result['nutrition_ratios']['carbohydrate_ratio'] == 60.0
        assert result['main_ingredients'] == ['밀가루', '설탕', '버터']
        assert len(result['embedding']) == 384
    
    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(self, enhanced_vector_service):
        """Test product retrieval when product is not found"""
        enhanced_vector_service.is_chromadb_available = Mock(return_value=True)
        enhanced_vector_service.collection.get.return_value = {'ids': []}
        
        result = await enhanced_vector_service.get_product_by_id(99999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_product_by_id_chromadb_unavailable(self, enhanced_vector_service):
        """Test product retrieval when ChromaDB is unavailable"""
        enhanced_vector_service.is_chromadb_available = Mock(return_value=False)
        
        result = await enhanced_vector_service.get_product_by_id(12345)
        
        assert result is None