# Implementation Plan

- [x] 1. 벡터 서비스 확장 및 영양소 구성비 계산 기능 구현
  - EnhancedVectorService 클래스 생성하여 기존 VectorService 확장
  - 영양소 구성비 계산 메서드 구현 (탄단지 비율)
  - 주요 원재료 추출 메서드 구현
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 1.1 영양소 구성비 계산 로직 구현
  - calculate_nutrition_ratios 메서드 작성 (탄수화물, 단백질, 지방 칼로리 기여도 계산)
  - 영양소별 칼로리 변환 상수 정의 (탄수화물/단백질: 4kcal/g, 지방: 9kcal/g)
  - 총 칼로리 대비 각 영양소 비율 백분율 계산
  - 영양소 데이터 검증 및 예외 처리 로직 추가
  - _Requirements: 2.1, 2.2_

- [x] 1.2 주요 원재료 추출 및 정제 로직 구현
  - extract_main_ingredients 메서드 작성 (상위 5개 원재료 추출)
  - 원재료 중복 제거 및 정제 로직 구현
  - 빈 문자열 및 무효한 원재료 필터링
  - _Requirements: 2.3_

- [x] 1.3 product_id 키 기반 벡터 저장 메서드 구현
  - store_product_with_id 메서드 작성
  - 영양소 구성비와 원재료 정보를 메타데이터에 포함
  - 기존 product_id 데이터 업데이트 로직 구현
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. 상품 기반 추천 서비스 분리 및 새로운 알고리즘 구현
  - ProductBasedRecommendationService 클래스 생성
  - 영양소 구성비 유사도 계산 메서드 구현
  - 원재료 유사도 계산 메서드 구현 (Jaccard 유사도 + 가중치)
  - 최종 추천 점수 계산 메서드 구현 (영양소 60% + 원재료 40%)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.2_

- [x] 2.1 영양소 구성비 유사도 계산 메서드 구현
  - calculate_nutrition_similarity 메서드 작성
  - 탄단지 비율 벡터 간 코사인 유사도 계산
  - 영양소 데이터 부족 시 예외 처리 로직
  - _Requirements: 2.1, 2.2_

- [x] 2.2 원재료 유사도 계산 메서드 구현
  - calculate_ingredient_similarity 메서드 작성
  - Jaccard 유사도 기반 계산 (교집합/합집합)
  - 상위 3개 원재료 가중치 2.0, 4-5번째 가중치 1.0 적용
  - 빈 원재료 리스트 처리 로직
  - _Requirements: 2.3_

- [x] 2.3 최종 추천 점수 계산 및 추천 생성 메서드 구현
  - calculate_final_score 메서드 작성 (영양소 60% + 원재료 40% 가중 평균)
  - get_recommendations 메서드 작성 (전체 추천 플로우)
  - 추천 이유 생성 로직 구현 (영양소/원재료 유사도 기반)
  - _Requirements: 2.4, 4.1, 4.2, 4.3, 4.4_

- [x] 3. 사용자 행동 기반 추천 서비스 분리
  - UserBehaviorRecommendationService 클래스 생성
  - 기존 사용자 선호도 벡터 생성 로직 이전
  - 사용자 행동 분석 로직 이전
  - 개인화 추천 생성 로직 이전
  - _Requirements: 3.1, 3.3_

- [x] 3.1 UserBehaviorRecommendationService 클래스 구현
  - 기존 RecommendationService에서 사용자 관련 메서드들 분리
  - generate_user_preference_vector 메서드 이전
  - analyze_user_behavior_patterns 메서드 이전
  - get_recommendations 메서드 구현 (사용자 행동 기반)
  - _Requirements: 3.1, 3.3_

- [x] 4. 통합 RecommendationService 리팩토링
  - 기존 RecommendationService를 통합 인터페이스로 변경
  - ProductBasedRecommendationService와 UserBehaviorRecommendationService 인스턴스 생성
  - 기존 API 메서드들이 새로운 서비스들을 호출하도록 수정
  - 기존 API 호환성 유지
  - _Requirements: 3.4, 5.1, 5.2_

- [x] 4.1 통합 RecommendationService 클래스 수정
  - __init__ 메서드에서 ProductBasedRecommendationService와 UserBehaviorRecommendationService 초기화
  - get_product_based_recommendations 메서드가 새로운 ProductBasedRecommendationService 호출
  - get_user_based_recommendations 메서드가 새로운 UserBehaviorRecommendationService 호출
  - _Requirements: 3.4, 5.1, 5.2_

- [x] 5. API 응답 모델 확장
  - EnhancedRecommendationResult 모델 생성
  - 영양소 유사도, 원재료 유사도 필드 추가
  - 영양소 구성비 정보 필드 추가
  - 주요 원재료 정보 필드 추가
  - 기존 RecommendationResult와 호환성 유지
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.3_

- [x] 5.1 확장된 추천 결과 모델 구현
  - EnhancedRecommendationResult 클래스 작성
  - nutrition_similarity, ingredient_similarity 필드 추가
  - nutrition_ratios, main_ingredients 필드 추가
  - 기존 RecommendationResult 상속하여 호환성 유지
  - _Requirements: 4.1, 4.2, 5.3_

- [x] 6. 추천 API 라우트 업데이트
  - recommendation_routes.py에서 새로운 추천 서비스 사용
  - 확장된 응답 정보 포함 (선택적)
  - 기존 API 엔드포인트 및 응답 형식 유지
  - 에러 처리 및 fallback 메커니즘 유지
  - _Requirements: 5.1, 5.2, 5.4_

- [x] 6.1 상품 기반 추천 API 라우트 업데이트
  - get_product_based_recommendations 함수에서 새로운 ProductBasedRecommendationService 사용
  - 영양소 유사도와 원재료 유사도 정보를 응답에 포함
  - 기존 응답 형식 유지하면서 새로운 필드는 선택적으로 추가
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6.2 사용자 기반 추천 API 라우트 업데이트
  - get_user_based_recommendations 함수에서 새로운 UserBehaviorRecommendationService 사용
  - 기존 개인화 추천 로직 유지
  - 에러 처리 및 fallback 메커니즘 유지
  - _Requirements: 5.1, 5.2, 5.4_

- [x] 7. 단위 테스트 작성
  - 영양소 구성비 계산 테스트 작성
  - 원재료 유사도 계산 테스트 작성
  - product_id 키 기반 저장/조회 테스트 작성
  - 새로운 추천 알고리즘 테스트 작성
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_

- [x] 7.1 영양소 구성비 계산 테스트 구현
  - test_calculate_nutrition_ratios 함수 작성
  - 정상적인 영양소 데이터로 탄단지 비율 계산 검증
  - 부족한 영양소 데이터 처리 테스트
  - 잘못된 영양소 데이터 처리 테스트
  - _Requirements: 2.1, 2.2_

- [x] 7.2 원재료 유사도 계산 테스트 구현
  - test_calculate_ingredient_similarity 함수 작성
  - Jaccard 유사도 계산 검증
  - 가중치 적용 로직 검증
  - 빈 원재료 리스트 처리 테스트
  - _Requirements: 2.3_

- [x] 7.3 벡터 서비스 확장 기능 테스트 구현
  - test_store_product_with_id 함수 작성
  - product_id 키 기반 저장 검증
  - 메타데이터 포함 저장 검증
  - 기존 데이터 업데이트 검증
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 8. 통합 테스트 작성
  - 전체 상품 기반 추천 플로우 테스트 작성
  - API 호환성 테스트 작성
  - 성능 테스트 작성 (대용량 데이터)
  - 에러 시나리오 테스트 작성
  - _Requirements: 5.1, 5.2, 5.4_

- [x] 8.1 상품 기반 추천 통합 테스트 구현
  - test_enhanced_product_recommendation_flow 함수 작성
  - 상품 저장부터 추천 생성까지 전체 플로우 검증
  - 영양소 유사도와 원재료 유사도 포함 검증
  - 추천 점수 계산 정확성 검증
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 8.2 API 호환성 및 성능 테스트 구현
  - test_api_compatibility 함수 작성
  - 기존 API 형식 유지 검증
  - 새로운 필드 선택적 포함 검증
  - 대용량 데이터 성능 테스트 (2초 이내 응답)
  - _Requirements: 5.1, 5.2, 5.3_