"""
Demonstration script for ValidationService functionality.
Shows how to use the AI validation service for single images and image pairs.
"""
import asyncio
import sys
import os

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from decodeat.services.validation_service import ValidationService


async def demo_single_image_validation():
    """Demonstrate single image validation functionality."""
    print("=== Single Image Validation Demo ===\n")
    
    validation_service = ValidationService()
    
    # Test with nutrition information
    nutrition_text = """
    영양성분 (1회 제공량 250ml당)
    열량 150kcal
    나트륨 55mg (3%)
    탄수화물 20g (6%)
    당류 18g (18%)
    지방 8g (15%)
    트랜스지방 0g
    포화지방 5g (33%)
    콜레스테롤 30mg (10%)
    단백질 3g (5%)
    """
    
    print("Testing with nutrition information:")
    print(f"Text: {nutrition_text[:100]}...")
    result = await validation_service.validate_single_image(nutrition_text)
    print(f"Validation result: {result}\n")
    
    # Test with ingredient information
    ingredient_text = """
    원재료명: 정제수, 백설탕, 혼합분유(탈지분유, 유청분말), 
    식물성유지(팜유, 코코넛유), 코코아분말, 바닐라향
    """
    
    print("Testing with ingredient information:")
    print(f"Text: {ingredient_text}")
    result = await validation_service.validate_single_image(ingredient_text)
    print(f"Validation result: {result}\n")
    
    # Test with irrelevant content
    irrelevant_text = """
    안녕하세요. 오늘 날씨가 좋네요.
    이것은 영양성분과 관련없는 텍스트입니다.
    """
    
    print("Testing with irrelevant content:")
    print(f"Text: {irrelevant_text}")
    result = await validation_service.validate_single_image(irrelevant_text)
    print(f"Validation result: {result}\n")


async def demo_image_pair_validation():
    """Demonstrate image pair validation functionality."""
    print("=== Image Pair Validation Demo ===\n")
    
    validation_service = ValidationService()
    
    # Test with same product
    text1 = """
    코카콜라 제로
    영양성분 (1회 제공량 250ml당)
    열량 0kcal
    나트륨 15mg (1%)
    탄수화물 0g
    당류 0g
    지방 0g
    단백질 0g
    """
    
    text2 = """
    코카콜라 제로
    원재료명: 정제수, 이산화탄소, 카라멜색소, 
    인산, 아스파탐, 아세설팜칼륨, 천연향료
    제조사: 한국코카콜라
    """
    
    print("Testing with same product (Coca-Cola Zero):")
    print(f"Text 1: {text1[:100]}...")
    print(f"Text 2: {text2[:100]}...")
    result = await validation_service.validate_image_pair(text1, text2)
    print(f"Validation result: {result}\n")
    
    # Test with different products
    text3 = """
    펩시콜라
    원재료명: 정제수, 이산화탄소, 설탕, 
    카라멜색소, 인산, 천연향료
    제조사: 롯데칠성음료
    """
    
    print("Testing with different products (Coca-Cola vs Pepsi):")
    print(f"Text 1: {text1[:100]}...")
    print(f"Text 3: {text3[:100]}...")
    result = await validation_service.validate_image_pair(text1, text3)
    print(f"Validation result: {result}\n")


async def main():
    """Run the validation service demonstration."""
    print("ValidationService Demonstration")
    print("=" * 50)
    
    try:
        await demo_single_image_validation()
        await demo_image_pair_validation()
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        print("Make sure GEMINI_API_KEY is set in your environment.")


if __name__ == "__main__":
    asyncio.run(main())