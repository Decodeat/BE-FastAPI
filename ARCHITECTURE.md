# DecodeAt 시스템 아키텍처

## 기술 스택

### 백엔드 프레임워크
- **FastAPI**: 메인 웹 프레임워크
- **Python 3.11**: 런타임 환경
- **Uvicorn**: ASGI 서버

### AI/ML 서비스
- **Google Cloud Vision API**: OCR 텍스트 추출
- **Google Gemini AI**: 영양성분 분석
- **Sentence Transformers**: 다국어 임베딩 생성
- **ChromaDB**: 벡터 데이터베이스

### 데이터베이스 및 캐싱
- **ChromaDB**: 벡터 유사도 검색
- **Redis**: 캐싱 (선택적)

### 컨테이너화
- **Docker**: 애플리케이션 컨테이너화
- **Docker Compose**: 멀티 컨테이너 오케스트레이션

## 시스템 아키텍처

```mermaid
graph TB
    %% Client Layer
    Client[클라이언트 애플리케이션]
    
    %% API Gateway Layer
    subgraph "API Layer"
        FastAPI[FastAPI Server<br/>Port: 8000]
        MainRouter[Main Routes<br/>/api/v1/analyze]
        RecommendRouter[Recommendation Routes<br/>/api/v1/recommend]
    end
    
    %% Service Layer
    subgraph "Service Layer"
        ImageService[Image Download Service]
        OCRService[OCR Service]
        ValidationService[Validation Service]
        AnalysisService[Analysis Service]
        RecommendService[Recommendation Service]
        VectorService[Vector Service]
    end
    
    %% External AI Services
    subgraph "External AI Services"
        GCV[Google Cloud Vision API<br/>OCR 텍스트 추출]
        Gemini[Google Gemini AI<br/>영양성분 분석]
        SentenceT[Sentence Transformers<br/>다국어 임베딩]
    end
    
    %% Database Layer
    subgraph "Database Layer"
        ChromaDB[ChromaDB<br/>Port: 8001<br/>벡터 유사도 검색]
        Redis[Redis<br/>Port: 6379<br/>캐싱]
    end
    
    %% Utility Layer
    subgraph "Utility Layer"
        Logging[Logging Service]
        Performance[Performance Monitor]
        Config[Configuration Manager]
    end
    
    %% Client connections
    Client --> FastAPI
    
    %% API routing
    FastAPI --> MainRouter
    FastAPI --> RecommendRouter
    
    %% Main analysis flow
    MainRouter --> ImageService
    MainRouter --> OCRService
    MainRouter --> ValidationService
    MainRouter --> AnalysisService
    MainRouter --> VectorService
    
    %% Recommendation flow
    RecommendRouter --> RecommendService
    RecommendService --> VectorService
    
    %% Service to external AI connections
    OCRService --> GCV
    AnalysisService --> Gemini
    VectorService --> SentenceT
    
    %% Database connections
    VectorService --> ChromaDB
    RecommendService --> Redis
    
    %% Utility connections
    ImageService --> Logging
    OCRService --> Logging
    AnalysisService --> Logging
    RecommendService --> Performance
    VectorService --> Performance
    
    %% Configuration
    FastAPI --> Config
    
    %% Styling
    classDef apiLayer fill:#e1f5fe
    classDef serviceLayer fill:#f3e5f5
    classDef externalService fill:#fff3e0
    classDef database fill:#e8f5e8
    classDef utility fill:#fce4ec
    
    class FastAPI,MainRouter,RecommendRouter apiLayer
    class ImageService,OCRService,ValidationService,AnalysisService,RecommendService,VectorService serviceLayer
    class GCV,Gemini,SentenceT externalService
    class ChromaDB,Redis database
    class Logging,Performance,Config utility
```

## 영양성분 분석 플로우

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant IS as ImageService
    participant OCR as OCRService
    participant VS as ValidationService
    participant AS as AnalysisService
    participant VecS as VectorService
    participant GCV as Google Vision
    participant Gemini as Gemini AI
    participant Chroma as ChromaDB
    
    C->>API: POST /api/v1/analyze
    API->>IS: download_image(urls)
    IS-->>API: image_bytes
    
    API->>OCR: extract_text(image_bytes)
    OCR->>GCV: document_text_detection
    GCV-->>OCR: extracted_text
    OCR-->>API: text
    
    API->>VS: validate_content(text)
    VS-->>API: validation_result
    
    API->>AS: analyze_nutrition_info(text)
    AS->>Gemini: generate_content(prompt)
    Gemini-->>AS: structured_data
    AS-->>API: nutrition_analysis
    
    API->>VecS: auto_generate_vector(analysis)
    VecS->>Chroma: store_vector
    Chroma-->>VecS: success
    VecS-->>API: stored
    
    API-->>C: AnalyzeResponse
```

## 추천 시스템 플로우

```mermaid
sequenceDiagram
    participant C as Client
    participant API as RecommendAPI
    participant RS as RecommendService
    participant VS as VectorService
    participant Chroma as ChromaDB
    participant ST as SentenceTransformers
    
    C->>API: POST /api/v1/recommend/user-based
    API->>RS: get_user_based_recommendations
    
    RS->>VS: generate_user_preference_vector
    VS->>Chroma: get_product_vectors
    Chroma-->>VS: user_products
    VS->>ST: encode(user_preferences)
    ST-->>VS: preference_vector
    VS-->>RS: user_vector
    
    RS->>VS: search_by_user_preferences
    VS->>Chroma: query(preference_vector)
    Chroma-->>VS: similar_products
    VS-->>RS: recommendations
    
    RS->>RS: enhance_with_reasons
    RS-->>API: enhanced_recommendations
    API-->>C: RecommendationResponse
```

## Docker 컨테이너 구성

```mermaid
graph LR
    subgraph "Docker Network: decodeat-network"
        subgraph "decodeat-api:8000"
            FastAPI[FastAPI Application]
            Services[All Services]
        end
        
        subgraph "chromadb:8001"
            ChromaDB[ChromaDB Vector DB]
        end
        
        subgraph "redis:6379"
            Redis[Redis Cache]
        end
    end
    
    FastAPI --> ChromaDB
    FastAPI --> Redis
    
    External[External APIs<br/>Google Cloud Vision<br/>Gemini AI] --> FastAPI
```

## 핵심 아키텍처 특징

### 1. 마이크로서비스 지향 설계
- 각 기능별로 독립적인 서비스 클래스
- 의존성 주입을 통한 느슨한 결합
- 비동기 처리로 성능 최적화

### 2. AI 서비스 통합
- Google Cloud Vision API로 OCR 처리
- Gemini AI로 구조화된 영양성분 분석
- Sentence Transformers로 다국어 임베딩 생성

### 3. 벡터 기반 추천 시스템
- ChromaDB를 활용한 벡터 유사도 검색
- 사용자 행동 기반 개인화 추천
- 제품 간 유사도 기반 추천

### 4. 컨테이너 기반 배포
- Docker Compose로 멀티 컨테이너 관리
- 서비스별 독립적인 스케일링 가능
- 헬스체크 및 자동 재시작 지원

### 5. 성능 최적화
- 비동기 처리로 동시성 향상
- 캐싱 레이어로 응답 속도 개선
- 성능 모니터링 및 측정

## 전체 시스템 아키텍처 (AWS 배포)

```mermaid
graph TD
    subgraph "End-User"
        Client[📱💻 Client Application]
    end

    subgraph "AWS Cloud ap-northeast-2"
        ALB[Application Load Balancer]
        subgraph "Amazon EC2"
            SpringBoot[Spring Boot Server]
            FastAPI[FastAPI Server<br/>Port 8000]
        end
        subgraph "Data Persistence Layer"
            RDS[Amazon RDS<br/>MySQL/PostgreSQL]
            S3[Amazon S3<br/>Image Storage]
            VectorDB[ChromaDB<br/>Vector Database]
        end
    end

    subgraph "External Services"
        Kakao[Kakao Authentication API]
        GoogleAI[Google Cloud AI Platform<br/>Vision API + Gemini]
    end

    %% Authentication Flow
    Client -->|HTTPS Request| ALB
    ALB -->|HTTP| SpringBoot
    SpringBoot -->|1. Kakao Redirect| Client
    Client -->|2. User Consent| Kakao
    Kakao -->|3. Auth Code| SpringBoot
    SpringBoot -->|4. Token Request| Kakao
    Kakao -->|5. Access Token| SpringBoot
    SpringBoot -->|6. User Info Request| Kakao
    Kakao -->|7. User Profile| SpringBoot
    SpringBoot -->|8. Issue JWT| Client

    %% Image Analysis Flow
    Client -->|Image Upload JWT| SpringBoot
    SpringBoot -->|AWS SDK| S3
    SpringBoot -->|JDBC| RDS
    SpringBoot -->|HTTP POST Image Location| FastAPI
    FastAPI -->|AWS SDK| S3
    FastAPI -->|REST API Call| GoogleAI
    GoogleAI -->|Analysis Result JSON| FastAPI
    FastAPI -->|Generate Vector| FastAPI
    FastAPI -->|Analysis Result + Vector JSON| SpringBoot
    SpringBoot -->|Store Vector| VectorDB
    SpringBoot -->|JDBC Update| RDS
    SpringBoot -->|HTTP 200 OK| Client

    %% Recommendation Flow
    Client -->|Recommendation Request JWT| SpringBoot
    SpringBoot -->|Query by ID| VectorDB
    SpringBoot -->|k-NN Search| VectorDB
    VectorDB -->|Similar Image IDs| SpringBoot
    SpringBoot -->|JDBC Batch Fetch| RDS
    SpringBoot -->|JSON Response| Client

    %% Styling
    classDef client fill:#e1f5fe
    classDef aws fill:#ff9800
    classDef external fill:#4caf50
    classDef database fill:#9c27b0
    
    class Client client
    class ALB,SpringBoot,FastAPI,RDS,S3,VectorDB aws
    class Kakao,GoogleAI external
```