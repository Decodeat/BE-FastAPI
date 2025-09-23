# Requirements Document

## Introduction

이 기능은 현재 추천 시스템을 개선하여 벡터 데이터베이스에 product_id를 키로 상품 정보를 저장하고, 상품 기반 추천 알고리즘을 영양소 구성비(탄단지 비율)와 원재료 유사도 기반으로 개선하며, 추천 코드를 상품 기반과 사용자 행동 기반으로 분리하는 것입니다.

## Requirements

### Requirement 1

**User Story:** 개발자로서, 스프링에서 전처리된 product_id(외부 DB PK)를 키로 하여 벡터 데이터베이스에 상품 정보를 효율적으로 저장하고 조회할 수 있기를 원합니다. 그래야 상품 기반 추천 시 빠른 검색이 가능합니다.

#### Acceptance Criteria

1. WHEN 스프링에서 상품 분석 요청이 product_id와 함께 들어올 때 THEN 시스템은 해당 product_id를 키로 하여 상품 정보를 벡터 데이터베이스에 저장해야 합니다
2. WHEN 벡터 데이터베이스에 상품을 저장할 때 THEN 시스템은 외부 DB의 product_id, 상품명, 영양성분, 원재료 정보를 메타데이터로 포함해야 합니다
3. WHEN product_id로 상품을 조회할 때 THEN 시스템은 해당 상품의 벡터와 메타데이터를 반환해야 합니다
4. IF 동일한 product_id로 상품이 다시 분석 요청될 때 THEN 시스템은 기존 벡터 데이터를 업데이트해야 합니다

### Requirement 2

**User Story:** 사용자로서, 영양소 구성비(탄단지 비율)와 원재료 유사도를 기반으로 한 정확한 상품 추천을 받고 싶습니다. 그래야 내 건강 목표에 맞는 제품을 찾을 수 있습니다.

#### Acceptance Criteria

1. WHEN 상품 기반 추천을 요청할 때 THEN 시스템은 탄수화물, 단백질, 지방 비율을 계산하여 유사한 영양소 구성비를 가진 제품을 추천해야 합니다
2. WHEN 영양소 구성비를 계산할 때 THEN 시스템은 총 칼로리 대비 각 영양소의 비율을 백분율로 계산해야 합니다
3. WHEN 원재료 유사도를 계산할 때 THEN 시스템은 주요 원재료(상위 5개)의 일치도를 기반으로 유사도를 측정해야 합니다
4. WHEN 상품 추천 점수를 계산할 때 THEN 시스템은 영양소 구성비 유사도(60%)와 원재료 유사도(40%)를 가중 평균하여 최종 점수를 산출해야 합니다

### Requirement 3

**User Story:** 개발자로서, 상품 기반 추천과 사용자 행동 기반 추천 코드가 분리되어 있기를 원합니다. 그래야 각각의 로직을 독립적으로 유지보수할 수 있습니다.

#### Acceptance Criteria

1. WHEN 추천 서비스를 구조화할 때 THEN 시스템은 ProductBasedRecommendationService와 UserBehaviorRecommendationService로 분리해야 합니다
2. WHEN 상품 기반 추천을 요청할 때 THEN ProductBasedRecommendationService가 영양소 구성비와 원재료 유사도 기반 추천을 처리해야 합니다
3. WHEN 사용자 행동 기반 추천을 요청할 때 THEN UserBehaviorRecommendationService가 사용자 선호도 벡터 기반 추천을 처리해야 합니다
4. WHEN 각 추천 서비스를 호출할 때 THEN 독립적인 인터페이스를 통해 접근할 수 있어야 합니다

### Requirement 4

**User Story:** 사용자로서, 추천 결과에 영양소 구성비와 원재료 유사도에 대한 구체적인 설명을 받고 싶습니다. 그래야 왜 이 제품이 추천되었는지 이해할 수 있습니다.

#### Acceptance Criteria

1. WHEN 상품 기반 추천 결과를 반환할 때 THEN 시스템은 영양소 구성비 유사도 점수를 포함해야 합니다
2. WHEN 상품 기반 추천 결과를 반환할 때 THEN 시스템은 원재료 유사도 점수를 포함해야 합니다
3. WHEN 추천 이유를 생성할 때 THEN 시스템은 "탄단지 비율이 유사함" 또는 "주요 원재료가 비슷함" 등의 구체적인 설명을 제공해야 합니다
4. IF 영양소 구성비 유사도가 80% 이상일 때 THEN "영양소 구성이 매우 유사한 제품"이라는 메시지를 표시해야 합니다

### Requirement 5

**User Story:** 개발자로서, 기존 추천 API의 호환성을 유지하면서 새로운 추천 알고리즘을 적용하고 싶습니다. 그래야 클라이언트 코드 변경 없이 개선된 추천을 제공할 수 있습니다.

#### Acceptance Criteria

1. WHEN 기존 추천 API를 호출할 때 THEN 시스템은 기존 응답 형식을 유지해야 합니다
2. WHEN 새로운 추천 알고리즘을 적용할 때 THEN 기존 API 엔드포인트는 변경되지 않아야 합니다
3. WHEN 추천 결과를 반환할 때 THEN 새로운 필드(영양소 유사도, 원재료 유사도)는 선택적으로 포함되어야 합니다
4. IF 벡터 데이터베이스가 사용 불가능할 때 THEN 시스템은 기존 fallback 메커니즘을 사용해야 합니다