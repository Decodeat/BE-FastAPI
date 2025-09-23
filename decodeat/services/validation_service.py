"""
영양성분표 분석을 위한 AI 유효성 검사 서비스입니다.
Gemini AI를 사용하여 단일 이미지와 이미지 쌍에 대한 유효성 검사를 제공합니다.
"""
import json
import logging
from typing import Tuple
import cv2
import numpy as np
import google.generativeai as genai
from decodeat.config import settings

logger = logging.getLogger(__name__)


class ValidationService:
    """Gemini AI를 사용하여 영양 관련 콘텐츠의 유효성을 검사하는 서비스입니다."""
    
    def __init__(self):
        """Gemini AI로 유효성 검사 서비스를 초기화합니다."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY는 유효성 검사 서비스에 필수입니다")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("ValidationService가 성공적으로 초기화되었습니다")
    
    async def validate_single_image(self, text: str) -> bool:
        """
        단일 이미지에 영양 정보나 원재료 정보가 포함되어 있는지 확인합니다.
        
        Args:
            text: 이미지에서 OCR로 추출한 텍스트
            
        Returns:
            bool: 이미지에 관련 영양/원재료 정보가 포함되어 있으면 True
            
        Raises:
            Exception: API 오류로 인해 유효성 검사에 실패할 경우
        """
        if not text or not text.strip():
            logger.warning("단일 이미지 유효성 검사에 빈 텍스트가 제공되었습니다")
            return False
        
        prompt = f"""
        당신은 대한민국의 식품 라벨 분석 전문가입니다. 
        주어진 텍스트가 식품의 영양성분표나 원재료명을 포함하고 있는지 판단해주세요.
        
        다음 중 하나라도 포함되어 있으면 "true"를 반환하고, 그렇지 않으면 "false"를 반환해주세요:
        1. 영양성분 정보 (칼로리, 나트륨, 탄수화물, 단백질, 지방, 당류, 식이섬유, 칼슘, 콜레스테롤, 포화지방, 트랜스지방 등)
        2. 원재료명 또는 성분 정보
        3. 영양성분 기준치 비율(%) 정보
        4. 1회 제공량 및 총 내용량 정보
        5. 알레르기 유발 성분 정보
        6. 품목보고번호
        응답은 반드시 "true" 또는 "false"만 반환해주세요. 다른 설명은 포함하지 마세요.
        
        분석할 텍스트:
        ---
        {text}
        ---
        """
        
        try:
            logger.debug(f"텍스트 길이 {len(text)}로 단일 이미지 유효성 검사 중")
            response = await self.model.generate_content_async(prompt)
            result = response.text.strip().lower()
            
            is_valid = result == "true"
            logger.info(f"단일 이미지 유효성 검사 결과: {is_valid}")
            return is_valid
            
        except Exception as e:
            logger.error(f"단일 이미지 유효성 검사 중 오류 발생: {e}")
            raise Exception(f"유효성 검사 실패: {str(e)}")

    def are_images_color_similar(self, image_bytes_list: list[bytes], threshold: float = 0.8) -> bool:
        """
        두 이미지(bytes)의 색상 히스토그램을 직접 비교하여 유사한지 여부를 반환합니다.
        (이 메서드는 validate_image_pair 내부에서 호출됩니다.)
        """
        if len(image_bytes_list) != 2:
            return False
        
        histograms = []
        try:
            for image_bytes in image_bytes_list:
                np_arr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("이미지 데이터를 디코딩할 수 없습니다.")
            
                hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv_img], [0, 1], None, [180, 256], [0, 180, 0, 256])
                cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                histograms.append(hist)
        except Exception as e:
            logger.error(f"히스토그램 계산 중 오류: {e}")
            return False
        
        if len(histograms) != 2:
            return False

        similarity = cv2.compareHist(histograms[0], histograms[1], cv2.HISTCMP_CORREL)
        logger.info(f"계산된 색상 유사도: {similarity:.4f} (임계값: {threshold})")
        return similarity >= threshold
    

    async def validate_image_pair(self, text1: str, text2: str, image_bytes_list: list[bytes]) -> bool:
        """
        두 이미지가 동일한 식품에 속하는지 확인합니다.
        
        Args:
            text1: 첫 번째 이미지에서 OCR로 추출한 텍스트
            text2: 두 번째 이미지에서 OCR로 추출한 텍스트
            image_bytes_list: 두 이미지의 바이트 데이터 리스트

        Returns:
            bool: 두 이미지가 모두 동일한 제품에 속하면 True
            
        Raises:
            Exception: API 오류로 인해 유효성 검사에 실패할 경우
        """
        # --- 1차 확인: 텍스트 분석 ---
        # 텍스트가 비어있지 않을 때만 시도
        if text1 and text1.strip() and text2 and text2.strip():
            prompt = f"""
            당신은 대한민국의 식품 라벨 분석 전문가입니다.
            두 개의 텍스트가 동일한 식품 제품에서 추출된 것인지 판단해주세요.
            
            다음 기준으로 판단해주세요:
            아래 두 텍스트는 각각 다른 이미지에서 추출되었습니다.
            두 텍스트에 언급된 제품명, 제조사, 브랜드 등의 정보를 종합적으로 고려했을 때,
            두 텍스트가 동일한 하나의 식품 제품의 일부일 가능성이 높습니까?
            품목제조번호와 바코드를 비교하여 확인해주세요, 만약 없다면 이 지시는 무시하세요.
            두 사진에서 나온 동일한 단어가 있다면, true로 판단하는 데 참고하세요.
            'true' 또는 'false'로만 정확하게 답변해주세요.

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
                logger.debug(f"텍스트 길이 {len(text1)}, {len(text2)}로 이미지 쌍 유효성 검사 중")
                response = await self.model.generate_content_async(prompt)
                result = response.text.strip().lower()
                
                is_valid = result == "true"
                logger.info(f"1차(텍스트) 분석 결과: {is_valid}")
                
                # 텍스트 분석 결과가 'true'이면, 즉시 성공으로 판정하고 함수 종료
                if is_valid:
                    return True

            except Exception as e:
                logger.error(f"1차(텍스트) 분석 중 API 오류: {e}. 2차 분석으로 넘어갑니다.")
        else:
             logger.warning("이미지 쌍 유효성 검사에 빈 텍스트가 제공되었습니다")

        # 텍스트가 비어있거나, 분석 결과가 'false'이거나, API 오류가 발생하면 이 부분으로 넘어옴
        logger.warning("1차(텍스트) 분석 불일치 또는 실패. 2차(색상) 분석을 시도합니다.")

        # --- 2차 확인: 색상 분석 ---
        color_is_valid = self.are_images_color_similar(image_bytes_list)
        
        if color_is_valid:
            logger.info("✅ 판정 성공: 2차(색상) 분석에서 높은 유사도 확인.")
            return True
        else:
            logger.warning("❌ 최종 판정 실패: 2차(색상) 분석에서도 유사도가 낮음.")
            return False