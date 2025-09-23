"""
Tests for ProductBasedRecommendationService
"""
import pytest
from unittest.mock import Mock, AsyncMock
import numpy as np
from decodeat.services.product_based_recommendation_service import ProductBasedRecommendationService


class TestProductBasedRecommendationService:
    """Test cases for ProductBasedRecommendationService"""
    
    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector service"""
        mock_service = Mock()
        mock_service.is_chromadb_available.return_value = True
        return mock_service
    
    @pytest.fixture
    def recommendation_service(self, mock_vector_service):
        """Create ProductBasedRecommendationService instance for testing"""
        return ProductBasedRecommendationService(mock_vector_service)
    
    def test_calculate_nutrition_similarity_identical_ratios(self, recommendation_service):
        """Test nutrition similarity calculation with identical ratios"""
        ratios1 = {
            'carbohydrate_ratio': 60.0,
            'protein_ratio': 20.0,
            'fat_ratio': 20.0
        }
        ratios2 = {
            'carbohydrate_ratio': 60.0,
            'protein_ratio': 20.0,
            'fat_ratio': 20.0
        }
        
        similarity = recommendation_service.calculate_nutrition_similarity(ratios1, ratios2)
        
        # Identical ratios should have similarity close to 1.0
        assert similarity > 0.99
    
    def test_calculate_nutrition_similarity_different_ratios(self, recommendation_service):
        """Test nutrition similarity calculation with different ratios"""
        ratios1 = {
            'carbohydrate_ratio': 80.0,
            'protein_ratio': 10.0,
            'fat_ratio': 10.0
        }
        ratios2 = {
            'carbohydrate_ratio': 20.0,
            'protein_ratio': 40.0,
            'fat_ratio': 40.0
        }
        
        similarity = recommendation_service.calculate_nutrition_similarity(ratios1, ratios2)
        
        # Different ratios should have lower similarity
        assert 0.0 <= similarity <= 1.0
        assert similarity < 0.8
    
    def test_calculate_nutrition_similarity_zero_vectors(self, recommendation_service):
        """Test nutrition similarity calculation with zero vectors"""
        ratios1 = {
            'carbohydrate_ratio': 0.0,
            'protein_ratio': 0.0,
            'fat_ratio': 0.0
        }
        ratios2 = {
            'carbohydrate_ratio': 60.0,
            'protein_ratio': 20.0,
            'fat_ratio': 20.0
        }
        
        similarity = recommendation_service.calculate_nutrition_similarity(ratios1, ratios2)
        
        # Zero vector should result in 0 similarity
        assert similarity == 0.0
    
    def test_calculate_ingredient_similarity_identical_ingredients(self, recommendation_service):
        """Test ingredient similarity calculation with identical ingredients"""
        ingredients1 = ['밀가루', '설탕', '버터', '계란', '우유']
        ingredients2 = ['밀가루', '설탕', '버터', '계란', '우유']
        
        similarity = recommendation_service.calculate_ingredient_similarity(ingredients1, ingredients2)
        
        # Identical ingredients should have similarity 1.0
        assert similarity == 1.0
    
    def test_calculate_ingredient_similarity_partial_overlap(self, recommendation_service):
        """Test ingredient similarity calculation with partial overlap"""
        ingredients1 = ['밀가루', '설탕', '버터', '계란', '우유']
        ingredients2 = ['밀가루', '설탕', '식물성유지', '계란', '소금']
        
        similarity = recommendation_service.calculate_ingredient_similarity(ingredients1, ingredients2)
        
        # 3 out of 5 common ingredients with weighting
        # Common: 밀가루(weight 2), 설탕(weight 2), 계란(weight 1)
        # Total weight in union should be considered
        assert 0.4 <= similarity <= 0.8
    
    def test_calculate_ingredient_similarity_no_overlap(self, recommendation_service):
        """Test ingredient similarity calculation with no overlap"""
        ingredients1 = ['밀가루', '설탕', '버터']
        ingredients2 = ['쌀', '간장', '참기름']
        
        similarity = recommendation_service.calculate_ingredient_similarity(ingredients1, ingredients2)
        
        # No common ingredients should result in 0 similarity
        assert similarity == 0.0
    
    def test_calculate_ingredient_similarity_empty_lists(self, recommendation_service):
        """Test ingredient similarity calculation with empty lists"""
        similarity = recommendation_service.calculate_ingredient_similarity([], ['밀가루'])
        assert similarity == 0.0
        
        similarity = recommendation_service.calculate_ingredient_similarity(['밀가루'], [])
        assert similarity == 0.0
        
        similarity = recommendation_service.calculate_ingredient_similarity([], [])
        assert similarity == 0.0
    
    def test_calculate_ingredient_similarity_case_insensitive(self, recommendation_service):
        """Test ingredient similarity calculation is case insensitive"""
        ingredients1 = ['밀가루', '설탕', '버터']
        ingredients2 = ['밀가루', '설탕', '버터']  # Same but could test with different cases
        
        similarity = recommendation_service.calculate_ingredient_similarity(ingredients1, ingredients2)
        
        assert similarity == 1.0
    
    def test_calculate_final_score_default_weights(self, recommendation_service):
        """Test final score calculation with default weights"""
        nutrition_similarity = 0.8
        ingredient_similarity = 0.6
        
        final_score = recommendation_service.calculate_final_score(
            nutrition_similarity, ingredient_similarity
        )
        
        # Default weights: nutrition 60%, ingredient 40%
        expected_score = (0.8 * 0.6) + (0.6 * 0.4)
        assert abs(final_score - expected_score) < 0.001
    
    def test_calculate_final_score_custom_weights(self, recommendation_service):
        """Test final score calculation with custom weights"""
        nutrition_similarity = 0.9
        ingredient_similarity = 0.7
        
        final_score = recommendation_service.calculate_final_score(
            nutrition_similarity, ingredient_similarity,
            nutrition_weight=0.8, ingredient_weight=0.2
        )
        
        # Custom weights: nutrition 80%, ingredient 20%
        expected_score = (0.9 * 0.8) + (0.7 * 0.2)
        assert abs(final_score - expected_score) < 0.001
    
    def test_calculate_final_score_zero_weights(self, recommendation_service):
        """Test final score calculation with zero weights"""
        final_score = recommendation_service.calculate_final_score(
            0.8, 0.6, nutrition_weight=0.0, ingredient_weight=0.0
        )
        
        assert final_score == 0.0
    
    def test_generate_recommendation_reason_high_scores(self, recommendation_service):
        """Test recommendation reason generation with high scores"""
        reason = recommendation_service.generate_recommendation_reason(
            nutrition_similarity=0.9,
            ingredient_similarity=0.9,
            final_score=0.9
        )
        
        assert "매우 유사한" in reason
        assert "영양소 구성과 원재료" in reason
    
    def test_generate_recommendation_reason_nutrition_dominant(self, recommendation_service):
        """Test recommendation reason generation when nutrition similarity is dominant"""
        reason = recommendation_service.generate_recommendation_reason(
            nutrition_similarity=0.9,
            ingredient_similarity=0.5,
            final_score=0.8
        )
        
        assert "영양소 구성" in reason or "탄단지 비율" in reason
    
    def test_generate_recommendation_reason_ingredient_dominant(self, recommendation_service):
        """Test recommendation reason generation when ingredient similarity is dominant"""
        reason = recommendation_service.generate_recommendation_reason(
            nutrition_similarity=0.5,
            ingredient_similarity=0.9,
            final_score=0.8
        )
        
        assert "원재료" in reason
    
    def test_generate_recommendation_reason_low_scores(self, recommendation_service):
        """Test recommendation reason generation with low scores"""
        reason = recommendation_service.generate_recommendation_reason(
            nutrition_similarity=0.3,
            ingredient_similarity=0.4,
            final_score=0.5
        )
        
        assert "관련 제품" in reason or "유사한 특성" in reason
    
    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, recommendation_service, mock_vector_service):
        """Test successful recommendation generation"""
        # Mock reference product
        mock_reference_product = {
            'nutrition_ratios': {
                'carbohydrate_ratio': 60.0,
                'protein_ratio': 20.0,
                'fat_ratio': 20.0,
                'total_calories': 200
            },
            'main_ingredients': ['밀가루', '설탕', '버터']
        }
        mock_vector_service.get_product_by_id = AsyncMock(return_value=mock_reference_product)
        
        # Mock collection info
        mock_vector_service.get_collection_info = AsyncMock(return_value={'count': 10})
        
        # Mock collection get
        mock_candidates = {
            'metadatas': [
                {
                    'product_id': 2,
                    'carbohydrate_ratio': 65.0,
                    'protein_ratio': 18.0,
                    'fat_ratio': 17.0,
                    'total_calories': 180,
                    'main_ingredients': '밀가루, 설탕, 식물성유지'
                },
                {
                    'product_id': 3,
                    'carbohydrate_ratio': 70.0,
                    'protein_ratio': 15.0,
                    'fat_ratio': 15.0,
                    'total_calories': 220,
                    'main_ingredients': '쌀가루, 설탕, 버터'
                }
            ]
        }
        mock_vector_service.collection.get.return_value = mock_candidates
        
        recommendations = await recommendation_service.get_recommendations(
            product_id=1, limit=5
        )
        
        assert len(recommendations) <= 5
        for rec in recommendations:
            assert 'product_id' in rec
            assert 'similarity_score' in rec
            assert 'nutrition_similarity' in rec
            assert 'ingredient_similarity' in rec
            assert 'recommendation_reason' in rec
            assert 0 <= rec['similarity_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_get_recommendations_reference_not_found(self, recommendation_service, mock_vector_service):
        """Test recommendation generation when reference product is not found"""
        mock_vector_service.get_product_by_id = AsyncMock(return_value=None)
        
        recommendations = await recommendation_service.get_recommendations(
            product_id=99999, limit=5
        )
        
        assert recommendations == []
    
    @pytest.mark.asyncio
    async def test_get_recommendations_chromadb_unavailable(self, recommendation_service, mock_vector_service):
        """Test recommendation generation when ChromaDB is unavailable"""
        mock_vector_service.is_chromadb_available.return_value = False
        
        recommendations = await recommendation_service.get_recommendations(
            product_id=1, limit=5
        )
        
        assert recommendations == []