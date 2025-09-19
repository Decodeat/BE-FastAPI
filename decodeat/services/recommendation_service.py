"""
개인화된 제품 추천을 생성하는 추천 서비스
"""
from typing import List, Dict, Any, Optional
import numpy as np

from decodeat.services.vector_service import VectorService
from decodeat.utils.logging import LoggingService
from decodeat.utils.performance import measure_time, recommendation_cache

logger = LoggingService(__name__)


class RecommendationService:
    """사용자 행동 기반 개인화 추천을 생성하는 서비스"""
    
    # 사용자 행동별 가중치 (요구사항에 따라 정의됨)
    BEHAVIOR_WEIGHTS = {
        'REGISTER': 5,  # 직접 등록 = 가장 강한 관심
        'LIKE': 3,      # 좋아요 = 선호
        'SEARCH': 2,    # 검색 = 관심
        'VIEW': 1       # 조회 = 기본 관심
    }
    
    def __init__(self, vector_service: VectorService):
        """
        추천 서비스를 초기화합니다.
        
        Args:
            vector_service: 유사도 검색을 위한 벡터 서비스 인스턴스
        """
        self.vector_service = vector_service
        
    async def generate_user_preference_vector(
        self, 
        behavior_data: List[Dict[str, Any]]
    ) -> Optional[List[float]]:
        """
        사용자 행동 데이터를 기반으로 사용자 선호도 벡터를 생성합니다.
        
        동작 방식:
        1. 사용자가 상호작용한 각 제품의 벡터를 ChromaDB에서 가져옴
        2. 행동 유형별 가중치를 적용 (REGISTER=5, LIKE=3, SEARCH=2, VIEW=1)
        3. 가중 평균을 계산하여 사용자의 전체적인 선호도를 나타내는 벡터 생성
        4. 이 벡터는 사용자가 좋아할 만한 제품을 찾는데 사용됨
        
        Args:
            behavior_data: 사용자 행동 기록 리스트 (제품ID, 행동유형, 시간 포함)
            
        Returns:
            사용자 선호도 벡터 (384차원) 또는 데이터 부족시 None
        """
        try:
            if not behavior_data:
                logger.warning("No behavior data provided for user preference vector")
                return None
                
            # Check if ChromaDB is available
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
            
    async def get_user_based_recommendations(
        self, 
        user_id: int,
        behavior_data: List[Dict[str, Any]], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        사용자 행동 기반 개인화 추천을 생성합니다.
        
        추천 알고리즘:
        1. 사용자 선호도 벡터 생성 (과거 행동 기반)
        2. ChromaDB에서 유사한 제품들을 벡터 검색으로 찾기
        3. 이미 상호작용한 제품들은 제외
        4. 유사도 점수와 추천 이유를 포함한 결과 반환
        
        Args:
            user_id: 사용자 식별자
            behavior_data: 사용자의 행동 이력 (좋아요, 검색, 조회 등)
            limit: 최대 추천 개수
            
        Returns:
            추천 제품 리스트 (제품ID, 유사도 점수, 추천 이유 포함)
        """
        try:
            logger.info(f"Generating user-based recommendations for user {user_id}")
            
            # Check if ChromaDB is available
            if not self.vector_service.is_chromadb_available():
                logger.warning("ChromaDB not available for user-based recommendations")
                return await self.get_fallback_recommendations(limit)
            
            # Generate user preference vector
            preference_vector = await self.generate_user_preference_vector(behavior_data)
            
            if not preference_vector:
                logger.warning(f"Could not generate preference vector for user {user_id}")
                return await self.get_fallback_recommendations(limit)
                
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
            
            # Limit to requested number
            filtered_recommendations = filtered_recommendations[:limit]
            
            logger.info(f"Generated {len(filtered_recommendations)} recommendations for user {user_id}")
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get user-based recommendations for user {user_id}: {e}")
            return await self.get_fallback_recommendations(limit)
            
    @measure_time("product_based_recommendations")
    async def get_product_based_recommendations(
        self, 
        product_id: int, 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        제품 유사도 기반 추천을 생성합니다.
        
        추천 알고리즘:
        1. 기준 제품의 벡터를 ChromaDB에서 가져옴
        2. 벡터 유사도 검색으로 비슷한 제품들을 찾음
        3. 영양성분, 원재료가 유사한 제품들이 높은 점수를 받음
        4. 유사도 점수에 따라 추천 이유를 자동 생성
        
        Args:
            product_id: 기준이 되는 제품 ID
            limit: 최대 추천 개수
            
        Returns:
            유사한 제품 리스트 (제품ID, 유사도 점수, 추천 이유 포함)
        """
        try:
            logger.info(f"Generating product-based recommendations for product {product_id}")
            
            # Check cache first
            cached_result = recommendation_cache.get(
                type="product_based",
                product_id=product_id,
                limit=limit
            )
            if cached_result:
                logger.debug(f"Using cached recommendations for product {product_id}")
                return cached_result
            
            # Check if ChromaDB is available
            if not self.vector_service.is_chromadb_available():
                logger.warning("ChromaDB not available for product-based recommendations")
                return await self.get_fallback_recommendations(limit)
            
            recommendations = await self.vector_service.find_similar_products(
                product_id, limit
            )
            
            if not recommendations:
                logger.warning(f"No similar products found for product {product_id}")
                return await self.get_fallback_recommendations(limit)
            
            # Cache the results
            recommendation_cache.set(
                recommendations,
                type="product_based",
                product_id=product_id,
                limit=limit
            )
            
            logger.info(f"Generated {len(recommendations)} similar products for product {product_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get product-based recommendations for product {product_id}: {e}")
            return await self.get_fallback_recommendations(limit)
            
    def _calculate_behavior_score(self, behavior_data: List[Dict[str, Any]]) -> float:
        """
        Calculate overall behavior score for a user.
        
        Args:
            behavior_data: User's behavior history
            
        Returns:
            Weighted behavior score
        """
        total_score = 0
        for behavior in behavior_data:
            behavior_type = behavior.get('behavior_type', 'VIEW').upper()
            weight = self.BEHAVIOR_WEIGHTS.get(behavior_type, 1)
            total_score += weight
            
        return total_score
        
    def analyze_user_behavior_patterns(self, behavior_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        사용자 행동 패턴과 선호도를 분석합니다.
        
        분석 내용:
        1. 행동 유형별 빈도 계산 (좋아요, 검색, 조회 등)
        2. 총 참여도 점수 계산 (가중치 적용)
        3. 평균 참여도와 가장 많이 하는 행동 파악
        4. 참여 수준 분류 (매우높음/높음/보통/낮음/없음)
        
        Args:
            behavior_data: 사용자의 행동 이력
            
        Returns:
            행동 분석 결과 (총 상호작용 수, 행동 분포, 참여 수준 등)
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
            
    async def create_user_preference_profile(
        self, 
        user_id: int, 
        behavior_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a comprehensive user preference profile.
        
        Args:
            user_id: User identifier
            behavior_data: User's behavior history
            
        Returns:
            User preference profile dictionary
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
        Calculate the strength of a user preference profile.
        
        Args:
            behavior_analysis: Behavior analysis results
            preference_vector: User preference vector
            
        Returns:
            Profile strength: 'strong', 'medium', 'weak'
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
        
    async def get_fallback_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        사용자 데이터가 부족할 때 대체 추천을 제공합니다.
        
        대체 추천 방식:
        1. ChromaDB에 저장된 제품들 중에서 무작위로 선택
        2. 실제 서비스에서는 인기도나 최신 제품 기준으로 개선 가능
        3. 모든 추천에 중립적인 점수(0.5)와 "인기 제품" 라벨 부여
        
        Args:
            limit: 최대 추천 개수
            
        Returns:
            대체 추천 제품 리스트
        """
        try:
            logger.info("Generating fallback recommendations")
            
            # Try to get some random products from ChromaDB if available
            if self.vector_service.is_chromadb_available():
                try:
                    # Get collection info to see if we have any data
                    collection_info = await self.vector_service.get_collection_info()
                    
                    if collection_info.get('count', 0) > 0:
                        # Get some random products (simplified fallback)
                        results = self.vector_service.collection.get(
                            limit=min(limit, collection_info['count']),
                            include=['metadatas']
                        )
                        
                        fallback_recommendations = []
                        for metadata in results['metadatas']:
                            fallback_recommendations.append({
                                'product_id': metadata['product_id'],
                                'similarity_score': 0.5,  # Neutral score for fallback
                                'recommendation_reason': '인기 제품'
                            })
                        
                        logger.info(f"Generated {len(fallback_recommendations)} fallback recommendations")
                        return fallback_recommendations
                        
                except Exception as e:
                    logger.warning(f"Failed to get fallback from ChromaDB: {e}")
            
            # If ChromaDB is not available or has no data, return empty list
            logger.warning("No fallback recommendations available - ChromaDB empty or unavailable")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get fallback recommendations: {e}")
            return []
            
    def evaluate_recommendation_quality(
        self, 
        recommendations: List[Dict[str, Any]], 
        user_behavior_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        추천 품질을 평가합니다.
        
        평가 기준:
        1. 추천 개수 (많을수록 좋음)
        2. 평균 유사도 점수 (높을수록 좋음)
        3. 사용자 참여도 (높을수록 좋음)
        4. 사용자 상호작용 횟수 (많을수록 좋음)
        
        품질 등급:
        - excellent: 높은 유사도 + 많은 추천 + 높은 사용자 참여도
        - good: 적당한 유사도 + 충분한 추천 + 보통 사용자 참여도
        - fair: 낮은 유사도 또는 적은 추천
        - poor: 매우 낮은 품질 또는 추천 없음
        
        Args:
            recommendations: 추천 결과 리스트
            user_behavior_analysis: 사용자 행동 분석 결과 (선택사항)
            
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
            
    async def get_popularity_based_fallback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popularity-based fallback recommendations.
        
        Args:
            limit: Maximum number of recommendations
            
        Returns:
            List of popular products as fallback recommendations
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
            # In a real implementation, this would query actual popularity metrics
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
            
    def generate_personalized_recommendation_reason(
        self, 
        user_behavior_analysis: Dict[str, Any],
        recommended_product_metadata: Dict[str, Any],
        similarity_score: float
    ) -> str:
        """
        Generate personalized recommendation reason based on user behavior patterns.
        
        Args:
            user_behavior_analysis: User's behavior analysis results
            recommended_product_metadata: Metadata of recommended product
            similarity_score: Similarity score between user preference and product
            
        Returns:
            Personalized recommendation reason
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
            
    @measure_time("enhanced_user_based_recommendations")
    async def get_enhanced_user_based_recommendations(
        self, 
        user_id: int,
        behavior_data: List[Dict[str, Any]], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get enhanced user-based recommendations with personalized reasons.
        
        Args:
            user_id: User identifier
            behavior_data: User's behavior history
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended products with personalized reasons
        """
        try:
            logger.info(f"Generating enhanced user-based recommendations for user {user_id}")
            
            # Analyze user behavior patterns first
            behavior_analysis = self.analyze_user_behavior_patterns(behavior_data)
            
            # Get basic recommendations
            recommendations = await self.get_user_based_recommendations(
                user_id, behavior_data, limit
            )
            
            # Enhance recommendations with personalized reasons
            enhanced_recommendations = []
            for rec in recommendations:
                # Get product metadata if available
                product_metadata = {}
                if self.vector_service.is_chromadb_available():
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
            
            logger.info(f"Enhanced {len(enhanced_recommendations)} recommendations for user {user_id}")
            return enhanced_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get enhanced user-based recommendations for user {user_id}: {e}")
            return await self.get_user_based_recommendations(user_id, behavior_data, limit)