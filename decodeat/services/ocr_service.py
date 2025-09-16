"""Google Cloud Vision API를 사용하여 이미지에서 텍스트를 추출하는 OCR 서비스입니다."""

import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from google.cloud.vision import Image, ImageAnnotatorClient
from google.cloud.exceptions import GoogleCloudError

from decodeat.utils.logging import LoggingService

logger = LoggingService(__name__)


class OCRService:
    """Google Cloud Vision API를 사용하여 이미지에서 텍스트를 추출하는 서비스입니다."""
    
    def __init__(self):
        """OCR 서비스를 초기화합니다."""
        self._client: Optional[ImageAnnotatorClient] = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ocr-worker")
    
    @property
    def client(self) -> ImageAnnotatorClient:
        """Vision API 클라이언트를 가져오거나 생성합니다."""
        if self._client is None:
            try:
                self._client = ImageAnnotatorClient()
                logger.info("Google Cloud Vision API 클라이언트가 성공적으로 초기화되었습니다")
            except Exception as e:
                logger.error(f"Google Cloud Vision API 클라이언트 초기화 실패: {e}", exc_info=True)
                raise RuntimeError(f"Google Cloud Vision API 클라이언트 초기화 실패: {e}")
        return self._client
    
    async def extract_text(self, image_bytes: bytes) -> str:
        """
        Google Cloud Vision API를 사용하여 이미지에서 텍스트를 추출합니다.
        
        Args:
            image_bytes: 바이트 형식의 원본 이미지 데이터
            
        Returns:
            str: 이미지에서 추출된 텍스트
            
        Raises:
            ValueError: image_bytes가 비어 있거나 유효하지 않은 경우
            RuntimeError: Google Cloud Vision API 호출이 실패하는 경우
        """
        if not image_bytes:
            raise ValueError("이미지 바이트는 비어 있을 수 없습니다")
        
        logger.info(f"이미지({len(image_bytes)} 바이트)에서 텍스트 추출 시작")
        
        try:
            # 동기적인 Vision API 호출을 스레드 풀에서 실행합니다
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                self._executor,
                self._extract_text_sync,
                image_bytes
            )
            
            logger.info(f"텍스트 추출 완료. {len(text)}자 추출됨")
            return text
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Vision API 오류: {e}", exc_info=True)
            raise RuntimeError(f"Google Cloud Vision API 오류: {e}")
        
        except Exception as e:
            logger.error(f"텍스트 추출 중 예기치 않은 오류 발생: {e}", exc_info=True)
            raise RuntimeError(f"텍스트 추출 실패: {e}")
    
    def _extract_text_sync(self, image_bytes: bytes) -> str:
        """
        Google Cloud Vision API를 사용하는 동기 방식 텍스트 추출 메서드입니다.
        
        Args:
            image_bytes: 바이트 형식의 원본 이미지 데이터
            
        Returns:
            str: 이미지에서 추출된 텍스트
            
        Raises:
            GoogleCloudError: Vision API 요청이 실패하는 경우
            RuntimeError: 텍스트가 감지되지 않거나 응답이 유효하지 않은 경우
        """
        try:
            # Vision API 이미지 객체를 생성합니다
            image = Image(content=image_bytes)
            
            # 문서 텍스트 감지를 수행합니다
            response = self.client.document_text_detection(image=image)
            
            # API 오류를 확인합니다
            if response.error.message:
                raise GoogleCloudError(f"Vision API 오류: {response.error.message}")
            
            # 응답에서 텍스트를 추출합니다
            if response.text_annotations:
                extracted_text = response.text_annotations[0].description
                if extracted_text:
                    return extracted_text.strip()
            
            # 텍스트가 감지되지 않았습니다
            logger.warning("이미지에서 텍스트가 감지되지 않았습니다")
            return ""
            
        except GoogleCloudError:
            raise
        except Exception as e:
            raise RuntimeError(f"Vision API로 이미지 처리 실패: {e}")
    
    async def extract_text_from_multiple_images(self, images_bytes: list[bytes]) -> list[str]:
        """
        여러 이미지에서 동시에 텍스트를 추출합니다.
        
        Args:
            images_bytes: 바이트 형식의 원본 이미지 데이터 목록
            
        Returns:
            list[str]: 각 이미지에서 추출된 텍스트 목록
            
        Raises:
            ValueError: images_bytes가 비어 있거나 유효하지 않은 데이터를 포함하는 경우
            RuntimeError: Google Cloud Vision API 호출 중 하나라도 실패하는 경우
        """
        if not images_bytes:
            raise ValueError("이미지 바이트 목록은 비어 있을 수 없습니다")
        
        logger.info(f"{len(images_bytes)}개 이미지에서 텍스트 추출 시작")
        
        try:
            # 모든 이미지에서 동시에 텍스트를 추출합니다
            tasks = [self.extract_text(image_bytes) for image_bytes in images_bytes]
            results = await asyncio.gather(*tasks)
            
            logger.info(f"{len(results)}개 이미지에서 텍스트 추출 성공")
            return results
            
        except Exception as e:
            logger.error(f"여러 이미지에서 텍스트 추출 실패: {e}", exc_info=True)
            raise
    
    async def close(self):
        """OCR 서비스를 닫고 리소스를 정리합니다."""
        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("OCR 서비스 실행기 종료 완료")
    
    async def __aenter__(self):
        """비동기 컨텍스트 관리자 진입점입니다."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 관리자 종료점입니다."""
        await self.close()