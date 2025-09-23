"""
Enhanced vector service with product_id key storage and nutrition ratio calculations.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

from decodeat.services.vector_service import VectorService
from decodeat.utils.logging import LoggingService
from decodeat.utils.model_cache import model_cache

logger = LoggingService(__name__)


class NutritionDataError(Exception):
    """영양소 데이터가 부족할 때 발생하는 예외"""
    pass


class IngredientDataError(Exception):
    """원재료 데이터가 부족할 때 발생하는 예외"""
    pass


class EnhancedVectorService(VectorService):
    """Enhanced vector service with nutrition ratios and ingredient analysis."""
    
    # 영양소별 칼로리 변환 상수
    NUTRITION_CALORIES = {
        'carbohydrate': 4,  # 탄수화물: 1g = 4kcal
        'protein': 4,       # 단백질: 1g = 4kcal
        'fat': 9           # 지방: 1g = 9kcal
    }
    
    def calculate_nutrition_ratios(self, nutrition_info: Dict[str, Any]) -> Dict[str, float]:
        """
        영양소 구성비 계산 (탄단지 비율).
        
        Args:
            nutrition_info: 영양소 정보 딕셔너리
            
        Returns:
            영양소 구성비 딕셔너리 (탄수화물, 단백질, 지방 비율)
            
        Raises:
            NutritionDataError: 필수 영양소 데이터가 부족할 때
        """
        try:
            if not nutrition_info:
                logger.warning("No nutrition info provided")
                return {'carbohydrate_ratio': 0, 'protein_ratio': 0, 'fat_ratio': 0, 'total_calories': 0}
            
            # 영양소 값 추출 및 검증
            try:
                carbohydrate = float(nutrition_info.get('carbohydrate', 0))
                protein = float(nutrition_info.get('protein', 0))
                fat = float(nutrition_info.get('fat', 0))
                total_calories = float(nutrition_info.get('energy', 0))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid nutrition data format: {e}")
                return {'carbohydrate_ratio': 0, 'protein_ratio': 0, 'fat_ratio': 0, 'total_calories': 0}
            
            # 음수 값 처리
            carbohydrate = max(0, carbohydrate)
            protein = max(0, protein)
            fat = max(0, fat)
            total_calories = max(0, total_calories)
            
            # 각 영양소별 칼로리 계산
            carb_calories = carbohydrate * self.NUTRITION_CALORIES['carbohydrate']
            protein_calories = protein * self.NUTRITION_CALORIES['protein']
            fat_calories = fat * self.NUTRITION_CALORIES['fat']
            
            # 계산된 총 칼로리
            calculated_calories = carb_calories + protein_calories + fat_calories
            
            # 총 칼로리가 0이거나 계산된 칼로리와 차이가 클 때 처리
            if total_calories == 0:
                if calculated_calories > 0:
                    total_calories = calculated_calories
                    logger.info(f"Using calculated calories: {calculated_calories}")
                else:
                    logger.warning("No calorie information available")
                    return {'carbohydrate_ratio': 0, 'protein_ratio': 0, 'fat_ratio': 0, 'total_calories': 0}
            
            # 비율 계산
            carbohydrate_ratio = (carb_calories / total_calories) * 100
            protein_ratio = (protein_calories / total_calories) * 100
            fat_ratio = (fat_calories / total_calories) * 100
            
            # 비율 합이 100%를 초과하지 않도록 정규화
            total_ratio = carbohydrate_ratio + protein_ratio + fat_ratio
            if total_ratio > 100:
                carbohydrate_ratio = (carbohydrate_ratio / total_ratio) * 100
                protein_ratio = (protein_ratio / total_ratio) * 100
                fat_ratio = (fat_ratio / total_ratio) * 100
            
            result = {
                'carbohydrate_ratio': round(carbohydrate_ratio, 2),
                'protein_ratio': round(protein_ratio, 2),
                'fat_ratio': round(fat_ratio, 2),
                'total_calories': total_calories
            }
            
            logger.debug(f"Calculated nutrition ratios: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate nutrition ratios: {e}")
            return {'carbohydrate_ratio': 0, 'protein_ratio': 0, 'fat_ratio': 0, 'total_calories': 0}
    
    def extract_main_ingredients(self, ingredients: List[str], max_count: int = 5) -> List[str]:
        """
        주요 원재료 추출 및 정제.
        
        Args:
            ingredients: 원재료 리스트
            max_count: 최대 추출할 원재료 개수
            
        Returns:
            정제된 주요 원재료 리스트
        """
        try:
            if not ingredients:
                logger.warning("No ingredients provided")
                return []
            
            # 원재료 정제
            cleaned_ingredients = []
            seen_ingredients = set()
            
            for ingredient in ingredients:
                if not ingredient or not isinstance(ingredient, str):
                    continue
                    
                # 공백 제거 및 소문자 변환으로 중복 체크
                cleaned = ingredient.strip()
                if not cleaned:
                    continue
                    
                # 중복 제거 (대소문자 구분 없이)
                ingredient_lower = cleaned.lower()
                if ingredient_lower not in seen_ingredients:
                    cleaned_ingredients.append(cleaned)
                    seen_ingredients.add(ingredient_lower)
                    
                    # 최대 개수 도달 시 중단
                    if len(cleaned_ingredients) >= max_count:
                        break
            
            logger.debug(f"Extracted {len(cleaned_ingredients)} main ingredients from {len(ingredients)} total")
            return cleaned_ingredients
            
        except Exception as e:
            logger.error(f"Failed to extract main ingredients: {e}")
            return []
    
    async def store_product_with_id(
        self, 
        product_id: int, 
        product_data: Dict[str, Any]
    ) -> bool:
        """
        product_id를 키로 하여 상품 정보를 벡터 데이터베이스에 저장.
        
        Args:
            product_id: 외부 DB의 상품 PK
            product_data: 상품 정보 (상품명, 영양성분, 원재료 포함)
            
        Returns:
            저장 성공 여부
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for store operation")
            return False
            
        try:
            # 기존 데이터가 있으면 삭제 (업데이트를 위해)
            try:
                existing = self.collection.get(ids=[str(product_id)])
                if existing['ids']:
                    await self.delete_product_vector(product_id)
                    logger.info(f"Updated existing product {product_id}")
            except Exception:
                # 기존 데이터가 없는 경우는 정상
                pass
            
            # 벡터 생성
            vector = await self.generate_product_vector(product_data)
            
            # 영양소 구성비 계산
            nutrition_ratios = {}
            if product_data.get('nutrition_info'):
                nutrition_ratios = self.calculate_nutrition_ratios(product_data['nutrition_info'])
            
            # 주요 원재료 추출
            main_ingredients = []
            if product_data.get('ingredients'):
                main_ingredients = self.extract_main_ingredients(product_data['ingredients'])
            
            # 메타데이터 준비
            current_time = datetime.now().isoformat()
            metadata = {
                "product_id": product_id,
                "product_name": product_data.get('product_name', ''),
                "carbohydrate_ratio": nutrition_ratios.get('carbohydrate_ratio', 0),
                "protein_ratio": nutrition_ratios.get('protein_ratio', 0),
                "fat_ratio": nutrition_ratios.get('fat_ratio', 0),
                "total_calories": nutrition_ratios.get('total_calories', 0),
                "main_ingredients": ', '.join(main_ingredients) if main_ingredients else '',
                "ingredient_count": len(main_ingredients),
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # 기존 영양성분 정보도 메타데이터에 포함 (호환성을 위해)
            if product_data.get('nutrition_info'):
                nutrition = product_data['nutrition_info']
                for key in ['energy', 'protein', 'fat', 'carbohydrate', 'sodium']:
                    if nutrition.get(key):
                        try:
                            metadata[key] = float(nutrition[key])
                        except (ValueError, TypeError):
                            pass
            
            # ChromaDB에 저장
            self.collection.add(
                embeddings=[vector],
                metadatas=[metadata],
                ids=[str(product_id)]
            )
            
            logger.info(f"Stored product {product_id} with nutrition ratios and ingredients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store product {product_id}: {e}")
            return False
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        product_id로 상품 정보 조회.
        
        Args:
            product_id: 조회할 상품 ID
            
        Returns:
            상품 정보 딕셔너리 또는 None
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for get operation")
            return None
            
        try:
            results = self.collection.get(
                ids=[str(product_id)],
                include=['embeddings', 'metadatas']
            )
            
            if not results['ids']:
                logger.warning(f"Product {product_id} not found")
                return None
            
            metadata = results['metadatas'][0]
            embedding = results['embeddings'][0] if results['embeddings'] else None
            
            return {
                'product_id': metadata.get('product_id'),
                'product_name': metadata.get('product_name', ''),
                'nutrition_ratios': {
                    'carbohydrate_ratio': metadata.get('carbohydrate_ratio', 0),
                    'protein_ratio': metadata.get('protein_ratio', 0),
                    'fat_ratio': metadata.get('fat_ratio', 0),
                    'total_calories': metadata.get('total_calories', 0)
                },
                'main_ingredients': metadata.get('main_ingredients', '').split(', ') if metadata.get('main_ingredients') else [],
                'embedding': embedding,
                'created_at': metadata.get('created_at'),
                'updated_at': metadata.get('updated_at')
            }
            
        except Exception as e:
            logger.error(f"Failed to get product {product_id}: {e}")
            return None