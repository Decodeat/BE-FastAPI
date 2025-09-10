"""
AI Validation Service for nutrition label analysis.
Provides validation for single images and image pairs using Gemini AI.
"""
import json
import logging
from typing import Tuple
import google.generativeai as genai
from decodeat.config import settings

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating nutrition-related content using Gemini AI."""
    
    def __init__(self):
        """Initialize the validation service with Gemini AI."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for validation service")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("ValidationService initialized successfully")
    
    async def validate_single_image(self, text: str) -> bool:
        """
        Validate if a single image contains nutrition or ingredient information.
        
        Args:
            text: OCR extracted text from the image
            
        Returns:
            bool: True if the image contains relevant nutrition/ingredient information
            
        Raises:
            Exception: If validation fails due to API errors
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for single image validation")
            return False
        
        prompt = f"""
        당신은 대한민국의 식품 라벨 분석 전문가입니다. 
        주어진 텍스트가 식품의 영양성분표나 원재료명을 포함하고 있는지 판단해주세요.
        
        다음 중 하나라도 포함되어 있으면 "true"를 반환하고, 그렇지 않으면 "false"를 반환해주세요:
        1. 영양성분 정보 (칼로리, 나트륨, 탄수화물, 단백질, 지방, 당류, 식이섬유, 칼슘, 콜레스테롤, 포화지방, 트랜스지방 등)
        2. 원재료명 또는 성분 정보
        3. 영양성분 기준치 비율(%) 정보
        
        응답은 반드시 "true" 또는 "false"만 반환해주세요. 다른 설명은 포함하지 마세요.
        
        분석할 텍스트:
        ---
        {text}
        ---
        """
        
        try:
            logger.debug(f"Validating single image with text length: {len(text)}")
            response = await self.model.generate_content_async(prompt)
            result = response.text.strip().lower()
            
            is_valid = result == "true"
            logger.info(f"Single image validation result: {is_valid}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Error during single image validation: {e}")
            raise Exception(f"Validation failed: {str(e)}")
    
    async def validate_image_pair(self, text1: str, text2: str) -> bool:
        """
        Validate if two images belong to the same food product.
        
        Args:
            text1: OCR extracted text from the first image
            text2: OCR extracted text from the second image
            
        Returns:
            bool: True if both images belong to the same product
            
        Raises:
            Exception: If validation fails due to API errors
        """
        if not text1 or not text1.strip() or not text2 or not text2.strip():
            logger.warning("Empty text provided for image pair validation")
            return False
        
        prompt = f"""
        당신은 대한민국의 식품 라벨 분석 전문가입니다.
        두 개의 텍스트가 동일한 식품 제품에서 추출된 것인지 판단해주세요.
        
        다음 기준으로 판단해주세요:
        1. 제품명이 동일하거나 유사한가?
        2. 브랜드명이 동일한가?
        3. 제조사 정보가 일치하는가?
        4. 하나는 영양성분표, 다른 하나는 원재료명 정보를 포함하고 있는가?
        5. 전체적인 제품 정보가 일관성이 있는가?
        
        두 텍스트가 동일한 제품에서 추출된 것으로 판단되면 "true"를, 
        서로 다른 제품으로 판단되면 "false"를 반환해주세요.
        
        응답은 반드시 "true" 또는 "false"만 반환해주세요. 다른 설명은 포함하지 마세요.
        
        첫 번째 이미지 텍스트:
        ---
        {text1}
        ---
        
        두 번째 이미지 텍스트:
        ---
        {text2}
        ---
        """
        
        try:
            logger.debug(f"Validating image pair with text lengths: {len(text1)}, {len(text2)}")
            response = await self.model.generate_content_async(prompt)
            result = response.text.strip().lower()
            
            is_valid = result == "true"
            logger.info(f"Image pair validation result: {is_valid}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Error during image pair validation: {e}")
            raise Exception(f"Image pair validation failed: {str(e)}")