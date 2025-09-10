"""
AI Analysis Service for nutrition label analysis.
Provides structured nutrition information extraction using Gemini AI.
"""
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from decodeat.config import settings
from decodeat.api.models import NutritionInfo, DecodeStatus

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for analyzing nutrition information using Gemini AI."""
    
    def __init__(self):
        """Initialize the analysis service with Gemini AI."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for analysis service")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("AnalysisService initialized successfully")
    
    def _normalize_product_name(self, product_name: str) -> str:
        """
        Normalize product name by removing spaces and keeping only Korean/English/numbers.
        
        Implements requirement 4.3: Remove spaces and keep only Korean/English/numbers.
        
        Args:
            product_name: Raw product name from analysis
            
        Returns:
            str: Normalized product name
        """
        if not product_name:
            return ""
        
        # Remove all spaces and keep only Korean, English, and numbers
        normalized = re.sub(r'[^\w가-힣]', '', product_name)
        logger.debug(f"Normalized product name: '{product_name}' -> '{normalized}'")
        return normalized
    
    def _extract_nutrition_values(self, nutrition_data: Dict) -> NutritionInfo:
        """
        Extract nutrition values and remove units, keeping only number strings.
        
        Implements requirements 4.4 and 4.5: Remove units, return number strings, use null for missing values.
        
        Args:
            nutrition_data: Raw nutrition data from AI analysis
            
        Returns:
            NutritionInfo: Structured nutrition information
        """
        def extract_number(value) -> Optional[str]:
            """Extract number from value string, removing units."""
            if not value or value == "null" or value == "정보없음":
                return None
            
            # Convert to string if not already
            value_str = str(value).strip()
            
            # Extract numbers (including decimals) from the string
            number_match = re.search(r'(\d+(?:\.\d+)?)', value_str)
            if number_match:
                return number_match.group(1)
            
            return None
        
        # Map the nutrition data to NutritionInfo fields
        nutrition_info = NutritionInfo(
            calcium=extract_number(nutrition_data.get('calcium')),
            carbohydrate=extract_number(nutrition_data.get('carbohydrate')),
            cholesterol=extract_number(nutrition_data.get('cholesterol')),
            dietary_fiber=extract_number(nutrition_data.get('dietary_fiber')),
            energy=extract_number(nutrition_data.get('energy')),
            fat=extract_number(nutrition_data.get('fat')),
            protein=extract_number(nutrition_data.get('protein')),
            sat_fat=extract_number(nutrition_data.get('sat_fat')),
            sodium=extract_number(nutrition_data.get('sodium')),
            sugar=extract_number(nutrition_data.get('sugar')),
            trans_fat=extract_number(nutrition_data.get('trans_fat'))
        )
        
        logger.debug(f"Extracted nutrition values: {nutrition_info}")
        return nutrition_info
    
    def _parse_ingredients(self, ingredients_text: str) -> Optional[List[str]]:
        """
        Parse ingredients text into a list of individual ingredients.
        
        Args:
            ingredients_text: Raw ingredients text from analysis
            
        Returns:
            List[str]: List of individual ingredients, or None if no ingredients found
        """
        if not ingredients_text or ingredients_text == "정보없음":
            return None
        
        # Split by common delimiters and clean up
        ingredients = re.split(r'[,，、]', ingredients_text)
        ingredients = [ingredient.strip() for ingredient in ingredients if ingredient.strip()]
        
        # Remove empty strings and common non-ingredient text
        ingredients = [
            ing for ing in ingredients 
            if ing and ing not in ['등', '기타', '정보없음', 'null']
        ]
        
        return ingredients if ingredients else None
    
    async def analyze_nutrition_info(self, text: str) -> Dict:
        """
        Analyze nutrition information from extracted text using Gemini AI.
        
        Implements requirements:
        - 4.1: Send extracted text to Gemini AI for analysis
        - 4.2: Extract product name, nutrition info, and ingredients
        - 4.3: Normalize product name
        - 4.4: Extract nutrition values as number strings without units
        - 4.5: Use null values for missing nutrition information
        
        Args:
            text: OCR extracted text from validated images
            
        Returns:
            Dict: Analysis result with decodeStatus, product_name, nutrition_info, ingredients, and message
            
        Raises:
            Exception: If analysis fails due to API errors
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for nutrition analysis")
            return {
                "decodeStatus": DecodeStatus.FAILED,
                "product_name": None,
                "nutrition_info": None,
                "ingredients": None,
                "message": "No text provided for analysis"
            }
        
        # Create detailed prompt for nutrition analysis matching Spring DB structure
        prompt = f"""
        당신은 대한민국의 식품 라벨 분석 전문가입니다. 
        주어진 텍스트에서 영양성분 정보를 추출하여 JSON 형식으로 반환해주세요.
        
        다음 형식으로 정확히 반환해주세요:
        {{
            "analysis_quality": "high|medium|low",
            "product_name": "제품명 (브랜드명 제외, 제품명만)",
            "nutrition_info": {{
                "energy": "칼로리 수치만 (단위 제거)",
                "carbohydrate": "탄수화물 수치만 (단위 제거)",
                "sugar": "당류 수치만 (단위 제거)",
                "dietary_fiber": "식이섬유 수치만 (단위 제거)",
                "protein": "단백질 수치만 (단위 제거)",
                "fat": "지방 수치만 (단위 제거)",
                "sat_fat": "포화지방 수치만 (단위 제거)",
                "trans_fat": "트랜스지방 수치만 (단위 제거)",
                "cholesterol": "콜레스테롤 수치만 (단위 제거)",
                "sodium": "나트륨 수치만 (단위 제거)",
                "calcium": "칼슘 수치만 (단위 제거)"
            }},
            "ingredients": "원재료명 전체 텍스트 (쉼표로 구분된 형태)"
        }}
        
        중요한 규칙:
        1. 수치는 숫자만 추출하고 단위(g, mg, kcal 등)는 제거
        2. 정보가 없는 항목은 "정보없음"으로 표시
        3. analysis_quality는 다음 기준으로 판단:
           - high: 대부분의 영양성분 정보가 명확하게 추출 가능
           - medium: 일부 영양성분 정보가 불분명하거나 누락
           - low: 텍스트가 흐리거나 대부분의 정보 추출 불가
        4. 제품명은 브랜드명을 제외하고 실제 제품명만 추출
        5. 원재료명은 전체 텍스트를 그대로 반환 (후처리에서 분리)
        
        분석할 텍스트:
        ---
        {text}
        ---
        
        JSON 응답만 반환하고 다른 설명은 포함하지 마세요.
        """
        
        try:
            logger.debug(f"Analyzing nutrition info with text length: {len(text)}")
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()
            
            # Parse JSON response (handle markdown code blocks)
            try:
                # Remove markdown code blocks if present
                clean_response = response_text.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]  # Remove ```json
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]  # Remove ```
                clean_response = clean_response.strip()
                
                analysis_result = json.loads(clean_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                return {
                    "decodeStatus": DecodeStatus.FAILED,
                    "product_name": None,
                    "nutrition_info": None,
                    "ingredients": None,
                    "message": "Failed to parse analysis response"
                }
            
            # Determine decode status based on analysis quality
            analysis_quality = analysis_result.get('analysis_quality', 'low')
            if analysis_quality == 'low':
                decode_status = DecodeStatus.FAILED
                message = "Image quality too low for accurate analysis"
            elif analysis_quality == 'medium':
                decode_status = DecodeStatus.COMPLETED
                message = "Analysis completed with some missing information"
            else:  # high quality
                decode_status = DecodeStatus.COMPLETED
                message = "Analysis completed successfully"
            
            # Extract and normalize product name
            raw_product_name = analysis_result.get('product_name', '')
            normalized_product_name = self._normalize_product_name(raw_product_name) if raw_product_name != "정보없음" else None
            
            # Extract nutrition information
            nutrition_data = analysis_result.get('nutrition_info', {})
            nutrition_info = self._extract_nutrition_values(nutrition_data)
            
            # Parse ingredients
            ingredients_text = analysis_result.get('ingredients', '')
            ingredients = self._parse_ingredients(ingredients_text) if ingredients_text != "정보없음" else None
            
            result = {
                "decodeStatus": decode_status,
                "product_name": normalized_product_name,
                "nutrition_info": nutrition_info,
                "ingredients": ingredients,
                "message": message
            }
            
            logger.info(f"Nutrition analysis completed with status: {decode_status}")
            logger.debug(f"Analysis result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during nutrition analysis: {e}")
            raise Exception(f"Nutrition analysis failed: {str(e)}")