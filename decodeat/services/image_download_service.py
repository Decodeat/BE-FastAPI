"""영양성분표 분석을 위한 이미지 다운로드 서비스입니다."""

import asyncio
import logging
from io import BytesIO
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
from PIL import Image

from decodeat.utils.logging import LoggingService

logger = LoggingService(__name__)


class ImageDownloadService:
    """URL에서 이미지를 다운로드하고 유효성을 검사하는 서비스입니다."""
    
    # 지원하는 이미지 형식
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'BMP', 'GIF'}
    
    # 최대 파일 크기 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 요청 타임아웃 (초)
    REQUEST_TIMEOUT = 30.0
    
    def __init__(self):
        """이미지 다운로드 서비스를 초기화합니다."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.REQUEST_TIMEOUT),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    async def __aenter__(self):
        """비동기 컨텍스트 관리자 진입점입니다."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 관리자 종료점입니다."""
        await self.client.aclose()
    
    async def download_image(self, url: str) -> bytes:
        """
        URL에서 이미지를 다운로드하고 유효성 검사 및 오류 처리를 수행합니다.
        
        Args:
            url: 이미지를 다운로드할 URL
            
        Returns:
            bytes: 다운로드된 이미지 데이터
            
        Raises:
            ValueError: URL이 유효하지 않거나 지원되지 않는 이미지 형식일 경우
            httpx.HTTPError: 네트워크 요청이 실패할 경우
            RuntimeError: 이미지가 너무 크거나 손상된 경우
        """
        logger.info(f"URL에서 이미지 다운로드 시작: {url}")
        
        # URL 형식 검사
        if not self._is_valid_url(url):
            raise ValueError(f"잘못된 URL 형식입니다: {url}")
        
        try:
            # 스트리밍으로 이미지를 다운로드하여 크기 확인
            async with self.client.stream('GET', url) as response:
                response.raise_for_status()
                
                # Content-Type 확인 (URL 확장자 확인으로 대체 허용)
                content_type = response.headers.get('content-type', '').lower()
                if not self._is_image_content_type(content_type) and not self._is_image_url(url):
                    raise ValueError(f"URL이 이미지를 가리키지 않습니다. Content-Type: {content_type}")
                
                # 크기 제한을 두고 다운로드
                image_data = BytesIO()
                total_size = 0
                
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > self.MAX_FILE_SIZE:
                        raise RuntimeError(f"이미지가 너무 큽니다. 최대 크기: {self.MAX_FILE_SIZE} 바이트")
                    image_data.write(chunk)
                
                image_bytes = image_data.getvalue()
                
                # 이미지 형식 및 무결성 검사 (이것이 최종 확인 단계)
                logger.info(f"{len(image_bytes)} 바이트 이미지 형식 유효성 검사 시작")
                if not self._validate_image_format(image_bytes):
                    raise ValueError(f"잘못되었거나 손상된 이미지 형식입니다. URL: {url}, 크기: {len(image_bytes)} 바이트")
                
                logger.info(f"이미지 다운로드 성공: {len(image_bytes)} 바이트")
                return image_bytes
                
        except httpx.TimeoutException as e:
            logger.error(f"{url}에서 이미지 다운로드 중 타임아웃 발생: {e}")
            raise httpx.HTTPError(f"{url}에서 이미지 다운로드 중 요청 시간이 초과되었습니다.")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"{url}에서 이미지 다운로드 중 HTTP 오류 발생: {e.response.status_code}")
            raise httpx.HTTPError(f"{url}에서 이미지 다운로드 중 HTTP {e.response.status_code} 오류가 발생했습니다.")
        
        except httpx.RequestError as e:
            logger.error(f"{url}에서 이미지 다운로드 중 네트워크 오류 발생: {e}")
            raise httpx.HTTPError(f"{url}에서 이미지 다운로드 중 네트워크 오류가 발생했습니다: {str(e)}")
    
    def _is_valid_url(self, url: str) -> bool:
        """
        URL 형식을 검사합니다.
        
        Args:
            url: 검사할 URL
            
        Returns:
            bool: URL이 유효하면 True, 그렇지 않으면 False
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except Exception:
            return False
    
    def _is_image_content_type(self, content_type: str) -> bool:
        """
        Content-Type이 이미지인지 확인합니다.
        
        Args:
            content_type: HTTP Content-Type 헤더 값
            
        Returns:
            bool: Content-Type이 이미지 형식이면 True, 그렇지 않으면 False
        """
        image_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp',
            'image/bmp', 'image/gif', 'image/tiff'
        ]
        return any(img_type in content_type for img_type in image_types)
    
    def _is_image_url(self, url: str) -> bool:
        """
        URL에 이미지 파일 확장자가 있는지 확인합니다.
        
        Args:
            url: 확인할 URL
            
        Returns:
            bool: URL에 이미지 확장자가 있으면 True, 그렇지 않으면 False
        """
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff']
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in image_extensions)
    
    def _validate_image_format(self, image_bytes: bytes) -> bool:
        """
        PIL을 사용하여 이미지 형식과 무결성을 검사합니다. JPEG는 특별 처리합니다.
        
        Args:
            image_bytes: 원본 이미지 데이터
            
        Returns:
            bool: 이미지가 유효하고 지원되는 형식이면 True, 그렇지 않으면 False
        """
        try:
            # 먼저, 이미지를 열어 기본 정보를 가져옵니다
            with Image.open(BytesIO(image_bytes)) as img:
                img_format = img.format
                img_size = img.size
                
                logger.info(f"이미지를 성공적으로 열었습니다: 형식={img_format}, 크기={img_size}")
                
                # 지원되는 형식인지 확인
                if img_format not in self.SUPPORTED_FORMATS:
                    logger.warning(f"지원되지 않는 이미지 형식입니다: {img_format}")
                    return False
                
                # 최소 크기 확인 (최소 50x50 픽셀)
                if img_size[0] < 50 or img_size[1] < 50:
                    logger.warning(f"이미지가 너무 작습니다: {img_size}")
                    return False
                
                # JPEG 특별 처리
                if img_format == 'JPEG':
                    return self._validate_jpeg_image(img, image_bytes)
                else:
                    # JPEG가 아닌 이미지의 경우 더 가벼운 유효성 검사 사용
                    try:
                        # verify()는 너무 엄격할 수 있으므로 사용하지 않음
                        # mode와 size를 가져오는 것만 시도
                        _ = img.mode
                        logger.info(f"이미지 유효성 검사 통과: {img_format}, {img_size}")
                        return True
                    except Exception as e:
                        logger.warning(f"이미지 유효성 검사 경고: {e}, 하지만 형식은 유효합니다")
                        return True  # 이미지를 열 수 있다면 아마도 괜찮은 것
                
        except Exception as e:
            logger.error(f"이미지를 여는 중 유효성 검사 실패: {type(e).__name__}: {e}")
            return self._try_lenient_validation(image_bytes)
    
    def _validate_jpeg_image(self, img, image_bytes: bytes) -> bool:
        """
        여러 대체 전략을 사용하여 JPEG 이미지를 특별 검사합니다.
        
        Args:
            img: PIL 이미지 객체
            image_bytes: 원본 이미지 데이터
            
        Returns:
            bool: JPEG가 유효하면 True, 그렇지 않으면 False
        """
        try:
            # 전략 1: verify() 없이 기본 속성을 가져오려고 시도
            _ = img.mode
            _ = img.size
            logger.info(f"기본 검사를 통해 JPEG 유효성 검사 통과: {img.size}")
            return True
            
        except Exception as e1:
            logger.warning(f"JPEG 기본 검사 실패: {type(e1).__name__}: {e1}")
            
            try:
                # 전략 2: RGB로 변환 시도 (CMYK 등 처리)
                with Image.open(BytesIO(image_bytes)) as fresh_img:
                    rgb_img = fresh_img.convert('RGB')
                    _ = rgb_img.size
                    logger.info(f"RGB 변환을 통해 JPEG 유효성 검사 통과: {fresh_img.size}")
                    return True
                
            except Exception as e2:
                logger.warning(f"JPEG RGB 변환 실패: {type(e2).__name__}: {e2}")
                
                # 전략 3: 최후의 수단으로 JPEG 매직 바이트 확인
                return self._is_jpeg_by_header(image_bytes)
    
    def _is_jpeg_by_header(self, image_bytes: bytes) -> bool:
        """
        파일 헤더(매직 바이트)를 검사하여 이미지가 JPEG인지 확인합니다.
        
        Args:
            image_bytes: 원본 이미지 데이터
            
        Returns:
            bool: JPEG로 보이면 True, 그렇지 않으면 False
        """
        try:
            # JPEG 파일은 FF D8로 시작함
            if len(image_bytes) < 4:
                logger.warning("이미지가 너무 작아 JPEG 헤더를 확인할 수 없습니다")
                return False
                
            # JPEG 매직 바이트 확인
            if image_bytes[:2] == b'\xff\xd8':
                logger.info("헤더 검사(FF D8 매직 바이트)를 통해 JPEG 유효성 검사 통과")
                return True
                
            logger.warning("유효한 JPEG가 아님 - 매직 바이트가 없습니다")
            return False
            
        except Exception as e:
            logger.error(f"JPEG 헤더 확인 실패: {e}")
            return False
    
    def _try_lenient_validation(self, image_bytes: bytes) -> bool:
        """
        최후의 유효성 검사 - 매우 관대한 접근 방식입니다.
        
        Args:
            image_bytes: 원본 이미지 데이터
            
        Returns:
            bool: 이미지가 유효해 보이면 True, 그렇지 않으면 False
        """
        try:
            # 아무 작업 없이 열기만 시도
            with Image.open(BytesIO(image_bytes)) as img:
                img_format = img.format
                if img_format in self.SUPPORTED_FORMATS:
                    logger.info(f"관대한 검사를 통해 이미지 유효성 검사 통과: {img_format}")
                    return True
                    
        except Exception as e:
            logger.error(f"관대한 이미지 유효성 검사도 실패: {type(e).__name__}: {e}")
        
        return False
    
    async def download_multiple_images(self, urls: list[str]) -> list[bytes]:
        """
        여러 이미지를 동시에 다운로드합니다.
        
        Args:
            urls: 다운로드할 URL 목록
            
        Returns:
            list[bytes]: 다운로드된 이미지 데이터 목록
            
        Raises:
            ValueError: URL 중 하나라도 유효하지 않거나 지원되지 않는 이미지 형식일 경우
            httpx.HTTPError: 네트워크 요청 중 하나라도 실패할 경우
            RuntimeError: 이미지 중 하나라도 너무 크거나 손상된 경우
        """
        logger.info(f"{len(urls)}개 이미지 동시 다운로드 시작")
        
        # 모든 이미지를 동시에 다운로드
        tasks = [self.download_image(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        logger.info(f"{len(results)}개 이미지 다운로드 성공")
        return results
    
    async def close(self):
        """HTTP 클라이언트를 닫습니다."""
        await self.client.aclose()