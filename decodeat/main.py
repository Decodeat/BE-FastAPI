import os
import json
import uvicorn
from dotenv import load_dotenv

# FastAPI 관련 라이브러리
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Optional

# Google Cloud 관련 라이브러리
from google.cloud.vision import Image, ImageAnnotatorClient
import google.generativeai as genai

# ==============================================================================
# 1. 설정 및 초기화
# .env 파일의 환경변수 자동 로드
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))
# ==============================================================================

# FastAPI 앱 생성
app = FastAPI(
    title="Decodeat OCR & AI Parsing Server",
    description="가공식품 라벨 이미지를 분석하여 구조화된 영양 정보를 제공합니다."
)

# --- 인증 정보 설정 ---
try:
    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        print("경고: GOOGLE_APPLICATION_CREDENTIALS 환경 변수가 설정되지 않았습니다.")
        # 현재 파일 기준으로 gcp-key.json의 절대경로 지정
        key_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'gcp-key.json'))
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_path

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("오류: GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    genai.configure(api_key=gemini_api_key)

except Exception as e:
    print(f"인증 설정 중 오류 발생: {e}")

# ==============================================================================
# 2. 데이터 모델 정의 (Pydantic)
# ==============================================================================

class NutritionFact(BaseModel):
    name: str = Field(..., description="영양성분 이름", example="나트륨")
    value: float = Field(..., description="함량", example=55.0)
    unit: str = Field(..., description="단위", example="mg")
    # [수정됨] 1일 영양성분 기준치 비율 필드 추가 (Optional)
    daily_value_percentage: Optional[int] = Field(None, description="1일 영양성분 기준치에 대한 비율(%)", example=5)

class AnalysisResponse(BaseModel):
    ingredients: List[str] = Field(..., description="원재료명 리스트", example=["정제수", "백설탕"])
    nutrition_facts: List[NutritionFact] = Field(..., description="영양성분 리스트")

# ==============================================================================
# 3. 핵심 로직 함수
# ==============================================================================

def detect_text_from_image_sync(image_bytes: bytes) -> str:
    """[동기 함수] Cloud Vision API를 사용해 이미지에서 텍스트를 추출합니다."""
    client = ImageAnnotatorClient()
    image = Image(content=image_bytes)
    
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(f"Google Vision API Error: {response.error.message}")
    
    return response.text_annotations[0].description if response.text_annotations else ""

async def parse_text_with_gemini(ocr_text: str) -> dict:
    """Gemini AI를 사용해 텍스트를 구조화된 JSON으로 파싱합니다."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # [수정됨] 사용자가 제안한 더 정교한 프롬프트로 변경
    prompt = f"""
    당신은 대한민국의 가공식품 텍스트 분석 전문가입니다. 주어진 OCR 텍스트에서 '원재료명'과 '영양정보'를 추출하여 아래의 JSON 형식에 맞춰서 반환해주세요.
    결과에는 JSON 객체 외에 다른 어떤 설명이나 추가 텍스트도 포함하지 마세요.

    1.  **원재료명(ingredients)**: 원산지는 제외하고 함량이 표시된경우 원재료명에 함량을 포함해주세요. 원재료명에 이어 괄호안에 추가 원재료가 포함된 경우 'ex) 혼합분유(탈지분유, 유청분말)' 혼합분유, 탈지분유, 유청분말 이렇게 각각의 원재료명으로 반환해주세요. 또한 리스트에 중복 값이 있으면 안됩니다. 
    2.  **영양정보(nutrition_facts)**: 각 영양성분의 이름(name), 값(value), 단위(unit)를 추출해주세요. 값(value)은 반드시 숫자(float) 형태여야 합니다. 1일 영양성분 기준치에 대한 비율(%)도 `daily_value_percentage` 키를 사용하여 포함해주세요.

    **[ 출력 JSON 형식 ]**
    {{
      "ingredients": ["정제수", "백설탕", "혼합분유", "탈지분유", "유청분말"],
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
        response = await model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Gemini API 파싱 오류: {e}")
        raise HTTPException(status_code=500, detail="AI 모델이 유효한 JSON을 생성하지 못했습니다.")

# ==============================================================================
# 4. API 엔드포인트 정의
# ==============================================================================

@app.post("/analyze/image", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    이미지 파일을 업로드받아 OCR 및 AI 파싱을 수행하고,
    구조화된 영양 정보를 JSON 형태로 반환합니다.
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 비어있습니다.")

    try:
        # [수정됨] 안정적인 동기 함수를 별도 스레드에서 실행
        ocr_text = await run_in_threadpool(detect_text_from_image_sync, image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if not ocr_text.strip():
        raise HTTPException(status_code=422, detail="이미지에서 텍스트를 추출할 수 없습니다.")

    structured_data = await parse_text_with_gemini(ocr_text)
    
    return structured_data

# ==============================================================================
# 5. 서버 실행
# ==============================================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)