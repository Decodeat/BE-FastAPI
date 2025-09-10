#!/usr/bin/env python3
"""
API 테스트 예시 스크립트
"""
import requests
import json

# API 엔드포인트
BASE_URL = "http://localhost:8000"

def test_health():
    """헬스체크 테스트"""
    response = requests.get(f"{BASE_URL}/health")
    print("헬스체크:", response.json())

def test_analyze_single_image():
    """단일 이미지 분석 테스트"""
    data = {
        "image_urls": [
            "https://example.com/nutrition-label.jpg"
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/analyze", json=data)
    print("단일 이미지 분석:", response.json())

def test_analyze_dual_images():
    """이중 이미지 분석 테스트"""
    data = {
        "image_urls": [
            "https://example.com/nutrition-label.jpg",
            "https://example.com/ingredients-label.jpg"
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/analyze", json=data)
    print("이중 이미지 분석:", response.json())

if __name__ == "__main__":
    print("🧪 API 테스트 시작")
    print("서버가 실행 중인지 확인하세요: http://localhost:8000")
    print()
    
    try:
        test_health()
        # test_analyze_single_image()
        # test_analyze_dual_images()
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")