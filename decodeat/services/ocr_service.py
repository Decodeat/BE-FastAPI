"""OCR service for extracting text from images using Google Cloud Vision API."""

import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from google.cloud.vision import Image, ImageAnnotatorClient
from google.cloud.exceptions import GoogleCloudError

from decodeat.utils.logging import LoggingService

logger = LoggingService(__name__)


class OCRService:
    """Service for extracting text from images using Google Cloud Vision API."""
    
    def __init__(self):
        """Initialize the OCR service."""
        self._client: Optional[ImageAnnotatorClient] = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ocr-worker")
    
    @property
    def client(self) -> ImageAnnotatorClient:
        """Get or create the Vision API client."""
        if self._client is None:
            try:
                self._client = ImageAnnotatorClient()
                logger.info("Google Cloud Vision API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud Vision API client: {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize Google Cloud Vision API client: {e}")
        return self._client
    
    async def extract_text(self, image_bytes: bytes) -> str:
        """
        Extract text from image using Google Cloud Vision API.
        
        Args:
            image_bytes: Raw image data as bytes
            
        Returns:
            str: Extracted text from the image
            
        Raises:
            ValueError: If image_bytes is empty or invalid
            RuntimeError: If Google Cloud Vision API fails
        """
        if not image_bytes:
            raise ValueError("Image bytes cannot be empty")
        
        logger.info(f"Starting text extraction from image ({len(image_bytes)} bytes)")
        
        try:
            # Run the synchronous Vision API call in a thread pool
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                self._executor,
                self._extract_text_sync,
                image_bytes
            )
            
            logger.info(f"Text extraction completed. Extracted {len(text)} characters")
            return text
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Vision API error: {e}", exc_info=True)
            raise RuntimeError(f"Google Cloud Vision API error: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {e}", exc_info=True)
            raise RuntimeError(f"Text extraction failed: {e}")
    
    def _extract_text_sync(self, image_bytes: bytes) -> str:
        """
        Synchronous text extraction using Google Cloud Vision API.
        
        Args:
            image_bytes: Raw image data as bytes
            
        Returns:
            str: Extracted text from the image
            
        Raises:
            GoogleCloudError: If Vision API request fails
            RuntimeError: If no text is detected or response is invalid
        """
        try:
            # Create Vision API image object
            image = Image(content=image_bytes)
            
            # Perform document text detection
            response = self.client.document_text_detection(image=image)
            
            # Check for API errors
            if response.error.message:
                raise GoogleCloudError(f"Vision API error: {response.error.message}")
            
            # Extract text from response
            if response.text_annotations:
                extracted_text = response.text_annotations[0].description
                if extracted_text:
                    return extracted_text.strip()
            
            # No text detected
            logger.warning("No text detected in the image")
            return ""
            
        except GoogleCloudError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to process image with Vision API: {e}")
    
    async def extract_text_from_multiple_images(self, images_bytes: list[bytes]) -> list[str]:
        """
        Extract text from multiple images concurrently.
        
        Args:
            images_bytes: List of raw image data as bytes
            
        Returns:
            list[str]: List of extracted text from each image
            
        Raises:
            ValueError: If images_bytes is empty or contains invalid data
            RuntimeError: If any Google Cloud Vision API call fails
        """
        if not images_bytes:
            raise ValueError("Images bytes list cannot be empty")
        
        logger.info(f"Starting text extraction from {len(images_bytes)} images")
        
        try:
            # Extract text from all images concurrently
            tasks = [self.extract_text(image_bytes) for image_bytes in images_bytes]
            results = await asyncio.gather(*tasks)
            
            logger.info(f"Successfully extracted text from {len(results)} images")
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract text from multiple images: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close the OCR service and clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("OCR service executor shutdown completed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()