"""Image download service for nutrition label analysis."""

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
    """Service for downloading and validating images from URLs."""
    
    # Supported image formats
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'BMP', 'GIF'}
    
    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 30.0
    
    def __init__(self):
        """Initialize the image download service."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.REQUEST_TIMEOUT),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def download_image(self, url: str) -> bytes:
        """
        Download image from URL with validation and error handling.
        
        Args:
            url: The URL to download the image from
            
        Returns:
            bytes: The downloaded image data
            
        Raises:
            ValueError: If URL is invalid or image format is not supported
            httpx.HTTPError: If network request fails
            RuntimeError: If image is too large or corrupted
        """
        logger.info(f"Starting image download from URL: {url}")
        
        # Validate URL format
        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL format: {url}")
        
        try:
            # Download image with streaming to check size
            async with self.client.stream('GET', url) as response:
                response.raise_for_status()
                
                # Check content type (allow fallback to URL extension check)
                content_type = response.headers.get('content-type', '').lower()
                if not self._is_image_content_type(content_type) and not self._is_image_url(url):
                    raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")
                
                # Download with size limit
                image_data = BytesIO()
                total_size = 0
                
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > self.MAX_FILE_SIZE:
                        raise RuntimeError(f"Image too large. Maximum size: {self.MAX_FILE_SIZE} bytes")
                    image_data.write(chunk)
                
                image_bytes = image_data.getvalue()
                
                # Validate image format and integrity (this is the definitive check)
                if not self._validate_image_format(image_bytes):
                    raise ValueError("Invalid or corrupted image format")
                
                logger.info(f"Successfully downloaded image: {len(image_bytes)} bytes")
                return image_bytes
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout downloading image from {url}: {e}")
            raise httpx.HTTPError(f"Request timeout while downloading image from {url}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading image from {url}: {e.response.status_code}")
            raise httpx.HTTPError(f"HTTP {e.response.status_code} error downloading image from {url}")
        
        except httpx.RequestError as e:
            logger.error(f"Network error downloading image from {url}: {e}")
            raise httpx.HTTPError(f"Network error downloading image from {url}: {str(e)}")
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except Exception:
            return False
    
    def _is_image_content_type(self, content_type: str) -> bool:
        """
        Check if content type indicates an image.
        
        Args:
            content_type: HTTP Content-Type header value
            
        Returns:
            bool: True if content type is an image, False otherwise
        """
        image_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp',
            'image/bmp', 'image/gif', 'image/tiff'
        ]
        return any(img_type in content_type for img_type in image_types)
    
    def _is_image_url(self, url: str) -> bool:
        """
        Check if URL has an image file extension.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if URL has an image extension, False otherwise
        """
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff']
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in image_extensions)
    
    def _validate_image_format(self, image_bytes: bytes) -> bool:
        """
        Validate image format and integrity using PIL.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            bool: True if image is valid and supported, False otherwise
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # Verify the image can be loaded
                img.verify()
                
                # Check if format is supported
                if img.format not in self.SUPPORTED_FORMATS:
                    logger.warning(f"Unsupported image format: {img.format}")
                    return False
                
                # Check minimum dimensions (at least 50x50 pixels)
                if img.size[0] < 50 or img.size[1] < 50:
                    logger.warning(f"Image too small: {img.size}")
                    return False
                
                logger.info(f"Image validation passed: {img.format}, {img.size}")
                return True
                
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return False
    
    async def download_multiple_images(self, urls: list[str]) -> list[bytes]:
        """
        Download multiple images concurrently.
        
        Args:
            urls: List of URLs to download
            
        Returns:
            list[bytes]: List of downloaded image data
            
        Raises:
            ValueError: If any URL is invalid or image format is not supported
            httpx.HTTPError: If any network request fails
            RuntimeError: If any image is too large or corrupted
        """
        logger.info(f"Starting concurrent download of {len(urls)} images")
        
        # Download all images concurrently
        tasks = [self.download_image(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        logger.info(f"Successfully downloaded {len(results)} images")
        return results
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()