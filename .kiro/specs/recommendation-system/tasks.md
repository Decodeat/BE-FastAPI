# Implementation Plan

- [x] 1. 개발 환경 설정 및 기본 구조 구축
  - ChromaDB 설치 및 연결 설정
  - sentence-transformers 라이브러리 설치
  - 기본 FastAPI 라우트 구조 확장
  - _Requirements: 1.1, 4.1_

- [x] 2. 벡터 임베딩 생성 서비스 구현
  - sentence-transformer 모델 로드 (한국어 지원)
  - 영양성분 데이터를 텍스트로 변환하는 함수 구현
  - 원재료 데이터를 텍스트로 변환하는 함수 구현
  - 텍스트를 384차원 벡터로 변환하는 함수 구현
  - _Requirements: 4.1, 4.2_

- [x] 3. ChromaDB 벡터 저장소 서비스 구현
  - ChromaDB 클라이언트 초기화
  - product_vectors 컬렉션 생성
  - 제품 벡터 저장 함수 구현
  - 벡터 유사도 검색 함수 구현
  - _Requirements: 4.3, 4.5_

- [x] 4. 기존 상품 분석 API에 벡터 생성 기능 통합
  - 기존 analyze 함수에 벡터 생성 로직 추가
  - 분석 성공 시 자동으로 벡터 생성 및 저장
  - 벡터 생성 실패 시에도 기존 분석 결과는 정상 반환
  - 에러 처리 및 로깅 추가
  - _Requirements: 1.1, 1.3, 4.1_

- [x] 5. 제품 기반 유사 제품 추천 API 구현
  - POST /api/v1/recommend/product-based 엔드포인트 생성
  - 특정 제품 ID로 벡터 검색
  - 유사도 점수 계산 및 정렬
  - 추천 이유 생성 로직 구현
  - _Requirements: 5.2, 5.5_

- [x] 6. 사용자 행동 데이터 분석 서비스 구현
  - 사용자 행동 데이터 가중치 적용 로직 (VIEW:1, SEARCH:2, LIKE:3, REGISTER:5)
  - 사용자가 관심있어 한 제품들의 평균 벡터 계산
  - 사용자 선호도 프로필 생성 함수 구현
  - _Requirements: 3.1, 3.5, 5.1_

- [x] 7. 사용자 행동 기반 추천 API 구현
  - POST /api/v1/recommend/user-based 엔드포인트 생성
  - 사용자 행동 데이터로 선호도 벡터 생성
  - 선호도 벡터와 유사한 제품 검색
  - 개인화된 추천 이유 생성
  - _Requirements: 5.1, 5.3, 5.5_

- [x] 8. API 응답 모델 및 에러 처리 구현
  - RecommendationResult 모델 정의
  - API 요청/응답 검증 로직 구현
  - 데이터 부족 시 폴백 로직 (인기도 기반 추천)
  - 적절한 HTTP 상태 코드 및 에러 메시지 반환
  - _Requirements: 6.1, 6.2_

- [x] 9. 성능 최적화 및 테스트
  - 벡터 검색 성능 측정 및 최적화
  - 추천 API 응답 시간 측정
  - 단위 테스트 작성 (벡터 생성, 유사도 검색)
  - 통합 테스트 작성 (전체 추천 플로우)
  - _Requirements: 6.1, 6.4_

- [ ] 10. Docker 설정 및 배포 준비
  - ChromaDB 컨테이너 설정
  - Python ML 서버 Dockerfile 업데이트
  - docker-compose.yml 설정
  - 환경 변수 및 설정 파일 정리
  - _Requirements: 8.1, 8.5_