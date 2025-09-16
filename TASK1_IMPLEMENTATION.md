# Task 1: 개발 환경 설정 및 기본 구조 구축 - 구현 완료

## 개요
추천 시스템의 기본 환경 설정과 핵심 구조를 구축했습니다. ChromaDB와 sentence-transformers를 활용한 벡터 기반 추천 시스템의 기반을 마련했습니다.

## 구현된 구성 요소

### 1. 의존성 추가 (requirements.txt)
```
# ML and Vector Database dependencies
chromadb==0.4.24
sentence-transformers==2.2.2
scikit-learn>=1.4.0
```

### 2. 설정 확장 (decodeat/config.py)
ChromaDB 연결 설정 추가:
```python
# ChromaDB settings
chroma_host: str = Field("localhost", env="CHROMA_HOST", description="ChromaDB host")
chroma_port: int = Field(8000, env="CHROMA_PORT", description="ChromaDB port")
```

### 3. 벡터 서비스 (decodeat/services/vector_service.py)
**주요 기능:**
- 제품 데이터를 벡터로 변환 (sentence-transformers 사용)
- ChromaDB에 벡터 저장 및 검색
- 유사도 기반 제품 추천
- 한국어 지원 모델 (`jhgan/ko-sroberta-multitask`) 사용

**핵심 메서드:**
- `generate_product_vector()`: 제품 정보를 384차원 벡터로 변환
- `store_product_vector()`: ChromaDB에 벡터 저장
- `find_similar_products()`: 유사 제품 검색
- `search_by_user_preferences()`: 사용자 선호도 기반 검색

### 4. 추천 서비스 (decodeat/services/recommendation_service.py)
**주요 기능:**
- 사용자 행동 데이터 분석
- 가중치 기반 선호도 벡터 생성
- 개인화된 추천 생성

**행동 가중치:**
- REGISTER: 5 (직접 등록)
- LIKE: 3 (좋아요)
- SEARCH: 2 (검색)
- VIEW: 1 (조회)

**핵심 메서드:**
- `generate_user_preference_vector()`: 사용자 선호도 벡터 생성
- `get_user_based_recommendations()`: 사용자 기반 추천
- `get_product_based_recommendations()`: 제품 기반 추천

### 5. API 모델 확장 (decodeat/api/models.py)
추가된 모델:
- `UserBehavior`: 사용자 행동 데이터
- `UserBasedRecommendationRequest`: 사용자 기반 추천 요청
- `ProductBasedRecommendationRequest`: 제품 기반 추천 요청
- `RecommendationResult`: 개별 추천 결과
- `RecommendationResponse`: 추천 응답

### 6. 추천 API 라우트 (decodeat/api/recommendation_routes.py)
**엔드포인트:**
- `POST /api/v1/recommend/user-based`: 사용자 기반 추천
- `POST /api/v1/recommend/product-based`: 제품 기반 추천
- `GET /api/v1/recommend/health`: 헬스체크

### 7. 메인 애플리케이션 확장 (decodeat/main.py)
- 추천 라우터 등록: `/api/v1/recommend`

### 8. 기존 분석 API 확장 (decodeat/api/routes.py)
- 성공적인 영양성분 분석 후 자동 벡터 생성 및 저장
- `_auto_generate_product_vector()` 함수 추가

## 기술적 특징

### 벡터 임베딩
- **모델**: `jhgan/ko-sroberta-multitask` (한국어 특화)
- **차원**: 384차원
- **입력**: 제품명 + 영양성분 + 원재료 텍스트

### 유사도 계산
- **방법**: 코사인 유사도 (ChromaDB 내장)
- **거리 변환**: `similarity = max(0, 1 - distance)`

### 추천 알고리즘
1. **사용자 기반**: 행동 가중치를 적용한 선호도 벡터 생성
2. **제품 기반**: 벡터 유사도를 통한 유사 제품 추천

## 요구사항 충족

### Requirement 1.1 ✅
- ChromaDB 설치 및 연결 설정 완료
- sentence-transformers 라이브러리 설치 완료
- FastAPI 라우트 구조 확장 완료

### Requirement 4.1 ✅
- 영양성분 분석 성공 시 자동 벡터 생성 구현
- 백그라운드에서 실행되어 메인 응답에 영향 없음

## 다음 단계

1. **ChromaDB 서버 실행**:
   ```bash
   docker run -p 8000:8000 chromadb/chroma
   ```

2. **API 테스트**:
   - 기존 `/analyze` 엔드포인트로 제품 분석
   - 새로운 추천 엔드포인트 테스트

3. **다음 작업**: Task 2로 진행

## 파일 구조
```
decodeat/
├── services/
│   ├── vector_service.py          # 새로 추가
│   └── recommendation_service.py  # 새로 추가
├── api/
│   ├── models.py                  # 추천 모델 추가
│   ├── routes.py                  # 자동 벡터 생성 추가
│   └── recommendation_routes.py   # 새로 추가
├── config.py                      # ChromaDB 설정 추가
└── main.py                        # 추천 라우터 등록
```