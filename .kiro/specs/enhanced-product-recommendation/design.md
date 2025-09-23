# Design Document

## Overview

이 설계는 현재 추천 시스템을 개선하여 다음 세 가지 주요 목표를 달성합니다:

1. **벡터 데이터베이스 개선**: product_id를 키로 하는 효율적인 상품 정보 저장
2. **상품 기반 추천 알고리즘 개선**: 영양소 구성비(탄단지 비율)와 원재료 유사도 기반 추천
3. **코드 구조 개선**: 상품 기반 추천과 사용자 행동 기반 추천 서비스 분리

## Architecture

### 현재 구조 vs 개선된 구조

**현재 구조:**
```
RecommendationService (단일 서비스)
├── 사용자 행동 기반 추천
├── 상품 기반 추천 (기본 벡터 유사도)
└── VectorService (기본 텍스트 임베딩)
```

**개선된 구조:**
```
RecommendationService (통합 인터페이스)
├── ProductBasedRecommendationService
│   ├── 영양소 구성비 계산기
│   ├── 원재료 유사도 계산기
│   └── 가중 점수 계산기
├── UserBehaviorRecommendationService
│   ├── 사용자 선호도 벡터 생성
│   └── 개인화 추천 생성
└── EnhancedVectorService
    ├── product_id 키 기반 저장
    ├── 영양소 구성비 메타데이터
    └── 원재료 정보 메타데이터
```

## Components and Interfaces

### 1. EnhancedVectorService

기존 VectorService를 확장하여 product_id 키 기반 저장과 영양소/원재료 메타데이터를 지원합니다.

```python
class EnhancedVectorService(VectorService):
    async def store_product_with_id(
        self, 
        product_id: int, 
        product_data: Dict[str, Any]
    ) -> bool:
        """product_id를 키로 상품 정보 저장"""
        
    def calculate_nutrition_ratios(
        self, 
        nutrition_info: Dict[str, Any]
    ) -> Dict[str, float]:
        """탄단지 비율 계산"""
        
    def extract_main_ingredients(
        self, 
        ingredients: List[str], 
        max_count: int = 5
    ) -> List[str]:
        """주요 원재료 추출"""
```

### 2. ProductBasedRecommendationService

영양소 구성비와 원재료 유사도를 기반으로 한 상품 추천 서비스입니다.

```python
class ProductBasedRecommendationService:
    def __init__(self, vector_service: EnhancedVectorService):
        self.vector_service = vector_service
        
    async def get_recommendations(
        self, 
        product_id: int, 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """영양소 구성비와 원재료 유사도 기반 추천"""
        
    def calculate_nutrition_similarity(
        self, 
        product1_ratios: Dict[str, float], 
        product2_ratios: Dict[str, float]
    ) -> float:
        """영양소 구성비 유사도 계산 (0-1)"""
        
    def calculate_ingredient_similarity(
        self, 
        ingredients1: List[str], 
        ingredients2: List[str]
    ) -> float:
        """원재료 유사도 계산 (0-1)"""
        
    def calculate_final_score(
        self, 
        nutrition_similarity: float, 
        ingredient_similarity: float,
        nutrition_weight: float = 0.6,
        ingredient_weight: float = 0.4
    ) -> float:
        """최종 추천 점수 계산"""
```

### 3. UserBehaviorRecommendationService

사용자 행동 기반 개인화 추천 서비스입니다.

```python
class UserBehaviorRecommendationService:
    def __init__(self, vector_service: EnhancedVectorService):
        self.vector_service = vector_service
        
    async def get_recommendations(
        self, 
        user_id: int,
        behavior_data: List[Dict[str, Any]], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """사용자 행동 기반 추천"""
        
    async def generate_user_preference_vector(
        self, 
        behavior_data: List[Dict[str, Any]]
    ) -> Optional[List[float]]:
        """사용자 선호도 벡터 생성"""
```

### 4. 통합 RecommendationService

기존 API 호환성을 유지하면서 새로운 서비스들을 통합하는 인터페이스입니다.

```python
class RecommendationService:
    def __init__(self, vector_service: EnhancedVectorService):
        self.product_service = ProductBasedRecommendationService(vector_service)
        self.user_service = UserBehaviorRecommendationService(vector_service)
        
    async def get_product_based_recommendations(
        self, 
        product_id: int, 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """상품 기반 추천 (새로운 알고리즘 사용)"""
        return await self.product_service.get_recommendations(product_id, limit)
        
    async def get_user_based_recommendations(
        self, 
        user_id: int,
        behavior_data: List[Dict[str, Any]], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """사용자 행동 기반 추천"""
        return await self.user_service.get_recommendations(user_id, behavior_data, limit)
```

## Data Models

### 1. 영양소 구성비 모델

```python
class NutritionRatios(BaseModel):
    """영양소 구성비 (탄단지 비율)"""
    carbohydrate_ratio: float = Field(..., description="탄수화물 비율 (%)")
    protein_ratio: float = Field(..., description="단백질 비율 (%)")
    fat_ratio: float = Field(..., description="지방 비율 (%)")
    total_calories: float = Field(..., description="총 칼로리 (kcal)")
    
    @validator('*')
    def validate_ratios(cls, v):
        return max(0.0, min(100.0, v))
```

### 2. 상품 메타데이터 모델

```python
class ProductMetadata(BaseModel):
    """벡터 데이터베이스에 저장될 상품 메타데이터"""
    product_id: int
    product_name: str
    nutrition_ratios: Optional[NutritionRatios]
    main_ingredients: List[str]
    total_calories: Optional[float]
    created_at: datetime
    updated_at: datetime
```

### 3. 추천 결과 확장 모델

```python
class EnhancedRecommendationResult(RecommendationResult):
    """확장된 추천 결과"""
    nutrition_similarity: Optional[float] = Field(None, description="영양소 유사도 (0-1)")
    ingredient_similarity: Optional[float] = Field(None, description="원재료 유사도 (0-1)")
    nutrition_ratios: Optional[NutritionRatios] = Field(None, description="추천 상품의 영양소 구성비")
    main_ingredients: Optional[List[str]] = Field(None, description="추천 상품의 주요 원재료")
```

## Error Handling

### 1. 영양소 데이터 부족 처리

```python
class NutritionDataError(Exception):
    """영양소 데이터가 부족할 때 발생하는 예외"""
    pass

# 처리 방식:
# 1. 필수 영양소 (칼로리, 탄수화물, 단백질, 지방) 중 하나라도 없으면 기본 벡터 유사도 사용
# 2. 부분적 데이터가 있으면 가능한 범위에서 유사도 계산
# 3. 로그에 데이터 부족 상황 기록
```

### 2. 원재료 데이터 부족 처리

```python
class IngredientDataError(Exception):
    """원재료 데이터가 부족할 때 발생하는 예외"""
    pass

# 처리 방식:
# 1. 원재료 정보가 없으면 영양소 유사도만 사용 (가중치 100%)
# 2. 원재료가 1-2개만 있으면 부분 유사도 계산
# 3. 원재료 정보 품질에 따라 가중치 동적 조정
```

### 3. 벡터 저장 실패 처리

```python
# 처리 방식:
# 1. ChromaDB 연결 실패 시 로컬 캐시에 임시 저장
# 2. 재연결 시 캐시된 데이터 일괄 업로드
# 3. 추천 요청 시 벡터 DB 사용 불가능하면 fallback 메커니즘 사용
```

## Testing Strategy

### 1. 단위 테스트

```python
# 영양소 구성비 계산 테스트
def test_calculate_nutrition_ratios():
    nutrition_info = {
        'energy': '200',
        'carbohydrate': '30',
        'protein': '10', 
        'fat': '5'
    }
    ratios = calculate_nutrition_ratios(nutrition_info)
    assert ratios['carbohydrate_ratio'] == 60.0  # (30*4/200)*100
    assert ratios['protein_ratio'] == 20.0       # (10*4/200)*100
    assert ratios['fat_ratio'] == 22.5           # (5*9/200)*100

# 원재료 유사도 계산 테스트
def test_calculate_ingredient_similarity():
    ingredients1 = ['밀가루', '설탕', '버터', '계란', '우유']
    ingredients2 = ['밀가루', '설탕', '식물성유지', '계란', '소금']
    similarity = calculate_ingredient_similarity(ingredients1, ingredients2)
    assert 0.4 <= similarity <= 0.8  # 3/5 공통 원재료

# product_id 키 저장 테스트
async def test_store_product_with_id():
    product_data = {
        'product_name': '테스트 제품',
        'nutrition_info': {...},
        'ingredients': [...]
    }
    result = await vector_service.store_product_with_id(12345, product_data)
    assert result == True
    
    # 조회 테스트
    stored_data = await vector_service.get_product_by_id(12345)
    assert stored_data['product_id'] == 12345
```

### 2. 통합 테스트

```python
# 전체 추천 플로우 테스트
async def test_enhanced_product_recommendation_flow():
    # 1. 상품 데이터 저장
    await store_test_products()
    
    # 2. 상품 기반 추천 요청
    recommendations = await product_service.get_recommendations(
        product_id=1001, 
        limit=10
    )
    
    # 3. 결과 검증
    assert len(recommendations) > 0
    assert all('nutrition_similarity' in rec for rec in recommendations)
    assert all('ingredient_similarity' in rec for rec in recommendations)
    assert all(0 <= rec['similarity_score'] <= 1 for rec in recommendations)

# API 호환성 테스트
async def test_api_compatibility():
    # 기존 API 형식으로 요청
    request = ProductBasedRecommendationRequest(
        product_id=1001,
        limit=15
    )
    
    response = await get_product_based_recommendations(request, vector_service)
    
    # 기존 응답 형식 유지 확인
    assert isinstance(response, RecommendationResponse)
    assert hasattr(response, 'recommendations')
    assert hasattr(response, 'total_count')
```

### 3. 성능 테스트

```python
# 영양소 구성비 계산 성능 테스트
@measure_time("nutrition_ratio_calculation")
def test_nutrition_ratio_performance():
    # 1000개 상품의 영양소 구성비 계산 시간 측정
    for i in range(1000):
        calculate_nutrition_ratios(sample_nutrition_data)

# 대용량 추천 성능 테스트
async def test_large_scale_recommendation_performance():
    # 10000개 상품 중에서 유사 상품 찾기
    start_time = time.time()
    recommendations = await product_service.get_recommendations(
        product_id=1001, 
        limit=50
    )
    end_time = time.time()
    
    assert (end_time - start_time) < 2.0  # 2초 이내 응답
    assert len(recommendations) == 50
```

### 4. 데이터 품질 테스트

```python
# 영양소 데이터 품질 검증
def test_nutrition_data_quality():
    # 잘못된 영양소 데이터 처리
    invalid_nutrition = {
        'energy': 'invalid',
        'protein': '-10',
        'fat': '1000'
    }
    
    ratios = calculate_nutrition_ratios(invalid_nutrition)
    assert ratios is not None  # 오류 상황에서도 기본값 반환
    
# 원재료 데이터 품질 검증
def test_ingredient_data_quality():
    # 빈 원재료 리스트 처리
    empty_ingredients = []
    similarity = calculate_ingredient_similarity(empty_ingredients, ['밀가루'])
    assert similarity == 0.0
    
    # 중복 원재료 처리
    duplicate_ingredients = ['밀가루', '밀가루', '설탕']
    cleaned = extract_main_ingredients(duplicate_ingredients)
    assert len(cleaned) == 2  # 중복 제거됨
```

## Implementation Notes

### 1. 영양소 구성비 계산 공식

```python
# 칼로리 기반 영양소 비율 계산
def calculate_nutrition_ratios(nutrition_info: Dict[str, Any]) -> Dict[str, float]:
    """
    영양소별 칼로리 기여도 계산:
    - 탄수화물: 1g = 4kcal
    - 단백질: 1g = 4kcal  
    - 지방: 1g = 9kcal
    """
    carb_calories = float(nutrition_info.get('carbohydrate', 0)) * 4
    protein_calories = float(nutrition_info.get('protein', 0)) * 4
    fat_calories = float(nutrition_info.get('fat', 0)) * 9
    
    total_calories = float(nutrition_info.get('energy', 0))
    
    if total_calories == 0:
        return {'carbohydrate_ratio': 0, 'protein_ratio': 0, 'fat_ratio': 0}
    
    return {
        'carbohydrate_ratio': (carb_calories / total_calories) * 100,
        'protein_ratio': (protein_calories / total_calories) * 100,
        'fat_ratio': (fat_calories / total_calories) * 100
    }
```

### 2. 원재료 유사도 계산 방식

```python
def calculate_ingredient_similarity(ingredients1: List[str], ingredients2: List[str]) -> float:
    """
    Jaccard 유사도 기반 원재료 유사도 계산:
    similarity = |A ∩ B| / |A ∪ B|
    
    가중치 적용:
    - 상위 3개 원재료: 가중치 2.0
    - 4-5번째 원재료: 가중치 1.0
    """
    set1 = set(ingredients1[:5])  # 상위 5개만 비교
    set2 = set(ingredients2[:5])
    
    intersection = set1 & set2
    union = set1 | set2
    
    if not union:
        return 0.0
    
    # 가중치 적용
    weighted_intersection = 0
    weighted_union = 0
    
    for ingredient in union:
        weight = 2.0 if (ingredients1.index(ingredient) < 3 if ingredient in ingredients1 else False) or \
                       (ingredients2.index(ingredient) < 3 if ingredient in ingredients2 else False) else 1.0
        
        weighted_union += weight
        if ingredient in intersection:
            weighted_intersection += weight
    
    return weighted_intersection / weighted_union
```

### 3. 벡터 데이터베이스 스키마

```python
# ChromaDB 컬렉션 메타데이터 스키마
metadata_schema = {
    "product_id": int,           # 외부 DB PK
    "product_name": str,         # 상품명
    "carbohydrate_ratio": float, # 탄수화물 비율 (%)
    "protein_ratio": float,      # 단백질 비율 (%)
    "fat_ratio": float,          # 지방 비율 (%)
    "total_calories": float,     # 총 칼로리
    "main_ingredients": str,     # 주요 원재료 (쉼표 구분)
    "ingredient_count": int,     # 원재료 개수
    "created_at": str,          # 생성 시간 (ISO format)
    "updated_at": str           # 수정 시간 (ISO format)
}
```

이 설계를 통해 기존 API 호환성을 유지하면서도 더 정확하고 설명 가능한 추천 시스템을 구축할 수 있습니다.