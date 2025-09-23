"""
Product-based recommendation service using nutrition ratios and ingredient similarity.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from decodeat.services.enhanced_vector_service import EnhancedVectorService
from decodeat.utils.logging import LoggingService
from decodeat.utils.performance import measure_time

logger = LoggingService(__name__)


class ProductBasedRecommendationService:
    """상품 기반 추천 서비스 - 영양소 구성비와 원재료 유사도 기반"""
    
    def __init__(self, vector_service: EnhancedVectorService):
        """
        상품 기반 추천 서비스 초기화.
        
        Args:
            vector_service: 확장된 벡터 서비스 인스턴스
        """
        self.vector_service = vector_service
        
    def calculate_nutrition_similarity(
        self, 
        ratios1: Dict[str, float], 
        ratios2: Dict[str, float]
    ) -> float:
        """
        영양소 구성비 유사도 계산 (코사인 유사도 사용).
        
        Args:
            ratios1: 첫 번째 상품의 영양소 구성비
            ratios2: 두 번째 상품의 영양소 구성비
            
        Returns:
            영양소 구성비 유사도 (0-1, 높을수록 유사)
        """
        try:
            # 영양소 구성비 벡터 생성
            vector1 = np.array([
                ratios1.get('carbohydrate_ratio', 0),
                ratios1.get('protein_ratio', 0),
                ratios1.get('fat_ratio', 0)
            ])
            
            vector2 = np.array([
                ratios2.get('carbohydrate_ratio', 0),
                ratios2.get('protein_ratio', 0),
                ratios2.get('fat_ratio', 0)
            ])
            
            # 영벡터 처리
            if np.linalg.norm(vector1) == 0 or np.linalg.norm(vector2) == 0:
                logger.warning("One or both nutrition vectors are zero")
                return 0.0
            
            # 코사인 유사도 계산
            similarity = cosine_similarity([vector1], [vector2])[0][0]
            
            # NaN 처리
            if np.isnan(similarity):
                logger.warning("Nutrition similarity calculation resulted in NaN")
                return 0.0
            
            # 0-1 범위로 정규화 (코사인 유사도는 -1~1 범위)
            normalized_similarity = (similarity + 1) / 2
            
            return max(0.0, min(1.0, normalized_similarity))
            
        except Exception as e:
            logger.error(f"Failed to calculate nutrition similarity: {e}")
            return 0.0
    
    def calculate_ingredient_similarity(
        self, 
        ingredients1: List[str], 
        ingredients2: List[str]
    ) -> float:
        """
        원재료 유사도 계산 (Jaccard 유사도 + 가중치).
        
        Args:
            ingredients1: 첫 번째 상품의 원재료 리스트
            ingredients2: 두 번째 상품의 원재료 리스트
            
        Returns:
            원재료 유사도 (0-1, 높을수록 유사)
        """
        try:
            if not ingredients1 or not ingredients2:
                logger.debug("One or both ingredient lists are empty")
                return 0.0
            
            # 상위 5개 원재료만 비교 (대소문자 구분 없이)
            set1 = set(ingredient.lower().strip() for ingredient in ingredients1[:5] if ingredient.strip())
            set2 = set(ingredient.lower().strip() for ingredient in ingredients2[:5] if ingredient.strip())
            
            if not set1 or not set2:
                return 0.0
            
            # 교집합과 합집합 계산
            intersection = set1 & set2
            union = set1 | set2
            
            if not union:
                return 0.0
            
            # 가중치 적용 Jaccard 유사도
            weighted_intersection = 0
            weighted_union = 0
            
            for ingredient in union:
                # 상위 3개 원재료는 가중치 2.0, 4-5번째는 1.0
                weight1 = 2.0 if ingredient in [ing.lower().strip() for ing in ingredients1[:3]] else 1.0
                weight2 = 2.0 if ingredient in [ing.lower().strip() for ing in ingredients2[:3]] else 1.0
                
                # 두 상품 모두에서의 최대 가중치 사용
                max_weight = max(weight1 if ingredient in set1 else 0, weight2 if ingredient in set2 else 0)
                weighted_union += max_weight
                
                if ingredient in intersection:
                    weighted_intersection += max_weight
            
            if weighted_union == 0:
                return 0.0
            
            similarity = weighted_intersection / weighted_union
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Failed to calculate ingredient similarity: {e}")
            return 0.0
    
    def calculate_final_score(
        self, 
        nutrition_similarity: float, 
        ingredient_similarity: float,
        nutrition_weight: float = 0.6,
        ingredient_weight: float = 0.4
    ) -> float:
        """
        최종 추천 점수 계산 (가중 평균).
        
        Args:
            nutrition_similarity: 영양소 구성비 유사도
            ingredient_similarity: 원재료 유사도
            nutrition_weight: 영양소 유사도 가중치 (기본값: 0.6)
            ingredient_weight: 원재료 유사도 가중치 (기본값: 0.4)
            
        Returns:
            최종 추천 점수 (0-1)
        """
        try:
            # 가중치 정규화
            total_weight = nutrition_weight + ingredient_weight
            if total_weight == 0:
                return 0.0
            
            normalized_nutrition_weight = nutrition_weight / total_weight
            normalized_ingredient_weight = ingredient_weight / total_weight
            
            # 가중 평균 계산
            final_score = (
                nutrition_similarity * normalized_nutrition_weight +
                ingredient_similarity * normalized_ingredient_weight
            )
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            logger.error(f"Failed to calculate final score: {e}")
            return 0.0
    
    def generate_recommendation_reason(
        self,
        nutrition_similarity: float,
        ingredient_similarity: float,
        final_score: float
    ) -> str:
        """
        추천 이유 생성.
        
        Args:
            nutrition_similarity: 영양소 구성비 유사도
            ingredient_similarity: 원재료 유사도
            final_score: 최종 추천 점수
            
        Returns:
            추천 이유 문자열
        """
        try:
            if final_score >= 0.9:
                if nutrition_similarity >= 0.8 and ingredient_similarity >= 0.8:
                    return "영양소 구성과 원재료가 매우 유사한 제품"
                elif nutrition_similarity >= 0.8:
                    return "탄단지 비율이 매우 유사한 제품"
                elif ingredient_similarity >= 0.8:
                    return "주요 원재료가 매우 유사한 제품"
                else:
                    return "매우 유사한 제품"
            elif final_score >= 0.8:
                if nutrition_similarity > ingredient_similarity:
                    return "영양소 구성이 유사한 제품"
                else:
                    return "주요 원재료가 비슷한 제품"
            elif final_score >= 0.7:
                if nutrition_similarity >= 0.7:
                    return "탄단지 비율이 비슷한 제품"
                elif ingredient_similarity >= 0.7:
                    return "원재료가 유사한 제품"
                else:
                    return "관련 제품"
            elif final_score >= 0.6:
                return "유사한 특성을 가진 제품"
            else:
                return "관련 제품"
                
        except Exception as e:
            logger.error(f"Failed to generate recommendation reason: {e}")
            return "추천 제품"
    
    @measure_time("product_based_recommendations")
    async def get_recommendations(
        self, 
        product_id: int, 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        상품 기반 추천 생성 (영양소 구성비 + 원재료 유사도).
        
        Args:
            product_id: 기준 상품 ID
            limit: 최대 추천 개수
            
        Returns:
            추천 상품 리스트
        """
        try:
            logger.info(f"Generating product-based recommendations for product {product_id}")
            
            if not self.vector_service.is_chromadb_available():
                logger.warning("ChromaDB not available for product-based recommendations")
                return []
            
            # 기준 상품 정보 조회
            reference_product = await self.vector_service.get_product_by_id(product_id)
            if not reference_product:
                logger.warning(f"Reference product {product_id} not found")
                return []
            
            reference_ratios = reference_product['nutrition_ratios']
            reference_ingredients = reference_product['main_ingredients']
            
            # 모든 상품과 비교하여 유사도 계산
            collection_info = await self.vector_service.get_collection_info()
            if collection_info.get('count', 0) <= 1:
                logger.warning("Not enough products in database for recommendations")
                return []
            
            # 전체 상품 조회 (배치 처리)
            try:
                all_products = self.vector_service.collection.get(
                    include=['metadatas'],
                    limit=min(1000, collection_info['count'])  # 최대 1000개까지
                )
            except Exception as e:
                logger.error(f"Failed to get products from ChromaDB: {e}")
                return []
            
            recommendations = []
            
            for metadata in all_products['metadatas']:
                try:
                    candidate_id = metadata.get('product_id')
                    
                    # 자기 자신 제외
                    if candidate_id == product_id:
                        continue
                    
                    # 후보 상품의 영양소 구성비와 원재료
                    candidate_ratios = {
                        'carbohydrate_ratio': metadata.get('carbohydrate_ratio', 0),
                        'protein_ratio': metadata.get('protein_ratio', 0),
                        'fat_ratio': metadata.get('fat_ratio', 0),
                        'total_calories': metadata.get('total_calories', 0)
                    }
                    
                    candidate_ingredients = metadata.get('main_ingredients', '').split(', ') if metadata.get('main_ingredients') else []
                    
                    # 유사도 계산
                    nutrition_similarity = self.calculate_nutrition_similarity(reference_ratios, candidate_ratios)
                    ingredient_similarity = self.calculate_ingredient_similarity(reference_ingredients, candidate_ingredients)
                    final_score = self.calculate_final_score(nutrition_similarity, ingredient_similarity)
                    
                    # 최소 임계값 적용 (너무 낮은 점수는 제외)
                    if final_score < 0.1:
                        continue
                    
                    # 추천 이유 생성
                    recommendation_reason = self.generate_recommendation_reason(
                        nutrition_similarity, ingredient_similarity, final_score
                    )
                    
                    recommendations.append({
                        'product_id': candidate_id,
                        'similarity_score': round(final_score, 3),
                        'nutrition_similarity': round(nutrition_similarity, 3),
                        'ingredient_similarity': round(ingredient_similarity, 3),
                        'recommendation_reason': recommendation_reason,
                        'nutrition_ratios': candidate_ratios,
                        'main_ingredients': candidate_ingredients
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to process candidate product: {e}")
                    continue
            
            # 점수순으로 정렬하고 상위 N개 반환
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            recommendations = recommendations[:limit]
            
            logger.info(f"Generated {len(recommendations)} product-based recommendations for product {product_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get product-based recommendations for product {product_id}: {e}")
            return []