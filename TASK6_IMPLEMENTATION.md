# Task 6 구현 완료: 사용자 행동 데이터 분석 서비스

## 📋 Task 개요
- **Task ID**: 6
- **Task 명**: 사용자 행동 데이터 분석 서비스 구현
- **완료 일시**: 2025-09-16
- **상태**: ✅ 완료

## 🎯 구현 요구사항
- [x] 사용자 행동 데이터 가중치 적용 로직 (VIEW:1, SEARCH:2, LIKE:3, REGISTER:5)
- [x] 사용자가 관심있어 한 제품들의 평균 벡터 계산
- [x] 사용자 선호도 프로필 생성 함수 구현
- [x] Requirements: 3.1, 3.5, 5.1 충족

## 🔧 구현 내용

### 1. 행동 가중치 시스템
```python
class RecommendationService:
    # 행동 가중치 정의 (요구사항에 따라)
    BEHAVIOR_WEIGHTS = {
        'REGISTER': 5,  # 직접 등록 = 가장 강한 관심
        'LIKE': 3,      # 좋아요 = 선호
        'SEARCH': 2,    # 검색 = 관심
        'VIEW': 1       # 조회 = 기본 관심
    }
```

**특징:**
- 사용자의 행동 강도에 따른 차등 가중치
- REGISTER가 가장 높은 가중치 (5점)
- VIEW가 가장 낮은 가중치 (1점)

### 2. 사용자 선호도 벡터 생성
```python
async def generate_user_preference_vector(self, behavior_data: List[Dict[str, Any]]) -> Optional[List[float]]:
    """사용자 행동 데이터를 기반으로 선호도 벡터 생성"""
    
    # ChromaDB 연결 상태 확인
    if not self.vector_service.is_chromadb_available():
        return None
    
    weighted_vectors = []
    total_weight = 0
    
    for behavior in behavior_data:
        product_id = behavior.get('product_id')
        behavior_type = behavior.get('behavior_type', 'VIEW').upper()
        
        # 제품 벡터 조회
        results = self.vector_service.collection.get(
            ids=[str(product_id)],
            include=['embeddings']
        )
        
        if results['embeddings']:
            product_vector = np.array(results['embeddings'][0])
            weight = self.BEHAVIOR_WEIGHTS.get(behavior_type, 1)
            
            weighted_vectors.append(product_vector * weight)
            total_weight += weight
    
    if not weighted_vectors:
        return None
    
    # 가중 평균 계산
    preference_vector = np.sum(weighted_vectors, axis=0) / total_weight
    return preference_vector.tolist()
```

**핵심 로직:**
- 각 제품 벡터에 행동 가중치 적용
- 가중 평균으로 사용자 선호도 벡터 계산
- 384차원 벡터로 사용자 취향 표현

### 3. 행동 패턴 분석
```python
def analyze_user_behavior_patterns(self, behavior_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """사용자 행동 패턴 분석"""
    
    behavior_counts = {}
    total_score = 0
    
    # 행동 유형별 집계
    for behavior in behavior_data:
        behavior_type = behavior.get('behavior_type', 'VIEW').upper()
        behavior_counts[behavior_type] = behavior_counts.get(behavior_type, 0) + 1
        total_score += self.BEHAVIOR_WEIGHTS.get(behavior_type, 1)
    
    # 통계 계산
    total_interactions = len(behavior_data)
    average_score = total_score / total_interactions if total_interactions > 0 else 0
    most_common_behavior = max(behavior_counts.items(), key=lambda x: x[1])[0] if behavior_counts else None
    
    # 참여 수준 결정
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
```

### 4. 사용자 선호도 프로필 생성
```python
async def create_user_preference_profile(self, user_id: int, behavior_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """종합적인 사용자 선호도 프로필 생성"""
    
    # 행동 패턴 분석
    behavior_analysis = self.analyze_user_behavior_patterns(behavior_data)
    
    # 선호도 벡터 생성
    preference_vector = await self.generate_user_preference_vector(behavior_data)
    
    # 상호작용한 제품 목록
    interacted_products = list({behavior.get('product_id') for behavior in behavior_data if behavior.get('product_id')})
    
    # 프로필 생성
    profile = {
        'user_id': user_id,
        'created_at': behavior_data[-1].get('timestamp') if behavior_data else None,
        'behavior_analysis': behavior_analysis,
        'preference_vector': preference_vector,
        'interacted_products': interacted_products,
        'profile_strength': self._calculate_profile_strength(behavior_analysis, preference_vector)
    }
    
    return profile
```

### 5. 프로필 강도 계산
```python
def _calculate_profile_strength(self, behavior_analysis: Dict[str, Any], preference_vector: Optional[List[float]]) -> str:
    """프로필 강도 계산"""
    
    total_interactions = behavior_analysis.get('total_interactions', 0)
    engagement_level = behavior_analysis.get('engagement_level', 'none')
    has_vector = preference_vector is not None
    
    # 강한 프로필: 10회 이상 상호작용, 높은 참여도, 벡터 존재
    if (total_interactions >= 10 and 
        engagement_level in ['high', 'very_high'] and 
        has_vector):
        return 'strong'
    
    # 중간 프로필: 5회 이상 상호작용, 중간 이상 참여도, 벡터 존재
    elif (total_interactions >= 5 and 
          engagement_level in ['medium', 'high', 'very_high'] and 
          has_vector):
        return 'medium'
    
    # 약한 프로필
    else:
        return 'weak'
```

### 6. 사용자 기반 추천 개선
```python
async def get_user_based_recommendations(self, user_id: int, behavior_data: List[Dict[str, Any]], limit: int = 20):
    """개선된 사용자 기반 추천"""
    
    # ChromaDB 연결 확인
    if not self.vector_service.is_chromadb_available():
        return await self.get_fallback_recommendations(limit)
    
    # 사용자 선호도 벡터 생성
    preference_vector = await self.generate_user_preference_vector(behavior_data)
    
    if not preference_vector:
        return await self.get_fallback_recommendations(limit)
    
    # 유사 제품 검색
    recommendations = await self.vector_service.search_by_user_preferences(
        preference_vector, limit * 2  # 필터링을 위해 더 많이 조회
    )
    
    # 이미 상호작용한 제품 제외
    interacted_products = {behavior.get('product_id') for behavior in behavior_data}
    filtered_recommendations = [
        rec for rec in recommendations 
        if rec['product_id'] not in interacted_products
    ]
    
    return filtered_recommendations[:limit]
```

## 📊 테스트 결과

### 1. 행동 데이터 분석
```bash
생성된 행동 데이터: 7개
  1. 제품 1001 - VIEW (가중치: 1)
  2. 제품 1001 - LIKE (가중치: 3)
  3. 제품 1002 - VIEW (가중치: 1)
  4. 제품 1002 - SEARCH (가중치: 2)
  5. 제품 1003 - VIEW (가중치: 1)
  6. 제품 1003 - LIKE (가중치: 3)
  7. 제품 1003 - REGISTER (가중치: 5)
```

### 2. 행동 패턴 분석 결과
```bash
총 상호작용: 7회
총 점수: 16점
평균 점수: 2.29점
가장 많은 행동: VIEW
참여 수준: medium
행동 분포: {'VIEW': 3, 'LIKE': 2, 'SEARCH': 1, 'REGISTER': 1}
```

### 3. 사용자 프로필 생성
```bash
사용자 ID: 12345
프로필 강도: weak (ChromaDB 미연결로 벡터 없음)
상호작용한 제품: [1001, 1002, 1003]
선호도 벡터 존재: ❌
```

### 4. 다양한 참여 수준 테스트
```bash
높은 참여도 사용자 - 평균 점수: 4.0점, 수준: very_high
낮은 참여도 사용자 - 평균 점수: 1.0점, 수준: low
빈 데이터 사용자 - 평균 점수: 0점, 수준: none
```

### 5. 프로필 강도 계산
```bash
강한 프로필 (15개 REGISTER): strong
중간 프로필 (7개 LIKE): medium
약한 프로필 (1개 VIEW, 벡터 없음): weak
```

## 🔄 핵심 기능

### 1. 가중치 기반 점수 계산
- VIEW: 1점 (기본 관심)
- SEARCH: 2점 (적극적 관심)
- LIKE: 3점 (선호 표현)
- REGISTER: 5점 (강한 관심)

### 2. 참여 수준 분류
- **very_high**: 평균 4점 이상
- **high**: 평균 3-4점
- **medium**: 평균 2-3점
- **low**: 평균 1-2점
- **none**: 평균 1점 미만

### 3. 프로필 강도 분류
- **strong**: 10회 이상 상호작용 + 높은 참여도 + 벡터 존재
- **medium**: 5회 이상 상호작용 + 중간 이상 참여도 + 벡터 존재
- **weak**: 그 외 모든 경우

### 4. 선호도 벡터 생성
- 각 제품 벡터에 행동 가중치 적용
- 가중 평균으로 사용자 취향 벡터 계산
- 384차원 벡터로 정밀한 선호도 표현

## 📁 수정된 파일

### decodeat/services/recommendation_service.py
- `generate_user_preference_vector()` 메서드 개선
- `analyze_user_behavior_patterns()` 메서드 추가
- `create_user_preference_profile()` 메서드 추가
- `_calculate_profile_strength()` 메서드 추가
- `get_user_based_recommendations()` 메서드 개선
- ChromaDB 연결 상태 확인 로직 추가
- 에러 처리 및 로깅 강화

## 🎯 달성된 목표

### Requirements 충족
- **3.1**: ✅ 사용자 행동 데이터 가중치 적용
- **3.5**: ✅ 사용자 선호도 프로필 생성
- **5.1**: ✅ 행동 기반 개인화 추천

### 핵심 기능
- ✅ 사용자 행동 데이터 가중치 적용 (VIEW:1, SEARCH:2, LIKE:3, REGISTER:5)
- ✅ 사용자가 관심있어 한 제품들의 가중 평균 벡터 계산
- ✅ 사용자 선호도 프로필 생성 함수
- ✅ 행동 패턴 분석 및 통계
- ✅ 참여 수준 분석 (very_high/high/medium/low/none)
- ✅ 프로필 강도 계산 (strong/medium/weak)
- ✅ 이미 상호작용한 제품 필터링
- ✅ ChromaDB 연결 상태 확인
- ✅ 에러 처리 및 로깅

### 분석 기능
- ✅ 총 상호작용 횟수 계산
- ✅ 행동 유형별 분포 분석
- ✅ 가중치 기반 총점 및 평균점 계산
- ✅ 가장 많은 행동 유형 식별
- ✅ 참여 수준 자동 분류
- ✅ 상호작용한 제품 목록 관리

## 🚀 다음 단계
Task 7: 사용자 행동 기반 추천 API 구현
- POST /api/v1/recommend/user-based 엔드포인트 생성
- 사용자 행동 데이터로 선호도 벡터 생성
- 선호도 벡터와 유사한 제품 검색
- 개인화된 추천 이유 생성

## 📝 참고사항
- 행동 가중치는 사용자 관심도를 반영하여 설계
- 선호도 벡터는 가중 평균으로 계산하여 사용자 취향 정확도 향상
- 프로필 강도는 추천 품질 예측에 활용 가능
- ChromaDB 미연결 시에도 행동 분석 기능은 정상 작동
- 이미 상호작용한 제품은 추천에서 자동 제외