"""
User behavior-based recommendation service.
"""
from typing import List, Dict, Any, Optional
import numpy as np

from decodeat.services.enhanced_vector_service import EnhancedVectorService
from decodeat.utils.logging import LoggingService
from decodeat.utils.performance import measure_time

logger = LoggingService(__name__)


class UserBehaviorRecommendationService:
    """사용자 행동 기반 개인화 추천 서비스"""
    
    # 사용자 행동별 가중치
    BEHAVIOR_WEIGHTS = {
        'REGISTER': 5,  # 직접 등록 = 가장 강한 관심
        'LIKE': 3,      # 좋아요 = 선호
        'SEARCH': 2,    # 검색 = 관심
        'VIEW': 1       # 조회 = 기본 관심
    }
    
    def __init__(self, vector_service: EnhancedVectorService):
        """
        사용자 행동 기반 추천 서비스 초기화.
        
        Args:
            vector_service: 확장된 벡터 서비스 인스턴스
        """
        self.vector_service = vector_service
        
    async def generate_user_preference_vector(
        self, 
        behavior_data: List[Dict[str, Any]]
    ) -> Optional[List[float]]:
        """
        사용자 행동 데이터를 기반으로 사용자 선호도 벡터를 생성합니다.
        
        Args:
            behavior_data: 사용자 행동 기록 리스트
            
        Returns:
            사용자 선호도 벡터 (384차원) 또는 데이터 부족시 None
        """
        try:
            if not behavior_data:
                logger.warning("No behavior data provided for user preference vector")
                return None
                
            if not self.vector_service.is_chromadb_available():
                logger.warning("ChromaDB not available for user preference vector generation")
                return None
                
            weighted_vectors = []
            total_weight = 0
            
            for behavior in behavior_data:
                product_id = behavior.get('product_id')
                behavior_type = behavior.get('behavior_type', 'VIEW')
                
                if not product_id:
                    continue
                    
                # Get product vector from ChromaDB
                try:
                    results = self.vector_service.collection.get(
                        ids=[str(product_id)],
                        include=['embeddings']
                    )
                    
                    if results['embeddings']:
                        product_vector = np.array(results['embeddings'][0])
                        weight = self.BEHAVIOR_WEIGHTS.get(behavior_type.upper(), 1)
                        
                        weighted_vectors.append(product_vector * weight)
                        total_weight += weight
                        
                        logger.debug(f"Added product {product_id} with weight {weight} ({behavior_type})")
                        
                except Exception as e:
                    logger.warning(f"Could not get vector for product {product_id}: {e}")
                    continue
                    
            if not weighted_vectors:
                logger.warning("No valid product vectors found for user preference")
                return None
                
            # Calculate weighted average
            preference_vector = np.sum(weighted_vectors, axis=0) / total_weight
            
            logger.info(f"Generated user preference vector from {len(weighted_vectors)} products (total weight: {total_weight})")
            return preference_vector.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate user preference vector: {e}")
            return None
    
    def analyze_user_behavior_patterns(self, behavior_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        사용자 행동 패턴과 선호도를 분석합니다.
        
        Args:
            behavior_data: 사용자의 행동 이력
            
        Returns:
            행동 분석 결과
        """
        try:
            if not behavior_data:
                return {
                    'total_interactions': 0,
                    'behavior_distribution': {},
                    'total_score': 0,
                    'average_score_per_interaction': 0,
                    'most_common_behavior': None,
                    'engagement_level': 'none'
                }
            
            # Count behavior types
            behavior_counts = {}
            total_score = 0
            
            for behavior in behavior_data:
                behavior_type = behavior.get('behavior_type', 'VIEW').upper()
                behavior_counts[behavior_type] = behavior_counts.get(behavior_type, 0) + 1
                total_score += self.BEHAVIOR_WEIGHTS.get(behavior_type, 1)
            
            # Calculate statistics
            total_interactions = len(behavior_data)
            average_score = total_score / total_interactions if total_interactions > 0 else 0
            most_common_behavior = max(behavior_counts.items(), key=lambda x: x[1])[0] if behavior_counts else None
            
            # Determine engagement level
            if average_score >= 4:
                engagement_level = 'very_high'
            elif average_score >= 3:
                engagement_level = 'high'
            elif average_score >= 2:
                engagement_level = 'medium'
            elif average_score >= 1:
                engagement_level = 'low'
            else:
                engagement_level = 'none'
            
            return {
                'total_interactions': total_interactions,
                'behavior_distribution': behavior_counts,
                'total_score': total_score,
                'average_score_per_interaction': round(average_score, 2),
                'most_common_behavior': most_common_behavior,
                'engagement_level': engagement_level
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze user behavior patterns: {e}")
            return {
                'total_interactions': 0,
                'behavior_distribution': {},
                'total_score': 0,
                'average_score_per_interaction': 0,
                'most_common_behavior': None,
                'engagement_level': 'none'
            }
    
    def generate_personalized_recommendation_reason(
        self, 
        user_behavior_analysis: Dict[str, Any],
        recommended_product_metadata: Dict[str, Any],
        similarity_score: float
    ) -> str:
        """
        개인화된 추천 이유 생성.
        
        Args:
            user_behavior_analysis: 사용자 행동 분석 결과
            recommended_product_metadata: 추천 상품 메타데이터
            similarity_score: 유사도 점수
            
        Returns:
            개인화된 추천 이유
        """
        try:
            engagement_level = user_behavior_analysis.get('engagement_level', 'low')
            most_common_behavior = user_behavior_analysis.get('most_common_behavior', 'VIEW')
            
            # Base reason based on similarity score
            if similarity_score > 0.9:
                base_reason = "매우 유사한 영양성분"
            elif similarity_score > 0.8:
                base_reason = "유사한 제품 특성"
            elif similarity_score > 0.7:
                base_reason = "관련 제품"
            else:
                base_reason = "추천 제품"
            
            # Personalize based on user behavior patterns
            if engagement_level == 'very_high':
                if most_common_behavior == 'REGISTER':
                    return f"자주 등록하시는 제품과 {base_reason}"
                elif most_common_behavior == 'LIKE':
                    return f"좋아요 하신 제품과 {base_reason}"
                else:
                    return f"적극적으로 관심 보이신 제품과 {base_reason}"
                    
            elif engagement_level == 'high':
                if most_common_behavior == 'LIKE':
                    return f"선호하시는 제품과 {base_reason}"
                elif most_common_behavior == 'SEARCH':
                    return f"검색하신 제품과 {base_reason}"
                else:
                    return f"관심 있어 하신 제품과 {base_reason}"
                    
            elif engagement_level == 'medium':
                return f"이전에 본 제품과 {base_reason}"
                
            else:  # low or none
                return f"추천 {base_reason}"
                
        except Exception as e:
            logger.error(f"Failed to generate personalized recommendation reason: {e}")
            return "추천 제품"
    
    @measure_time("user_behavior_recommendations")
    async def get_recommendations(
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
            
            if not self.vector_service.is_chromadb_available():
                logger.warning("ChromaDB not available for user-based recommendations")
                return []
            
            # Analyze user behavior patterns first
            behavior_analysis = self.analyze_user_behavior_patterns(behavior_data)
            
            # Generate user preference vector
            preference_vector = await self.generate_user_preference_vector(behavior_data)
            
            if not preference_vector:
                logger.warning(f"Could not generate preference vector for user {user_id}")
                return []
                
            # Search for similar products
            recommendations = await self.vector_service.search_by_user_preferences(
                preference_vector, limit * 2  # Get more to filter out interacted products
            )
            
            # Filter out products the user has already interacted with
            interacted_products = {behavior.get('product_id') for behavior in behavior_data}
            filtered_recommendations = [
                rec for rec in recommendations 
                if rec['product_id'] not in interacted_products
            ]
            
            # Enhance recommendations with personalized reasons
            enhanced_recommendations = []
            for rec in filtered_recommendations[:limit]:
                # Get product metadata if available
                product_metadata = {}
                try:
                    results = self.vector_service.collection.get(
                        ids=[str(rec['product_id'])],
                        include=['metadatas']
                    )
                    if results['metadatas']:
                        product_metadata = results['metadatas'][0]
                except Exception as e:
                    logger.warning(f"Could not get metadata for product {rec['product_id']}: {e}")
                
                # Generate personalized reason
                personalized_reason = self.generate_personalized_recommendation_reason(
                    behavior_analysis,
                    product_metadata,
                    rec['similarity_score']
                )
                
                enhanced_rec = rec.copy()
                enhanced_rec['recommendation_reason'] = personalized_reason
                enhanced_rec['user_engagement_level'] = behavior_analysis.get('engagement_level', 'low')
                enhanced_recommendations.append(enhanced_rec)
            
            logger.info(f"Generated {len(enhanced_recommendations)} user-based recommendations for user {user_id}")
            return enhanced_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get user-based recommendations for user {user_id}: {e}")
            return []
    
    async def create_user_preference_profile(
        self, 
        user_id: int, 
        behavior_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        사용자 선호도 프로필 생성.
        
        Args:
            user_id: 사용자 식별자
            behavior_data: 사용자의 행동 이력
            
        Returns:
            사용자 선호도 프로필
        """
        try:
            logger.info(f"Creating preference profile for user {user_id}")
            
            # Analyze behavior patterns
            behavior_analysis = self.analyze_user_behavior_patterns(behavior_data)
            
            # Generate preference vector
            preference_vector = await self.generate_user_preference_vector(behavior_data)
            
            # Get product categories/types the user interacted with
            interacted_products = list({behavior.get('product_id') for behavior in behavior_data if behavior.get('product_id')})
            
            # Create profile
            profile = {
                'user_id': user_id,
                'created_at': behavior_data[-1].get('timestamp') if behavior_data else None,
                'behavior_analysis': behavior_analysis,
                'preference_vector': preference_vector,
                'interacted_products': interacted_products,
                'profile_strength': self._calculate_profile_strength(behavior_analysis, preference_vector)
            }
            
            logger.info(f"Created preference profile for user {user_id} with strength {profile['profile_strength']}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to create user preference profile for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'created_at': None,
                'behavior_analysis': {},
                'preference_vector': None,
                'interacted_products': [],
                'profile_strength': 'weak'
            }
    
    def _calculate_profile_strength(
        self, 
        behavior_analysis: Dict[str, Any], 
        preference_vector: Optional[List[float]]
    ) -> str:
        """
        사용자 선호도 프로필 강도 계산.
        
        Args:
            behavior_analysis: 행동 분석 결과
            preference_vector: 사용자 선호도 벡터
            
        Returns:
            프로필 강도: 'strong', 'medium', 'weak'
        """
        try:
            total_interactions = behavior_analysis.get('total_interactions', 0)
            engagement_level = behavior_analysis.get('engagement_level', 'none')
            has_vector = preference_vector is not None
            
            # Strong profile criteria
            if (total_interactions >= 10 and 
                engagement_level in ['high', 'very_high'] and 
                has_vector):
                return 'strong'
            
            # Medium profile criteria
            elif (total_interactions >= 5 and 
                  engagement_level in ['medium', 'high', 'very_high'] and 
                  has_vector):
                return 'medium'
            
            # Weak profile
            else:
                return 'weak'
                
        except Exception:
            return 'weak'