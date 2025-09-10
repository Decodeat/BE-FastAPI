# API Reference

## 서비스 클래스 상세 문서

### ImageDownloadService

이미지 URL에서 이미지를 다운로드하고 검증하는 서비스입니다.

#### 클래스 정의

```python
class ImageDownloadService:
    """Service for downloading and validating images from URLs."""
    
    # 지원되는 이미지 형식
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'BMP', 'GIF'}
    
    # 최대 파일 크기 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 요청 타임아웃 (30초)
    REQUEST_TIMEOUT = 30.0
```

#### 주요 메서드

##### `async download_image(url: str) -> bytes`

단일 이미지를 다운로드합니다.

**Parameters:**
- `url` (str): 다운로드할 이미지 URL

**Returns:**
- `bytes`: 다운로드된 이미지 데이터

**Raises:**
- `ValueError`: URL이 유효하지 않거나 이미지 형식이 지원되지 않는 경우
- `httpx.HTTPError`: 네트워크 요청 실패
- `RuntimeError`: 이미지가 너무 크거나 손상된 경우

**Example:**
```python
async with ImageDownloadService() as service:
    image_bytes = await service.download_image("https://example.com/image.jpg")
```

##### `async download_multiple_images(urls: list[str]) -> list[bytes]`

여러 이미지를 동시에 다운로드합니다.

**Parameters:**
- `urls` (list[str]): 다운로드할 이미지 URL 목록

**Returns:**
- `list[bytes]`: 다운로드된 이미지 데이터 목록

**Example:**
```python
async with ImageDownloadService() as service:
    images = await service.download_multiple_images([
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
    ])
```

#### 내부 메서드

##### `_is_valid_url(url: str) -> bool`
URL 형식의 유효성을 검사합니다.

##### `_is_image_content_type(content_type: str) -> bool`
HTTP Content-Type 헤더가 이미지를 나타내는지 확인합니다.

##### `_is_image_url(url: str) -> bool`
URL의 파일 확장자가 이미지 형식인지 확인합니다.

##### `_validate_image_format(image_bytes: bytes) -> bool`
PIL을 사용하여 이미지 형식과 무결성을 검증합니다.

---

### OCRService

Google Cloud Vision API를 사용하여 이미지에서 텍스트를 추출하는 서비스입니다.

#### 클래스 정의

```python
class OCRService:
    """Service for extracting text from images using Google Cloud Vision API."""
    
    def __init__(self):
        self._client: Optional[ImageAnnotatorClient] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
```

#### 주요 메서드

##### `async extract_text(image_bytes: bytes) -> str`

이미지에서 텍스트를 추출합니다.

**Parameters:**
- `image_bytes` (bytes): 원본 이미지 데이터

**Returns:**
- `str`: 추출된 텍스트

**Raises:**
- `ValueError`: 이미지 데이터가 비어있거나 유효하지 않은 경우
- `RuntimeError`: Google Cloud Vision API 호출 실패

**Example:**
```python
async with OCRService() as service:
    text = await service.extract_text(image_bytes)
    print(f"추출된 텍스트: {text}")
```

##### `async extract_text_from_multiple_images(images_bytes: list[bytes]) -> list[str]`

여러 이미지에서 동시에 텍스트를 추출합니다.

**Parameters:**
- `images_bytes` (list[bytes]): 이미지 데이터 목록

**Returns:**
- `list[str]`: 각 이미지에서 추출된 텍스트 목록

**Example:**
```python
async with OCRService() as service:
    texts = await service.extract_text_from_multiple_images([image1_bytes, image2_bytes])
```

#### 내부 메서드

##### `_extract_text_sync(image_bytes: bytes) -> str`
동기적으로 Vision API를 호출하여 텍스트를 추출합니다.

---

### ValidationService

Gemini AI를 사용하여 이미지 내용을 검증하는 서비스입니다.

#### 클래스 정의

```python
class ValidationService:
    """Service for validating nutrition-related content using Gemini AI."""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
```

#### 주요 메서드

##### `async validate_single_image(text: str) -> bool`

단일 이미지가 영양성분 또는 원재료 정보를 포함하는지 검증합니다.

**Parameters:**
- `text` (str): OCR로 추출된 텍스트

**Returns:**
- `bool`: 영양성분/원재료 정보 포함 여부

**검증 기준:**
1. 영양성분 정보 (칼로리, 나트륨, 탄수화물, 단백질, 지방 등)
2. 원재료명 또는 성분 정보
3. 영양성분 기준치 비율(%) 정보

**Example:**
```python
validation_service = ValidationService()
is_valid = await validation_service.validate_single_image(extracted_text)
```

##### `async validate_image_pair(text1: str, text2: str) -> bool`

두 이미지가 동일한 식품 제품에 속하는지 검증합니다.

**Parameters:**
- `text1` (str): 첫 번째 이미지의 OCR 텍스트
- `text2` (str): 두 번째 이미지의 OCR 텍스트

**Returns:**
- `bool`: 동일 제품 여부

**검증 기준:**
1. 제품명 동일성
2. 브랜드명 일치
3. 제조사 정보 일치
4. 전체적인 제품 정보 일관성

**Example:**
```python
validation_service = ValidationService()
is_same_product = await validation_service.validate_image_pair(text1, text2)
```

---

### AnalysisService

Gemini AI를 사용하여 영양성분 정보를 분석하고 구조화하는 서비스입니다.

#### 클래스 정의

```python
class AnalysisService:
    """Service for analyzing nutrition information using Gemini AI."""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
```

#### 주요 메서드

##### `async analyze_nutrition_info(text: str) -> Dict`

텍스트에서 영양성분 정보를 분석하여 구조화된 데이터로 반환합니다.

**Parameters:**
- `text` (str): OCR로 추출된 텍스트

**Returns:**
- `Dict`: 분석 결과 딕셔너리

**반환 구조:**
```python
{
    "decodeStatus": DecodeStatus,  # COMPLETED, CANCELLED, FAILED
    "product_name": str | None,    # 정규화된 제품명
    "nutrition_info": NutritionInfo | None,  # 영양성분 정보
    "ingredients": list[str] | None,  # 원재료 목록
    "message": str  # 상태 메시지
}
```

**Example:**
```python
analysis_service = AnalysisService()
result = await analysis_service.analyze_nutrition_info(combined_text)
```

#### 내부 메서드

##### `_normalize_product_name(product_name: str) -> str`

제품명을 정규화합니다.

**정규화 규칙:**
- 모든 공백 제거
- 한글, 영문, 숫자만 유지
- 특수문자 제거

**Example:**
```python
# "곰곰 육개장" -> "곰곰육개장"
normalized = service._normalize_product_name("곰곰 육개장")
```

##### `_extract_nutrition_values(nutrition_data: Dict) -> NutritionInfo`

영양성분 데이터에서 수치만 추출하여 NutritionInfo 객체로 변환합니다.

**처리 규칙:**
- 단위 제거 (g, mg, kcal 등)
- 숫자만 추출
- 정보가 없는 경우 None 반환

##### `_parse_ingredients(ingredients_text: str) -> Optional[List[str]]`

원재료 텍스트를 개별 원재료 목록으로 파싱합니다.

**파싱 규칙:**
- 쉼표, 콤마, 중점으로 분리
- 빈 문자열 및 불필요한 텍스트 제거
- 각 원재료 앞뒤 공백 제거

---

## 데이터 모델

### AnalyzeRequest

API 요청 모델입니다.

```python
class AnalyzeRequest(BaseModel):
    image_urls: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=2,
        description="분석할 이미지 URL 목록 (1-2개)"
    )
```

### AnalyzeResponse

API 응답 모델입니다.

```python
class AnalyzeResponse(BaseModel):
    decodeStatus: DecodeStatus  # 처리 상태
    product_name: Optional[str]  # 제품명
    nutrition_info: Optional[NutritionInfo]  # 영양성분 정보
    ingredients: Optional[List[str]]  # 원재료 목록
    message: Optional[str]  # 상태 메시지
```

### NutritionInfo

영양성분 정보 모델입니다.

```python
class NutritionInfo(BaseModel):
    calcium: Optional[str] = Field(None, description="칼슘 (mg)")
    carbohydrate: Optional[str] = Field(None, description="탄수화물 (g)")
    cholesterol: Optional[str] = Field(None, description="콜레스테롤 (mg)")
    dietary_fiber: Optional[str] = Field(None, description="식이섬유 (g)")
    energy: Optional[str] = Field(None, description="칼로리 (kcal)")
    fat: Optional[str] = Field(None, description="지방 (g)")
    protein: Optional[str] = Field(None, description="단백질 (g)")
    sat_fat: Optional[str] = Field(None, description="포화지방 (g)")
    sodium: Optional[str] = Field(None, description="나트륨 (mg)")
    sugar: Optional[str] = Field(None, description="당류 (g)")
    trans_fat: Optional[str] = Field(None, description="트랜스지방 (g)")
```

### DecodeStatus

처리 상태 열거형입니다.

```python
class DecodeStatus(str, Enum):
    COMPLETED = "completed"  # 성공적인 분석
    CANCELLED = "cancelled"  # 영양성분 정보 없음 또는 다른 제품
    FAILED = "failed"        # 기술적 오류 또는 이미지 품질 불량
```

---

## 오류 처리

### 공통 오류 패턴

모든 서비스는 다음과 같은 오류 처리 패턴을 따릅니다:

1. **입력 검증**: 매개변수 유효성 검사
2. **외부 API 오류**: 적절한 예외 변환
3. **로깅**: 구조화된 오류 로깅
4. **복구**: 가능한 경우 대안 제공

### 예외 계층

```
Exception
├── ValueError          # 입력 데이터 오류
├── RuntimeError        # 실행 시간 오류
├── httpx.HTTPError     # HTTP 요청 오류
└── GoogleCloudError    # Google Cloud API 오류
```

---

## 성능 고려사항

### 비동기 처리

- 모든 I/O 작업은 비동기로 처리
- 여러 이미지 동시 처리 지원
- 스레드 풀을 사용한 CPU 집약적 작업 처리

### 리소스 관리

- Context Manager 패턴 사용
- HTTP 클라이언트 연결 풀링
- 적절한 타임아웃 설정

### 메모리 최적화

- 스트리밍 다운로드로 메모리 사용량 제한
- 이미지 크기 제한 (10MB)
- 적절한 청크 크기 설정 (8KB)

---

## 확장 가이드

### 새로운 AI 모델 추가

1. `services/` 디렉토리에 새 서비스 클래스 생성
2. 기존 서비스와 동일한 인터페이스 구현
3. 설정에 새 API 키 추가
4. 테스트 코드 작성

### 새로운 이미지 형식 지원

1. `ImageDownloadService.SUPPORTED_FORMATS`에 형식 추가
2. `_is_image_content_type` 메서드에 MIME 타입 추가
3. `_is_image_url` 메서드에 파일 확장자 추가

### 캐싱 레이어 추가

1. Redis 또는 메모리 캐시 설정
2. OCR 결과 캐싱 (이미지 해시 기반)
3. 분석 결과 캐싱 (텍스트 해시 기반)

---

이 문서는 개발자가 프로젝트를 이해하고 확장할 수 있도록 상세한 API 참조를 제공합니다.