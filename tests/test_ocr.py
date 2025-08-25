import os
import json
from google.cloud import vision
import google.generativeai as genai

# --- 1. 인증 설정 ---
# Cloud Vision API를 위한 서비스 계정 키 설정
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'gcp-key.json'
GEMINI_API_KEY = "AIzaSyBryq5KrYjkCB9k4WbdUYFYHN5Mk-Q59C8" 
genai.configure(api_key=GEMINI_API_KEY)


# --- 2. OCR 기능 함수 ---
def detect_text_from_image(path: str) -> str:
    """이미지 파일에서 텍스트를 감지하여 문자열로 반환합니다."""
    print("--- [1단계] Cloud Vision API로 OCR 실행 중... ---")
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise Exception(response.error.message)
    
    # 감지된 전체 텍스트를 반환
    return response.text_annotations[0].description


# --- 3. AI 파싱 기능 함수 ---
def parse_text_with_gemini(ocr_text: str) -> dict:
    """Gemini AI를 사용해 텍스트를 구조화된 JSON으로 파싱합니다."""
    print("--- [2단계] Vertex AI (Gemini) API로 전처리 실행 중... ---")
    
    # Gemini 모델 선택 (Flash 모델이 빠르고 저렴)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # AI에게 내릴 자세한 지침 (프롬프트)
    prompt = f"""
    당신은 대한민국의 가공식품 텍스트 분석 전문가입니다. 주어진 OCR 텍스트에서 '원재료명'과 '영양정보'를 추출하여 아래의 JSON 형식에 맞춰서 반환해주세요.
    결과에는 JSON 객체 외에 다른 어떤 설명이나 추가 텍스트도 포함하지 마세요.

    1.  **원재료명(ingredients)**: 원산지는 제외하고 함량이 표시된경우 원재료명에 함량을 포함해주세요. 원재료명에 이어 괄호안에 추가 원재료가 포함된 경우 'ex) 혼합분유(탈지분유, 유청분말)' 혼합분유, 탈지분유, 유청분말 이렇게 각각의 원재료명으로 반환해주세요. 또한 리스트에 중복 값이 있으면 안됩니다. 
    2.  **영양정보(nutrition_facts)**: 각 영양성분의 이름(name), 값(value), 단위(unit)를 추출해주세요. 값(value)은 반드시 숫자(float) 형태여야 합니다. 1일 영양성분 기준치에 대한 비율(%)도 포함해주세요.

    **[ 출력 JSON 형식 ]**
    {{
      "ingredients": ["정제수", "백설탕", "혼합분유(탈지분유, 유청분말)"],
      "nutrition_facts": [
        {{"name": "나트륨", "value": 55, "unit": "mg", "daily_value_percentage": 2}},
        {{"name": "탄수화물", "value": 20, "unit": "g", "daily_value_percentage": 6}},
        {{"name": "단백질", "value": 3, "unit": "g", "daily_value_percentage": 5}}
      ]
    }}

    **[ 처리할 OCR 텍스트 ]**
    ---
    {ocr_text}
    ---
    """

    try:
        response = model.generate_content(prompt)
        # AI의 응답 텍스트에서 불필요한 마크다운 문법(```json ... ```)을 제거
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        # 문자열을 실제 JSON(Python 딕셔너리) 객체로 변환
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"  -> AI 파싱 중 오류가 발생했습니다: {e}")
        print(f"  -> AI 원본 응답: {response.text}")
        return None


# --- 4. 메인 실행 부분 ---
if __name__ == '__main__':
    image_path = 'test_image.jpg'
    
    # 1단계: 이미지에서 텍스트 추출
    raw_ocr_text = detect_text_from_image(image_path)
    print(f"--- OCR 결과 ---\n{raw_ocr_text}\n------------------\n")

    if raw_ocr_text:
        # 2단계: AI를 사용해 텍스트 파싱
        structured_data = parse_text_with_gemini(raw_ocr_text)

        if structured_data:
            print("--- [최종 결과] AI가 구조화한 데이터 ---")
            # 한국어가 깨지지 않고 예쁘게 출력
            print(json.dumps(structured_data, indent=2, ensure_ascii=False))