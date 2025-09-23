"""
통합 추천 서비스 - 상품 기반과 사용자 행동 기반 추천을 통합하는 인터페이스
"""
from typing import List, Dict, Any, Optional

from decodeat.services.enhanced_vector_service import EnhancedVectorService
from decodeat.services.product_based_recommendation_service import ProductBasedRecommendationService
from decodeat.services.user_behavior_recommendation_service import UserBehaviorRecommendationService
from decodeat.utils.logging import LoggingService
from decodeat.utils.performance import measure_time, recommendation_cache

logger = LoggingService(__name__)


class RecommendationService:
    """통합 추천 서비스 - 기존 API 호환성을 유지하면서 새로운 알고리즘 사용"""
    
    def __init__(self, vector_service):
        """
        통합 추천 서비스 초기화.
        
        Args:
            vector_service: 벡터 서비스 인스턴스 (VectorService 또는 EnhancedVectorService)
        """
        # 기존 VectorService와의 호환성을 위해 EnhancedVectorService로 래핑
        if isinstance(vector_service, EnhancedVectorService):
            self.vector_service = vector_service
        else:
            # 기존 VectorService를 EnhancedVectorService로 업그레이드
            enhanced_service = EnhancedVectorService(
                chroma_host=vector_service.chroma_host,
                chroma_port=vector_service.chroma_port
            )
            # 기존 연결 상태 복사
            enhanced_service.client = vector_service.client
            enhanced_service.collection = vector_service.collection
            enhanced_service.model = vector_service.model
            self.vector_service = enhanced_service
        
        # 전문 추천 서비스들 초기화
        self.product_service = ProductBasedRecommendationService(self.vector_service)
        self.user_service = UserBehaviorRecommendationService(self.vector_service)
        
    async def get_product_based_recommendations(
        self, 
        product_id: int, 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        상품 기반 추천 생성 (새로운 영양소 구성비 + 원재료 유사도 알고리즘 사용).
        
        Args:
            product_id: 기준이 되는 제품 ID
            limit: 최대 추천 개수
            
        Returns:
            유사한 제품 리스트 (영양소/원재료 유사도 포함)
        """
        try:
            logger.info(f"Generating enhanced product-based recommendations for product {product_id}")
            
            # Check cache first
            cached_result = recommendation_cache.get(
                type="enhanced_product_based",
                product_id=product_id,
                limit=limit
            )
            if cached_result:
                logger.debug(f"Using cached enhanced recommendations for product {product_id}")
                return cached_result
            
            # Use new product-based recommendation service
            recommendations = await self.product_service.get_recommendations(product_id, limit)
            
            if not recommendations:
                logger.warning(f"No enhanced recommendations found for product {product_id}, trying fallback")
                return await self.get_fallback_recommendations(limit)
            
            # Cache the results
            recommendation_cache.set(
                recommendations,
                type="enhanced_product_based",
                product_id=product_id,
                limit=limit
            )
            
            logger.info(f"Generated {len(recommendations)} enhanced product-based recommendations for product {product_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get enhanced product-based recommendations for product {product_id}: {e}")
            return await self.get_fallback_recommendations(limit)
    
    async def get_user_based_recommendations(
        self, 
        user_id: int,
        behavior_data: List[Dict[str, Any]], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        사용자 행동 기반 개인화 추천 생성.
        
        Args:
            user_id: 사용자 식별자
            behavior_data: 사용자의 행동 이력
            limit: 최대 추천 개수
            
        Returns:
            추천 제품 리스트
        """
        try:
            logger.info(f"Generating user-based recommendations for user {user_id}")
            
            # Use new user behavior recommendation service
            recommendations = await self.user_service.get_recommendations(user_id, behavior_data, limit)
            
            if not recommendations:
                logger.warning(f"No user-based recommendations found for user {user_id}, trying fallback")
                return await self.get_fallback_recommendations(limit)
            
            logger.info(f"Generated {len(recommendations)} user-based recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get user-based recommendations for user {user_id}: {e}")
            return await self.get_fallback_recommendations(limit)
    
    # 기존 API 호환성을 위한 위임 메서드들
    def analyze_user_behavior_patterns(self, behavior_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """사용자 행동 패턴 분석 (UserBehaviorRecommendationService로 위임)"""
        return self.user_service.analyze_user_behavior_patterns(behavior_data)
    
    async def create_user_preference_profile(
        self, 
        user_id: int, 
        behavior_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """사용자 선호도 프로필 생성 (UserBehaviorRecommendationService로 위임)"""
        return await self.user_service.create_user_preference_profile(user_id, behavior_data)
    
    async def generate_user_preference_vector(
        self, 
        behavior_data: List[Dict[str, Any]]
    ) -> Optional[List[float]]:
        """사용자 선호도 벡터 생성 (UserBehaviorRecommendationService로 위임)"""
        return await self.user_service.generate_user_preference_vector(behavior_data)
    
    async def get_enhanced_user_based_recommendations(
        self, 
        user_id: int,
        behavior_data: List[Dict[str, Any]], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        향상된 사용자 기반 추천 (UserBehaviorRecommendationService로 위임).
        
        Args:
            user_id: 사용자 식별자
            behavior_data: 사용자의 행동 이력
            limit: 최대 추천 개수
            
        Returns:
            개인화된 추천 제품 리스트
        """
        return await self.user_service.get_recommendations(user_id, behavior_data, limit)
    
    def evaluate_recommendation_quality(
        self, 
        recommendations: List[Dict[str, Any]], 
        user_behavior_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        추천 품질 평가.
        
        Args:
            recommendations: 추천 결과 리스트
            user_behavior_analysis: 사용자 행동 분석 결과
            
        Returns:
            품질 등급: excellent, good, fair, poor
        """
        try:
            if not recommendations:
                return "poor"
            
            # Check number of recommendations
            rec_count = len(recommendations)
            
            # Check average similarity score
            avg_similarity = sum(rec.get('similarity_score', 0) for rec in recommendations) / rec_count
            
            # Check user behavior quality if available
            behavior_quality = "fair"
            if user_behavior_analysis:
                engagement_level = user_behavior_analysis.get('engagement_level', 'low')
                total_interactions = user_behavior_analysis.get('total_interactions', 0)
                
                if engagement_level in ['very_high', 'high'] and total_interactions >= 10:
                    behavior_quality = "excellent"
                elif engagement_level in ['high', 'medium'] and total_interactions >= 5:
                    behavior_quality = "good"
                elif total_interactions >= 3:
                    behavior_quality = "fair"
                else:
                    behavior_quality = "poor"
            
            # Determine overall quality
            if avg_similarity >= 0.8 and rec_count >= 10 and behavior_quality in ["excellent", "good"]:
                return "excellent"
            elif avg_similarity >= 0.7 and rec_count >= 5 and behavior_quality in ["good", "fair"]:
                return "good"
            elif avg_similarity >= 0.6 and rec_count >= 3:
                return "fair"
            else:
                return "poor"
                
        except Exception as e:
            logger.error(f"Failed to evaluate recommendation quality: {e}")
            return "poor"
    
    async def get_fallback_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """대체 추천 제공"""
        return await self.get_popularity_based_fallback(limit)
    
    async def get_popularity_based_fallback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        인기도 기반 대체 추천.
        
        Args:
            limit: 최대 추천 개수
            
        Returns:
            인기 제품 추천 리스트
        """
        try:
            logger.info("Generating popularity-based fallback recommendations")
            
            if not self.vector_service.is_chromadb_available():
                logger.warning("ChromaDB not available for popularity-based fallback")
                return []
            
            # Get collection info
            collection_info = await self.vector_service.get_collection_info()
            
            if collection_info.get('count', 0) == 0:
                logger.warning("No products available for popularity-based fallback")
                return []
            
            # Get random products as popularity fallback (simplified)
            try:
                results = self.vector_service.collection.get(
                    limit=min(limit, collection_info['count']),
                    include=['metadatas']
                )
                
                fallback_recommendations = []
                for i, metadata in enumerate(results['metadatas']):
                    # Simulate popularity score (higher for earlier results)
                    popularity_score = max(0.3, 0.8 - (i * 0.05))
                    
                    fallback_recommendations.append({
                        'product_id': metadata['product_id'],
                        'similarity_score': popularity_score,
                        'recommendation_reason': '인기 제품',
                        'recommendation_type': 'popularity'
                    })
                
                logger.info(f"Generated {len(fallback_recommendations)} popularity-based recommendations")
                return fallback_recommendations
                
            except Exception as e:
                logger.error(f"Failed to get products for popularity fallback: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get popularity-based fallback: {e}")
            return []