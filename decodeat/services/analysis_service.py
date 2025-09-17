"""
영양성분표 분석을 위한 AI 분석 서비스입니다.
Gemini AI를 사용하여 구조화된 영양 정보를 추출합니다.
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
    """Gemini AI를 사용하여 영양 정보를 분석하는 서비스입니다."""
    
    def __init__(self):
        """Gemini AI로 분석 서비스를 초기화합니다."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY는 분석 서비스에 필수입니다")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("AnalysisService가 성공적으로 초기화되었습니다")
    
    def _normalize_product_name(self, product_name: str) -> str:
        """
        공백을 제거하고 한글/영어/숫자만 남겨 제품명을 정규화합니다.
        
        요구사항 4.3 구현: 공백을 제거하고 한글/영어/숫자만 유지합니다.
        
        Args:
            product_name: 분석에서 얻은 원본 제품명
            
        Returns:
            str: 정규화된 제품명
        """
        if not product_name:
            return ""
        
        # 모든 공백을 제거하고 한글, 영어, 숫자만 유지합니다
        normalized = re.sub(r'[^\w가-힣]', '', product_name)
        logger.debug(f"제품명 정규화: '{product_name}' -> '{normalized}'")
        return normalized
    
    def _extract_nutrition_values(self, nutrition_data: Dict) -> NutritionInfo:
        """
        단위를 제거하고 숫자 문자열만 유지하여 영양성분 값을 추출합니다.
        
        요구사항 4.4 및 4.5 구현: 단위를 제거하고, 숫자 문자열을 반환하며, 누락된 값에는 null을 사용합니다.
        
        Args:
            nutrition_data: AI 분석에서 얻은 원본 영양 데이터
            
        Returns:
            NutritionInfo: 구조화된 영양 정보
        """
        def extract_number(value) -> Optional[str]:
            """값 문자열에서 단위를 제거하고 숫자만 추출합니다."""
            if not value or value == "null" or value == "정보없음":
                return None
            
            # 문자열이 아니면 문자열로 변환합니다
            value_str = str(value).strip()
            
            # 문자열에서 숫자(소수점 포함)를 추출합니다
            number_match = re.search(r'(\d+(?:\.\d+)?)', value_str)
            if number_match:
                return number_match.group(1)
            
            return None
        
        # 영양 데이터를 NutritionInfo 필드에 매핑합니다
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
        
        logger.debug(f"추출된 영양성분 값: {nutrition_info}")
        return nutrition_info
    
    def _parse_ingredients(self, ingredients_text: str) -> Optional[List[str]]:
        """
        원재료 텍스트를 파싱하여 개별 원재료 목록으로 만듭니다.
        
        Args:
            ingredients_text: 분석에서 얻은 원본 원재료 텍스트
            
        Returns:
            List[str]: 개별 원재료 목록. 원재료가 없으면 None을 반환합니다.
        """
        if not ingredients_text or ingredients_text == "정보없음":
            return None
        
        # 일반적인 구분자로 분리하고 정리합니다
        ingredients = re.split(r'[,，、]', ingredients_text)
        ingredients = [ingredient.strip() for ingredient in ingredients if ingredient.strip()]
        
        # 빈 문자열과 일반적인 비-원재료 텍스트를 제거합니다
        ingredients = [
            ing for ing in ingredients 
            if ing and ing not in ['등', '기타', '정보없음', 'null']
        ]
        
        return ingredients if ingredients else None
    
    async def analyze_nutrition_info(self, text: str) -> Dict:
        """
        Gemini AI를 사용하여 추출된 텍스트에서 영양 정보를 분석합니다.
        
        요구사항 구현:
        - 4.1: 추출된 텍스트를 Gemini AI로 보내 분석
        - 4.2: 제품명, 영양 정보, 원재료 추출
        - 4.3: 제품명 정규화
        - 4.4: 단위 없이 숫자 문자열로 영양성분 값 추출
        - 4.5: 누락된 영양 정보에 null 값 사용
        
        Args:
            text: 유효성이 검증된 이미지에서 OCR로 추출한 텍스트
            
        Returns:
            Dict: decodeStatus, product_name, nutrition_info, ingredients, message를 포함한 분석 결과
            
        Raises:
            Exception: API 오류로 분석이 실패할 경우
        """
        if not text or not text.strip():
            logger.warning("영양 정보 분석에 빈 텍스트가 제공되었습니다")
            return {
                "decodeStatus": DecodeStatus.FAILED,
                "product_name": None,
                "nutrition_info": None,
                "ingredients": None,
                "message": "분석할 텍스트가 제공되지 않았습니다"
            }
        
        # Spring DB 구조와 일치하는 영양 분석을 위한 상세 프롬프트를 생성합니다
        prompt = f"""
        ### 페르소나 (Persona)
        당신은 식품 영양 성분표를 분석하여 구조화된 데이터로 추출하는 매우 꼼꼼한 AI 전문가입니다. GOOGLE CLOUD VISION API OCR로 인식된 텍스트의 오류나 노이즈를 감안하여 가장 정확한 정보를 추출해야 합니다. ocr의 한계가 있다는 것을 알고, 당신이 직접 판단하여 누락된 정보나 잘못 인식된 부분을 보완할 수 있습니다.

        ### 지시 (Instruction)
        아래 OCR 텍스트에서 제품명, 영양 정보, 원재료명을 추출하고, 지정된 카테고리에 따라 원재료를 분류하여 최종 결과를 오직 JSON 형식으로만 반환하세요.

        ### 아래는 OCR로 추출한 식품 라벨의 전체 텍스트입니다.
        {text}
        ### 제약 조건 (Constraints)
        1.  **product_name**: 띄어쓰기를 모두 제거한 한글/영문/숫자만 포함된 문자열로 만드세요.
        2.  **nutrition_info**: 영양성분 값은 단위(g, mg, kcal 등)를 완벽히 제거하고 **숫자와 소수점자리가 포함된 문자열**로 추출하세요. 만약 해당하는 영양성분이 텍스트에 없으면, 값으로 `null`을 사용하세요.
        3.  원재료명 추출: '원재료명:' 다음에 나오는 모든 성분을 추출하여 리스트로 만드세요. 괄호 안의 원산지나 세부 정보는 제외하고 핵심 원재료명만 포함하세요.
        4. analysis_quality는 다음 기준으로 판단:
           - high: 대부분의 영양성분 정보가 명확하게 추출 가능
           - medium: 일부 영양성분 정보가 불분명하거나 누락
           - low: 텍스트가 흐리거나 대부분의 정보 추출 불가
        ### 예시 (Few-shot Example)
        #### 텍스트 입력 예시:
        "제품명: 돌아온 로켓단 초코롤 원재료명: 밀가루(밀:미국산), 백설탕, 전란액(계란:국산), 가공버터(우유), 쇼트닝(대두), 전지분유, 코코아분말, 합성향료 영양정보 총 내용량 85g 278kcal 나트륨 140mg 탄수화물 43g 당류 26g 지방 10g 포화지방 6g 단백질 4g
        ```json
        {{
            "product_name": "돌아온로켓단초코롤",
            "nutrition_info": {{
            "energy": "278",
            "carbohydrate": "140",
            "sugar": "43",
            "dietary_fiber": "26",
            "protein": "4",
            "fat": "10",
            "sat_fat": "10",
            "trans_fat": null,
            "cholesterol": "0.6",
            "sodium": null,
            "calcium": null,
        }},
        "ingredients": "밀가루", "백설탕", "전란액", "가공버터", "쇼트닝", "전지분유", "코코아분말", "합성향료"
        }}
        ```

        JSON 응답만 반환하고 다른 설명은 포함하지 마세요.
        """
        
        try:
            logger.debug(f"텍스트 길이 {len(text)}로 영양 정보 분석 중")
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()
            
            # JSON 응답을 파싱합니다 (마크다운 코드 블록 처리)
            try:
                # 마크다운 코드 블록이 있는 경우 제거합니다
                clean_response = response_text.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]  # ```json 제거
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]  # ``` 제거
                clean_response = clean_response.strip()
                
                analysis_result = json.loads(clean_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 응답 파싱 실패: {e}")
                logger.error(f"원본 응답: {response_text}")
                return {
                    "decodeStatus": DecodeStatus.FAILED,
                    "product_name": None,
                    "nutrition_info": None,
                    "ingredients": None,
                    "message": "분석 응답 파싱에 실패했습니다"
                }
            
            # 분석 품질에 따라 decode 상태를 결정합니다
            analysis_quality = analysis_result.get('analysis_quality', 'low')
            if analysis_quality == 'low':
                decode_status = DecodeStatus.FAILED
                message = "이미지 품질이 낮아 정확한 분석이 어렵습니다"
            elif analysis_quality == 'medium':
                decode_status = DecodeStatus.COMPLETED
                message = "일부 정보가 누락된 채로 분석이 완료되었습니다"
            else:  # 높은 품질
                decode_status = DecodeStatus.COMPLETED
                message = "분석이 성공적으로 완료되었습니다"
            
            # 제품명을 추출하고 정규화합니다
            raw_product_name = analysis_result.get('product_name', '')
            normalized_product_name = self._normalize_product_name(raw_product_name) if raw_product_name != "정보없음" else None
            
            # 영양 정보를 추출합니다
            nutrition_data = analysis_result.get('nutrition_info', {})
            nutrition_info = self._extract_nutrition_values(nutrition_data)
            
            # 원재료를 파싱합니다
            ingredients_text = analysis_result.get('ingredients', '')
            ingredients = self._parse_ingredients(ingredients_text) if ingredients_text != "정보없음" else None
            
            result = {
                "decodeStatus": decode_status,
                "product_name": normalized_product_name,
                "nutrition_info": nutrition_info,
                "ingredients": ingredients,
                "message": message
            }
            
            logger.info(f"영양 정보 분석 완료, 상태: {decode_status}")
            logger.debug(f"분석 결과: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"영양 정보 분석 중 오류 발생: {e}")
            raise Exception(f"영양 정보 분석 실패: {str(e)}")