#!/usr/bin/env python3
"""
서버 실행 스크립트
"""
import os
import sys

# 환경 변수 설정
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), 'gcp-key.json')

# 서버 실행
if __name__ == "__main__":
    from decodeat.main import app
    import uvicorn
    
    print("🚀 Nutrition Label API 서버 시작")
    print(f"📁 Google Cloud 인증 파일: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔍 헬스체크: http://localhost:8000/health")
    print("🎯 API 엔드포인트: http://localhost:8000/api/v1/analyze")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)