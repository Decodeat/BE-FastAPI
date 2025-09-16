"""
Integration tests for the complete recommendation system.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from decodeat.services.vector_service import VectorService
from decodeat.services.recommendation_service import RecommendationService
from decodeat.api.models import (
    UserBasedRecommendationRequest,
    ProductBasedRecommendationRequest,
    UserBehavior,
    RecommendationResponse
)
from decodeat.utils.performance import performance_monitor, recommendation_cache


class TestRecommendationSystemIntegration:
    """Integration tests for the complete recommendation system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear performance metrics and cache
        performance_monitor.clear_metrics()
        recommendation_cache.clear()
        
        # Mock vector service
        self.mock_vector_service = Mock(spec=VectorService)
        self.mock_vector_service.is_chromadb_available.return_value = True
        
        # Initialize recommendation service
        self.recommendation_service = RecommendationService(self.mock_vector_service)
        
    @pytest.mark.asyncio
    async def test_complete_user_based_recommendation_flow(self):
        """Test complete user-based recommendation flow."""
        # Mock user behavior data
        behavior_data = [
            {'product_id': 1001, 'behavior_type': 'VIEW', 'timestamp': datetime.now()},
            {'product_id': 1001, 'behavior_type': 'LIKE', 'timestamp': datetime.now()},
            {'product_id': 1002, 'behavior_type': 'REGISTER', 'timestamp': datetime.now()},
        ]
        
        # Mock vector service responses
        mock_vectors = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
        self.mock_vector_service.collection.get.return_value = {
            'embeddings': mock_vectors
        }
        
        mock_recommendations = [
            {'product_id': 2001, 'similarity_score': 0.85, 'recommendation_reason': '유사한 제품'},
            {'product_id': 2002, 'similarity_score': 0.78, 'recommendation_reason': '관련 제품'}
        ]
        self.mock_vector_service.search_by_user_preferences = AsyncMock(return_value=mock_recommendations)
        
        # Execute recommendation flow
        recommendations = await self.recommendation_service.get_enhanced_user_based_recommendations(
            user_id=12345,
            behavior_data=behavior_data,
            limit=10
        )
        
        # Verify results
        assert len(recommendations) == 2
        assert recommendations[0]['product_id'] == 2001
        assert recommendations[0]['similarity_score'] == 0.85
        assert 'recommendation_reason' in recommendations[0]
        
        # Verify performance metrics were recorded
        stats = performance_monitor.get_metric_stats("enhanced_user_based_recommendations")
        assert stats['count'] == 1
        assert stats['avg'] > 0
        
    @pytest.mark.asyncio
    async def test_complete_product_based_recommendation_flow(self):
        """Test complete product-based recommendation flow."""
        product_id = 1001
        
        # Mock vector service responses
        mock_recommendations = [
            {'product_id': 2001, 'similarity_score': 0.92, 'recommendation_reason': '매우 유사한 제품'},
            {'product_id': 2002, 'similarity_score': 0.87, 'recommendation_reason': '유사한 제품'},
            {'product_id': 2003, 'similarity_score': 0.75, 'recommendation_reason': '관련 제품'}
        ]
        self.mock_vector_service.find_similar_products = AsyncMock(return_value=mock_recommendations)
        
        # Execute recommendation flow
        recommendations = await self.recommendation_service.get_product_based_recommendations(
            product_id=product_id,
            limit=5
        )
        
        # Verify results
        assert len(recommendations) == 3
        assert recommendations[0]['product_id'] == 2001
        assert recommendations[0]['similarity_score'] == 0.92
        
        # Verify caching worked
        cached_result = recommendation_cache.get(
            type="product_based",
            product_id=product_id,
            limit=5
        )
        assert cached_result == recommendations
        
        # Verify performance metrics were recorded
        stats = performance_monitor.get_metric_stats("product_based_recommendations")
        assert stats['count'] == 1
        
    @pytest.mark.asyncio
    async def test_fallback_recommendation_flow(self):
        """Test fallback recommendation when primary methods fail."""
        # Mock ChromaDB as unavailable
        self.mock_vector_service.is_chromadb_available.return_value = False
        
        # Mock fallback recommendations
        fallback_recommendations = [
            {'product_id': 3001, 'similarity_score': 0.5, 'recommendation_reason': '인기 제품'},
            {'product_id': 3002, 'similarity_score': 0.45, 'recommendation_reason': '인기 제품'}
        ]
        
        with patch.object(self.recommendation_service, 'get_popularity_based_fallback', 
                         return_value=fallback_recommendations) as mock_fallback:
            
            recommendations = await self.recommendation_service.get_product_based_recommendations(
                product_id=1001,
                limit=5
            )
            
            # Verify fallback was called
            mock_fallback.assert_called_once_with(5)
            assert recommendations == fallback_recommendations
            
    @pytest.mark.asyncio
    async def test_user_behavior_analysis_integration(self):
        """Test user behavior analysis integration."""
        # Create diverse behavior data
        behavior_data = [
            {'product_id': 1001, 'behavior_type': 'VIEW', 'timestamp': datetime.now()},
            {'product_id': 1001, 'behavior_type': 'LIKE', 'timestamp': datetime.now()},
            {'product_id': 1002, 'behavior_type': 'REGISTER', 'timestamp': datetime.now()},
            {'product_id': 1003, 'behavior_type': 'SEARCH', 'timestamp': datetime.now()},
            {'product_id': 1004, 'behavior_type': 'LIKE', 'timestamp': datetime.now()},
        ]
        
        # Analyze behavior patterns
        analysis = self.recommendation_service.analyze_user_behavior_patterns(behavior_data)
        
        # Verify analysis results
        assert analysis['total_interactions'] == 5
        assert analysis['total_score'] == 12  # 1+3+5+2+3
        assert analysis['average_score_per_interaction'] == 2.4
        assert analysis['engagement_level'] == 'medium'
        assert analysis['most_common_behavior'] == 'LIKE'
        
        # Test profile creation
        user_profile = await self.recommendation_service.create_user_preference_profile(
            user_id=12345,
            behavior_data=behavior_data
        )
        
        assert user_profile['user_id'] == 12345
        assert user_profile['behavior_analysis'] == analysis
        assert user_profile['interacted_products'] == [1001, 1002, 1003, 1004]
        
    @pytest.mark.asyncio
    async def test_recommendation_quality_evaluation(self):
        """Test recommendation quality evaluation."""
        # Test excellent quality
        excellent_recommendations = [
            {'product_id': i, 'similarity_score': 0.9 + (i * 0.001)} 
            for i in range(15)
        ]
        excellent_behavior = {
            'engagement_level': 'very_high',
            'total_interactions': 20
        }
        
        quality = self.recommendation_service.evaluate_recommendation_quality(
            excellent_recommendations, excellent_behavior
        )
        assert quality == 'excellent'
        
        # Test poor quality
        poor_recommendations = []
        poor_behavior = {
            'engagement_level': 'low',
            'total_interactions': 1
        }
        
        quality = self.recommendation_service.evaluate_recommendation_quality(
            poor_recommendations, poor_behavior
        )
        assert quality == 'poor'
        
    @pytest.mark.asyncio
    async def test_personalized_recommendation_reasons(self):
        """Test personalized recommendation reason generation."""
        # High engagement user
        high_engagement_analysis = {
            'engagement_level': 'very_high',
            'most_common_behavior': 'REGISTER',
            'total_interactions': 15
        }
        
        reason = self.recommendation_service.generate_personalized_recommendation_reason(
            high_engagement_analysis,
            {'product_name': '테스트 제품'},
            0.9
        )
        
        assert '자주 등록하시는 제품과' in reason
        assert '매우 유사한 영양성분' in reason
        
        # Low engagement user
        low_engagement_analysis = {
            'engagement_level': 'low',
            'most_common_behavior': 'VIEW',
            'total_interactions': 2
        }
        
        reason = self.recommendation_service.generate_personalized_recommendation_reason(
            low_engagement_analysis,
            {'product_name': '테스트 제품'},
            0.7
        )
        
        assert '추천' in reason
        
    @pytest.mark.asyncio
    async def test_caching_performance(self):
        """Test caching improves performance."""
        product_id = 1001
        limit = 10
        
        # Mock slow vector service
        async def slow_find_similar_products(pid, lim):
            await asyncio.sleep(0.01)  # Simulate slow operation
            return [{'product_id': 2001, 'similarity_score': 0.8, 'recommendation_reason': '유사'}]
        
        self.mock_vector_service.find_similar_products = slow_find_similar_products
        
        # First call (should be slow)
        start_time = asyncio.get_event_loop().time()
        recommendations1 = await self.recommendation_service.get_product_based_recommendations(
            product_id, limit
        )
        first_call_time = asyncio.get_event_loop().time() - start_time
        
        # Second call (should be fast due to caching)
        start_time = asyncio.get_event_loop().time()
        recommendations2 = await self.recommendation_service.get_product_based_recommendations(
            product_id, limit
        )
        second_call_time = asyncio.get_event_loop().time() - start_time
        
        # Verify results are the same
        assert recommendations1 == recommendations2
        
        # Verify second call was faster (cached)
        assert second_call_time < first_call_time
        
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        # Mock vector service to raise exception
        self.mock_vector_service.find_similar_products = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        # Mock fallback to work
        fallback_recommendations = [
            {'product_id': 3001, 'similarity_score': 0.5, 'recommendation_reason': '인기 제품'}
        ]
        
        with patch.object(self.recommendation_service, 'get_fallback_recommendations',
                         return_value=fallback_recommendations) as mock_fallback:
            
            recommendations = await self.recommendation_service.get_product_based_recommendations(
                product_id=1001,
                limit=5
            )
            
            # Should fall back to alternative recommendations
            mock_fallback.assert_called_once()
            assert recommendations == fallback_recommendations
            
    def test_api_model_validation(self):
        """Test API model validation."""
        # Valid user-based request
        valid_request = UserBasedRecommendationRequest(
            user_id=12345,
            behavior_data=[
                UserBehavior(product_id=1001, behavior_type='LIKE'),
                UserBehavior(product_id=1002, behavior_type='VIEW')
            ],
            limit=10
        )
        
        assert valid_request.user_id == 12345
        assert len(valid_request.behavior_data) == 2
        assert valid_request.limit == 10
        
        # Valid product-based request
        valid_product_request = ProductBasedRecommendationRequest(
            product_id=1001,
            limit=15
        )
        
        assert valid_product_request.product_id == 1001
        assert valid_product_request.limit == 15
        
        # Test invalid behavior type
        with pytest.raises(ValueError):
            UserBehavior(product_id=1001, behavior_type='INVALID_TYPE')
            
        # Test limit validation
        with pytest.raises(ValueError):
            ProductBasedRecommendationRequest(product_id=1001, limit=100)  # Over max limit


if __name__ == "__main__":
    pytest.main([__file__])