# Decodeat API

Decodeat API는 음식 상품 이미지(주로 성분표)를 분석하여 텍스트 정보를 추출하고, 이를 기반으로 사용자에게 맞춤형 상품 추천을 제공하는 FastAPI 기반의 백엔드 서비스입니다.

## ✨ 주요 기능

- **이미지 유효성 검증**: Gemini AI를 사용하여 OCR로 추출된 텍스트가 실제 영양성분표나 원재료명인지 확인하여 분석의 정확도를 높입니다.
- **이미지 OCR**: Google Cloud Vision API를 사용하여 이미지에서 텍스트(상품 성분, 영양 정보 등)를 추출합니다.
- **데이터 벡터화**: 추출된 텍스트를 Sentence Transformers를 이용해 벡터로 변환하여 의미 기반 검색을 가능하게 합니다.
- **상품 추천**: ChromaDB에 저장된 벡터를 기반으로 유사한 상품을 찾아 추천합니다.

## 🛠️ 기술 스택

- **Backend**: FastAPI, Uvicorn
- **AI & Machine Learning**:
  - `google-generativeai`: 이미지 유효성 검증 및 텍스트 분석
  - `google-cloud-vision`: 이미지 내 텍스트 인식을 위한 OCR
  - `sentence-transformers`: 텍스트 임베딩 및 벡터화
  - `scikit-learn`: 머신러닝 유틸리티
- **Database**: ChromaDB (벡터 데이터베이스)
- **Image Processing**: Pillow, OpenCV-Python
- **Containerization**: Docker, Docker Compose

## 📂 프로젝트 구조

```
/Users/junho/Desktop/BE-FastAPI/
├───decodeat/                 # 메인 애플리케이션 소스 코드
│   ├───api/                  # API 라우트 및 Pydantic 모델
│   ├───services/             # 비즈니스 로직 (OCR, 추천, 벡터화, 유효성 검증 등)
│   └───main.py               # FastAPI 애플리케이션 진입점
├───tests/                    # 단위 및 통합 테스트 코드
├───Dockerfile                # 애플리케이션 Docker 이미지 빌드 설정
└───... (기타 설정 파일)
```

## 🌊 전체 상품 분석 흐름

```mermaid
graph TD
    A[1. 이미지 URL 입력] --> B{2. 이미지 다운로드};
    B --> C{3. OCR 수행};
    C --> D{4. 유효성 검증 (ValidationService)};
    D -- 유효한 경우 --> E[5. 텍스트 분석 및 정제];
    D -- 유효하지 않은 경우 --> I[분석 중단];
    E --> F{6. 벡터 변환};
    F --> G[7. 벡터 DB에 저장/검색];
    G --> H[8. 유사 상품 추천];
```

## 🔬 `ValidationService` 동작 방식

`ValidationService`는 Gemini AI를 사용하여 입력된 이미지가 분석에 적합한지 판단하는 핵심적인 역할을 합니다.

### 1. 단일 이미지 유효성 검증 (`validate_single_image`)

- **목표**: 한 장의 이미지가 영양성분표 또는 원재료명 정보를 포함하는지 확인합니다.

```mermaid
graph TD
    subgraph 단일 이미지 검증
        A[OCR 텍스트 입력] --> B{Gemini AI 질의};
        B -- "텍스트가 식품 라벨 정보를 포함하는가?" --> C{판단};
        C --> D{응답이 'true'인가?};
        D -- Yes --> E[결과: 유효함 (True)];
        D -- No --> F[결과: 유효하지 않음 (False)];
    end
```

### 2. 이미지 쌍 동일성 검증 (`validate_image_pair`)

- **목표**: 두 장의 이미지가 동일한 제품에 속하는지 확인합니다. (예: 성분표 앞면과 뒷면)
- **로직**: 텍스트 분석을 먼저 시도하고, 실패 또는 불확실할 경우 색상 분석으로 2차 검증을 수행합니다.

```mermaid
graph TD
    subgraph 이미지 쌍 검증
        A[이미지 1, 2의 OCR 텍스트 입력] --> B{1차: 텍스트 분석};
        B -- "두 텍스트가 동일 제품에 대한 내용인가?" --> C{Gemini AI 질의};
        C --> D{응답이 'true'인가?};
        D -- Yes --> E[최종 판정: 동일 제품 (True)];
        D -- No --> F{2차: 색상 분석};
        F -- "두 이미지의 색상 분포가 유사한가?" --> G[색상 히스토그램 비교];
        G --> H{유사도가 임계값 이상인가?};
        H -- Yes --> E;
        H -- No --> I[최종 판정: 다른 제품 (False)];
    end
```

## 🚀 시작하기

### Docker 사용 (권장)

1.  프로젝트 루트 디렉토리에서 아래 명령어를 실행합니다.
    ```bash
    docker-compose up --build
    ```

2.  API 서버가 `http://localhost:8000`에서 실행됩니다.

### 로컬 환경에서 직접 실행

1.  필요한 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

2.  Uvicorn을 사용하여 서버를 실행합니다.
    ```bash
    uvicorn decodeat.main:app --reload
    ```