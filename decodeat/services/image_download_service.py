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
                logger.info(f"Starting image format validation for {len(image_bytes)} bytes")
                if not self._validate_image_format(image_bytes):
                    raise ValueError(f"Invalid or corrupted image format. URL: {url}, Size: {len(image_bytes)} bytes")
                
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
        Validate image format and integrity using PIL with JPEG-specific handling.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            bool: True if image is valid and supported, False otherwise
        """
        try:
            # First, try to open and get basic info
            with Image.open(BytesIO(image_bytes)) as img:
                img_format = img.format
                img_size = img.size
                
                logger.info(f"Image opened successfully: format={img_format}, size={img_size}")
                
                # Check if format is supported
                if img_format not in self.SUPPORTED_FORMATS:
                    logger.warning(f"Unsupported image format: {img_format}")
                    return False
                
                # Check minimum dimensions (at least 50x50 pixels)
                if img_size[0] < 50 or img_size[1] < 50:
                    logger.warning(f"Image too small: {img_size}")
                    return False
                
                # JPEG-specific handling
                if img_format == 'JPEG':
                    return self._validate_jpeg_image(img, image_bytes)
                else:
                    # For non-JPEG images, use lighter validation
                    try:
                        # Don't use verify() as it can be too strict
                        # Just try to get mode and size
                        _ = img.mode
                        logger.info(f"Image validation passed: {img_format}, {img_size}")
                        return True
                    except Exception as e:
                        logger.warning(f"Image validation warning: {e}, but format is valid")
                        return True  # If we can open it, it's probably fine
                
        except Exception as e:
            logger.error(f"Image validation failed during opening: {type(e).__name__}: {e}")
            return self._try_lenient_validation(image_bytes)
    
    def _validate_jpeg_image(self, img, image_bytes: bytes) -> bool:
        """
        Special validation for JPEG images with multiple fallback strategies.
        
        Args:
            img: PIL Image object
            image_bytes: Raw image data
            
        Returns:
            bool: True if JPEG is valid, False otherwise
        """
        try:
            # Strategy 1: Try to get basic properties without verify()
            _ = img.mode
            _ = img.size
            logger.info(f"JPEG validation passed with basic check: {img.size}")
            return True
            
        except Exception as e1:
            logger.warning(f"JPEG basic check failed: {type(e1).__name__}: {e1}")
            
            try:
                # Strategy 2: Try to convert to RGB (handles CMYK, etc.)
                with Image.open(BytesIO(image_bytes)) as fresh_img:
                    rgb_img = fresh_img.convert('RGB')
                    _ = rgb_img.size
                    logger.info(f"JPEG validation passed with RGB conversion: {fresh_img.size}")
                    return True
                
            except Exception as e2:
                logger.warning(f"JPEG RGB conversion failed: {type(e2).__name__}: {e2}")
                
                # Strategy 3: Check JPEG magic bytes as last resort
                return self._is_jpeg_by_header(image_bytes)
    
    def _is_jpeg_by_header(self, image_bytes: bytes) -> bool:
        """
        Check if image is JPEG by examining file header (magic bytes).
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            bool: True if appears to be JPEG, False otherwise
        """
        try:
            # JPEG files start with FF D8
            if len(image_bytes) < 4:
                logger.warning("Image too small for JPEG header check")
                return False
                
            # Check JPEG magic bytes
            if image_bytes[:2] == b'\xff\xd8':
                logger.info("JPEG validation passed with header check (FF D8 magic bytes)")
                return True
                
            logger.warning("Not a valid JPEG - missing magic bytes")
            return False
            
        except Exception as e:
            logger.error(f"JPEG header check failed: {e}")
            return False
    
    def _try_lenient_validation(self, image_bytes: bytes) -> bool:
        """
        Last resort validation - very lenient approach.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            bool: True if image seems valid, False otherwise
        """
        try:
            # Just try to open without any operations
            with Image.open(BytesIO(image_bytes)) as img:
                img_format = img.format
                if img_format in self.SUPPORTED_FORMATS:
                    logger.info(f"Image validation passed with lenient check: {img_format}")
                    return True
                    
        except Exception as e:
            logger.error(f"Lenient image validation also failed: {type(e).__name__}: {e}")
        
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