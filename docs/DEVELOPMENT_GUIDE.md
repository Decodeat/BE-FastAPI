# Development Guide

## 개발 환경 설정

### 1. 개발 도구 설치

#### 필수 도구
- **Python 3.11+**: 프로젝트 런타임
- **Git**: 버전 관리
- **IDE**: VS Code, PyCharm 등

#### 권장 도구
- **Docker**: 컨테이너화된 개발 환경
- **Postman**: API 테스트
- **Google Cloud CLI**: GCP 서비스 관리

### 2. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd nutrition-label-api

# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt

# 개발 의존성 설치 (선택사항)
pip install -r requirements-dev.txt
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# 필요한 API 키 설정
# - GEMINI_API_KEY: Gemini AI API 키
# - GOOGLE_APPLICATION_CREDENTIALS: GCP 서비스 계정 키 파일 경로
```

## 코딩 표준

### Python 코딩 스타일

#### PEP 8 준수
```python
# 좋은 예
def calculate_nutrition_score(protein: float, fat: float) -> float:
    """영양 점수를 계산합니다."""
    return (protein * 4) + (fat * 9)

# 나쁜 예
def calcNutrScore(p,f):
    return (p*4)+(f*9)
```

#### 타입 힌트 사용
```python
from typing import Optional, List, Dict, Any

async def process_images(
    urls: List[str], 
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    """이미지를 처리하고 결과를 반환합니다."""
    pass
```

#### Docstring 작성 (Google 스타일)
```python
def normalize_product_name(name: str) -> str:
    """제품명을 정규화합니다.
    
    공백을 제거하고 한글, 영문, 숫자만 유지합니다.
    
    Args:
        name: 원본 제품명
        
    Returns:
        정규화된 제품명
        
    Example:
        >>> normalize_product_name("곰곰 육개장")
        "곰곰육개장"
    """
    pass
```

### 비동기 프로그래밍 가이드

#### Context Manager 사용
```python
# 좋은 예
async with ImageDownloadService() as service:
    image = await service.download_image(url)

# 나쁜 예
service = ImageDownloadService()
image = await service.download_image(url)
# 리소스 정리 누락
```

#### 예외 처리
```python
async def safe_download_image(url: str) -> Optional[bytes]:
    """안전하게 이미지를 다운로드합니다."""
    try:
        async with ImageDownloadService() as service:
            return await service.download_image(url)
    except ValueError as e:
        logger.warning(f"Invalid URL: {url}, error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
        return None
```

### 로깅 가이드

#### 구조화된 로깅 사용
```python
from decodeat.utils.logging import LoggingService

logger = LoggingService(__name__)

# 정보 로깅
logger.info("이미지 다운로드 시작", extra_data={
    "url": url,
    "size_limit": MAX_FILE_SIZE
})

# 오류 로깅
logger.error("이미지 다운로드 실패", extra_data={
    "url": url,
    "error_type": type(e).__name__
}, exc_info=True)
```

#### 로그 레벨 가이드
- **DEBUG**: 상세한 디버깅 정보
- **INFO**: 일반적인 실행 정보
- **WARNING**: 주의가 필요한 상황
- **ERROR**: 오류 발생

## 테스트 작성 가이드

### 단위 테스트

#### 테스트 구조
```python
import pytest
from unittest.mock import AsyncMock, patch

class TestImageDownloadService:
    """ImageDownloadService 테스트 클래스."""
    
    @pytest.fixture
    async def service(self):
        """테스트용 서비스 인스턴스."""
        async with ImageDownloadService() as service:
            yield service
    
    async def test_download_valid_image(self, service):
        """유효한 이미지 다운로드 테스트."""
        url = "https://example.com/test.jpg"
        
        # Mock 설정
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_response = AsyncMock()
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_stream.return_value.__aenter__.return_value = mock_response
            
            # 테스트 실행
            result = await service.download_image(url)
            
            # 검증
            assert isinstance(result, bytes)
            mock_stream.assert_called_once()
```

#### 테스트 데이터 관리
```python
# tests/fixtures/sample_data.py
SAMPLE_NUTRITION_TEXT = """
제품명: 테스트 제품
칼로리: 100kcal
단백질: 5g
지방: 3g
"""

SAMPLE_INGREDIENTS_TEXT = """
원재료명: 밀가루, 설탕, 소금
"""
```

### 통합 테스트

#### API 엔드포인트 테스트
```python
from fastapi.testclient import TestClient
from decodeat.main import app

client = TestClient(app)

def test_analyze_endpoint():
    """분석 엔드포인트 통합 테스트."""
    response = client.post("/api/v1/analyze", json={
        "image_urls": ["https://example.com/nutrition.jpg"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "decodeStatus" in data
    assert "product_name" in data
```

### 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 파일
pytest tests/test_image_download_service.py

# 커버리지 측정
pytest --cov=decodeat --cov-report=html

# 병렬 실행
pytest -n auto
```

## 디버깅 가이드

### 로컬 디버깅

#### VS Code 설정 (.vscode/launch.json)
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/decodeat/main.py",
            "env": {
                "GOOGLE_APPLICATION_CREDENTIALS": "${workspaceFolder}/gcp-key.json"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

#### 디버그 로깅 활성화
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m decodeat.main
```

### 서비스별 디버깅

#### 이미지 다운로드 디버깅
```python
import asyncio
from decodeat.services.image_download_service import ImageDownloadService

async def debug_download():
    url = "https://example.com/image.jpg"
    
    async with ImageDownloadService() as service:
        try:
            # URL 검증
            if not service._is_valid_url(url):
                print(f"Invalid URL: {url}")
                return
            
            # 이미지 다운로드
            image_bytes = await service.download_image(url)
            print(f"Downloaded: {len(image_bytes)} bytes")
            
            # 이미지 검증
            if service._validate_image_format(image_bytes):
                print("Image format is valid")
            else:
                print("Invalid image format")
                
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(debug_download())
```

#### OCR 디버깅
```python
import asyncio
from decodeat.services.ocr_service import OCRService

async def debug_ocr():
    # 테스트 이미지 로드
    with open("test_image.jpg", "rb") as f:
        image_bytes = f.read()
    
    async with OCRService() as service:
        try:
            text = await service.extract_text(image_bytes)
            print(f"Extracted text ({len(text)} chars):")
            print(text)
        except Exception as e:
            print(f"OCR Error: {e}")

asyncio.run(debug_ocr())
```

## 성능 최적화

### 프로파일링

#### cProfile 사용
```python
import cProfile
import asyncio
from decodeat.api.routes import analyze_nutrition_label

def profile_analysis():
    # 프로파일링 코드
    pass

if __name__ == "__main__":
    cProfile.run('profile_analysis()', 'profile_stats')
```

#### 메모리 사용량 모니터링
```python
import tracemalloc
import asyncio

async def monitor_memory():
    tracemalloc.start()
    
    # 테스트 코드 실행
    await analyze_nutrition_label(request)
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
    
    tracemalloc.stop()
```

### 최적화 기법

#### 이미지 처리 최적화
```python
# 이미지 크기 제한
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# 청크 단위 다운로드
CHUNK_SIZE = 8192  # 8KB

# 동시 처리 제한
MAX_CONCURRENT_DOWNLOADS = 5
```

#### API 응답 최적화
```python
# 응답 압축
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 캐싱 헤더
from fastapi import Response
response.headers["Cache-Control"] = "public, max-age=3600"
```

## 배포 가이드

### Docker 컨테이너화

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY decodeat/ ./decodeat/
COPY gcp-key.json .

# 환경 변수 설정
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["python", "-m", "decodeat.main"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  nutrition-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DEBUG=false
    volumes:
      - ./gcp-key.json:/app/gcp-key.json:ro
```

### 환경별 설정

#### 개발 환경
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
export HOST=127.0.0.1
export PORT=8000
```

#### 프로덕션 환경
```bash
export DEBUG=false
export LOG_LEVEL=INFO
export HOST=0.0.0.0
export PORT=8000
export WORKERS=4
```

## 모니터링 및 로깅

### 애플리케이션 메트릭

#### Prometheus 메트릭
```python
from prometheus_client import Counter, Histogram, generate_latest

# 요청 카운터
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])

# 응답 시간 히스토그램
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_DURATION.observe(duration)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    
    return response
```

#### 헬스체크 엔드포인트
```python
@app.get("/health")
async def health_check():
    """상세한 헬스체크."""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.api_version,
        "services": {
            "gemini_ai": await check_gemini_connection(),
            "google_vision": await check_vision_connection(),
        }
    }
    return checks
```

### 로그 집계

#### ELK Stack 연동
```python
import json
import logging
from pythonjsonlogger import jsonlogger

# JSON 로거 설정
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

## 보안 가이드

### API 키 관리

#### 환경 변수 사용
```python
import os
from typing import Optional

def get_api_key(key_name: str) -> Optional[str]:
    """안전하게 API 키를 가져옵니다."""
    key = os.getenv(key_name)
    if not key:
        raise ValueError(f"Required API key {key_name} not found")
    return key
```

#### 키 로테이션
```bash
# 정기적인 API 키 교체
# 1. 새 키 생성
# 2. 환경 변수 업데이트
# 3. 애플리케이션 재시작
# 4. 이전 키 비활성화
```

### 입력 검증

#### URL 검증 강화
```python
from urllib.parse import urlparse
import re

def validate_image_url(url: str) -> bool:
    """이미지 URL의 보안성을 검증합니다."""
    parsed = urlparse(url)
    
    # HTTPS 강제
    if parsed.scheme != 'https':
        return False
    
    # 허용된 도메인 확인
    allowed_domains = ['amazonaws.com', 'googleusercontent.com']
    if not any(domain in parsed.netloc for domain in allowed_domains):
        return False
    
    # 파일 확장자 확인
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if not any(url.lower().endswith(ext) for ext in allowed_extensions):
        return False
    
    return True
```

#### 요청 제한
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/analyze")
@limiter.limit("10/minute")
async def analyze_nutrition_label(request: Request, data: AnalyzeRequest):
    """분석 엔드포인트 (분당 10회 제한)."""
    pass
```

## 문제 해결

### 일반적인 문제들

#### 1. 메모리 부족
```python
# 이미지 크기 제한 강화
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB로 축소

# 스트리밍 처리 개선
async def download_with_memory_limit(url: str, max_size: int) -> bytes:
    """메모리 제한이 있는 다운로드."""
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', url) as response:
            content = BytesIO()
            total_size = 0
            
            async for chunk in response.aiter_bytes(chunk_size=1024):
                total_size += len(chunk)
                if total_size > max_size:
                    raise ValueError(f"File too large: {total_size} > {max_size}")
                content.write(chunk)
            
            return content.getvalue()
```

#### 2. API 응답 지연
```python
# 타임아웃 설정 최적화
TIMEOUTS = {
    'image_download': 30,
    'ocr_processing': 60,
    'ai_analysis': 45
}

# 병렬 처리 개선
async def process_images_parallel(urls: List[str]) -> List[str]:
    """이미지를 병렬로 처리합니다."""
    semaphore = asyncio.Semaphore(3)  # 동시 처리 제한
    
    async def process_single(url: str) -> str:
        async with semaphore:
            return await process_image(url)
    
    tasks = [process_single(url) for url in urls]
    return await asyncio.gather(*tasks)
```

#### 3. 외부 API 오류
```python
# 재시도 로직
import asyncio
from typing import Callable, Any

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    backoff_factor: float = 1.0
) -> Any:
    """지수 백오프를 사용한 재시도."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = backoff_factor * (2 ** attempt)
            await asyncio.sleep(wait_time)
```

이 개발 가이드는 프로젝트의 코딩 표준, 테스트 방법, 디버깅 기법, 성능 최적화 등을 포괄적으로 다룹니다.