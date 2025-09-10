#!/usr/bin/env python3
"""
전체 API 테스트 스크립트
"""
import requests
import json
import time

def test_api():
    base_url = "http://localhost:8000"
    
    print("🧪 Nutrition Label API 테스트 시작")
    print()
    
    # 1. 헬스체크
    print("1. 헬스체크 테스트...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   ✅ 상태: {response.status_code}")
        print(f"   📄 응답: {response.json()}")
    except Exception as e:
        print(f"   ❌ 헬스체크 실패: {e}")
        return
    
    print()
    
    # 2. API 테스트
    print("2. 영양성분 분석 API 테스트...")
    url = f"{base_url}/api/v1/analyze"
    data = {
        "image_urls": [
            "https://decodeat-bucket.s3.ap-northeast-2.amazonaws.com/products/info/3d9df61d-7fe6-4da1-a21f-daec48f5b92f_%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7+2025-09-04+155836.png"
        ]
    }
    
    print(f"   📤 요청 URL: {url}")
    print(f"   📤 요청 데이터: {json.dumps(data, ensure_ascii=False)}")
    print("   ⏳ 분석 중... (30-60초 소요)")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=data, timeout=120)
        end_time = time.time()
        
        print(f"   ⏱️  응답 시간: {end_time - start_time:.2f}초")
        print(f"   📊 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ 분석 성공!")
            print(f"   📄 응답:")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            
            # 결과 요약
            print()
            print("📋 분석 결과 요약:")
            print(f"   🔍 상태: {result.get('decodeStatus')}")
            print(f"   🏷️  제품명: {result.get('product_name')}")
            print(f"   💬 메시지: {result.get('message')}")
            
            if result.get('nutrition_info'):
                nutrition = result['nutrition_info']
                print(f"   🍎 영양정보:")
                print(f"      - 칼로리: {nutrition.get('energy')} kcal")
                print(f"      - 탄수화물: {nutrition.get('carbohydrate')} g")
                print(f"      - 단백질: {nutrition.get('protein')} g")
                print(f"      - 지방: {nutrition.get('fat')} g")
                print(f"      - 나트륨: {nutrition.get('sodium')} mg")
            
            if result.get('ingredients'):
                ingredients = result['ingredients']
                print(f"   🥄 원재료 ({len(ingredients)}개): {', '.join(ingredients[:5])}{'...' if len(ingredients) > 5 else ''}")
        else:
            print(f"   ❌ 분석 실패: {response.status_code}")
            print(f"   📄 오류 응답: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ❌ 요청 타임아웃 (120초 초과)")
    except Exception as e:
        print(f"   ❌ 요청 실패: {e}")

if __name__ == "__main__":
    test_api()