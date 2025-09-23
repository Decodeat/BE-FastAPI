"""
Pydantic models for API requests and responses.
Designed to match Spring server's database structure.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class DecodeStatus(str, Enum):
    """Decode status enum matching Spring Boot's DecodeStatus."""
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED" 
    FAILED = "FAILED"


class AnalyzeRequest(BaseModel):
    """Request model for nutrition label analysis.
    
    Implements requirement 1.1: Accept image URLs in JSON format.
    """
    
    image_urls: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=2,
        description="List of image URLs to analyze (1-2 images)",
        example=["https://example.com/nutrition-label.jpg"]
    )
    
    product_id: Optional[int] = Field(
        None,
        description="Product ID from Spring server for vector storage",
        example=12345
    )
    
    @validator('image_urls')
    def validate_image_urls(cls, v):
        """Validate that URLs are properly formatted."""
        for url in v:
            if not url.strip():
                raise ValueError("Image URL cannot be empty")
            if not (url.startswith('http://') or url.startswith('https://')):
                raise ValueError("Image URL must start with http:// or https://")
        return v


class NutritionInfo(BaseModel):
    """Nutrition information model matching Spring's ProductNutrition entity."""
    
    calcium: Optional[str] = Field(None, description="칼슘 (mg)")
    carbohydrate: Optional[str] = Field(None, description="탄수화물 (g)")
    cholesterol: Optional[str] = Field(None, description="콜레스테롤 (mg)")
    dietary_fiber: Optional[str] = Field(None, description="식이섬유 (g)")
    energy: Optional[str] = Field(None, description="칼로리 (kcal)")
    fat: Optional[str] = Field(None, description="지방 (g)")
    protein: Optional[str] = Field(None, description="단백질 (g)")
    sat_fat: Optional[str] = Field(None, description="포화지방 (g)")
    sodium: Optional[str] = Field(None, description="나트륨 (mg)")
    sugar: Optional[str] = Field(None, description="당류 (g)")
    trans_fat: Optional[str] = Field(None, description="트랜스지방 (g)")


class AnalyzeResponse(BaseModel):
    """Response model for nutrition label analysis.
    
    Implements requirements:
    - 4.6: Include decodeStatus field in properly formatted JSON
    - 4.7: decodeStatus "cancelled" for non-nutrition images  
    - 4.8: decodeStatus "failed" for blurry/incomplete images
    - 4.9: decodeStatus "completed" for successful analysis
    """
    
    decodeStatus: DecodeStatus = Field(
        ..., 
        description="Processing status: completed, cancelled, or failed",
        example="completed"
    )
    product_name: Optional[str] = Field(
        None, 
        description="Product name (normalized: spaces removed, Korean/English/numbers only)",
        example="오리온초코파이"
    )
    nutrition_info: Optional[NutritionInfo] = Field(
        None, 
        description="Nutrition information matching Spring's ProductNutrition entity"
    )
    ingredients: Optional[List[str]] = Field(
        None, 
        description="List of ingredients matching Spring's RawMaterial entity",
        example=["밀가루", "설탕", "식물성유지"]
    )
    message: Optional[str] = Field(
        None, 
        description="Status message or error description",
        example="Analysis completed successfully"
    )


class ErrorResponse(BaseModel):
    """Error response model for various failure scenarios.
    
    Implements requirement 4.6: Structured error response with decodeStatus.
    """
    
    decodeStatus: DecodeStatus = Field(
        DecodeStatus.FAILED, 
        description="Status indicating failure type"
    )
    message: str = Field(
        ..., 
        description="Error message explaining the failure"
    )
    product_name: Optional[str] = Field(
        None,
        description="Product name if partially extracted"
    )
    nutrition_info: Optional[NutritionInfo] = Field(
        None,
        description="Partial nutrition info if available"
    )
    ingredients: Optional[List[str]] = Field(
        None,
        description="Partial ingredients list if available"
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response for input validation failures."""
    
    detail: List[Dict[str, str]] = Field(
        ...,
        description="List of validation errors",
        example=[{
            "loc": ["image_urls"],
            "msg": "ensure this value has at most 2 items",
            "type": "value_error.list.max_items"
        }]
    )


# Recommendation API Models

class UserBehavior(BaseModel):
    """User behavior data model for recommendations."""
    
    product_id: int = Field(..., description="Product ID that user interacted with")
    behavior_type: str = Field(
        ..., 
        description="Type of behavior: VIEW, LIKE, REGISTER, SEARCH",
        example="LIKE"
    )
    timestamp: Optional[datetime] = Field(
        None, 
        description="When the behavior occurred"
    )
    
    @validator('behavior_type')
    def validate_behavior_type(cls, v):
        """Validate behavior type."""
        valid_types = ['VIEW', 'LIKE', 'REGISTER', 'SEARCH']
        if v not in valid_types:
            raise ValueError(f"behavior_type must be one of: {valid_types}")
        return v


class UserBasedRecommendationRequest(BaseModel):
    """Request model for user-based recommendations."""
    
    user_id: int = Field(..., description="User ID to generate recommendations for")
    behavior_data: List[UserBehavior] = Field(
        ..., 
        description="User's behavior history",
        min_items=1
    )
    limit: int = Field(
        20, 
        description="Maximum number of recommendations to return",
        ge=1,
        le=50
    )


class ProductBasedRecommendationRequest(BaseModel):
    """Request model for product-based recommendations."""
    
    product_id: int = Field(..., description="Reference product ID")
    limit: int = Field(
        15, 
        description="Maximum number of similar products to return",
        ge=1,
        le=50
    )


class NutritionRatios(BaseModel):
    """영양소 구성비 (탄단지 비율)"""
    carbohydrate_ratio: float = Field(..., description="탄수화물 비율 (%)", ge=0.0, le=100.0)
    protein_ratio: float = Field(..., description="단백질 비율 (%)", ge=0.0, le=100.0)
    fat_ratio: float = Field(..., description="지방 비율 (%)", ge=0.0, le=100.0)
    total_calories: float = Field(..., description="총 칼로리 (kcal)", ge=0.0)


class RecommendationResult(BaseModel):
    """Individual recommendation result."""
    
    product_id: int = Field(..., description="Recommended product ID")
    similarity_score: float = Field(
        ..., 
        description="Similarity score (0-1, higher is more similar)",
        ge=0.0,
        le=1.0
    )
    recommendation_reason: str = Field(
        ..., 
        description="Explanation for why this product was recommended",
        example="사용자가 좋아요한 제품과 유사한 영양성분"
    )


class EnhancedRecommendationResult(RecommendationResult):
    """확장된 추천 결과 (영양소 유사도와 원재료 유사도 포함)"""
    
    nutrition_similarity: Optional[float] = Field(
        None, 
        description="영양소 구성비 유사도 (0-1)",
        ge=0.0,
        le=1.0
    )
    ingredient_similarity: Optional[float] = Field(
        None, 
        description="원재료 유사도 (0-1)",
        ge=0.0,
        le=1.0
    )
    nutrition_ratios: Optional[NutritionRatios] = Field(
        None, 
        description="추천 상품의 영양소 구성비"
    )
    main_ingredients: Optional[List[str]] = Field(
        None, 
        description="추천 상품의 주요 원재료 (상위 5개)",
        example=["밀가루", "설탕", "버터", "계란", "우유"]
    )


class RecommendationResponse(BaseModel):
    """Response model for recommendation requests."""
    
    recommendations: List[RecommendationResult] = Field(
        ..., 
        description="List of recommended products"
    )
    total_count: int = Field(
        ..., 
        description="Total number of recommendations returned"
    )
    user_id: Optional[int] = Field(
        None, 
        description="User ID (for user-based recommendations)"
    )
    reference_product_id: Optional[int] = Field(
        None, 
        description="Reference product ID (for product-based recommendations)"
    )
    recommendation_type: str = Field(
        ...,
        description="Type of recommendation: user-based, product-based, fallback",
        example="user-based"
    )
    data_quality: str = Field(
        "good",
        description="Quality of recommendation data: excellent, good, fair, poor",
        example="good"
    )
    message: Optional[str] = Field(
        None,
        description="Additional information about the recommendation process",
        example="Recommendations based on your recent activity"
    )


class RecommendationErrorResponse(BaseModel):
    """Error response model for recommendation failures."""
    
    error_code: str = Field(
        ...,
        description="Error code for the failure",
        example="INSUFFICIENT_DATA"
    )
    error_message: str = Field(
        ...,
        description="Human-readable error message",
        example="Not enough user behavior data to generate recommendations"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details",
        example={"required_behaviors": 1, "provided_behaviors": 0}
    )
    fallback_available: bool = Field(
        False,
        description="Whether fallback recommendations are available",
        example=True
    )


# Test API Models
class DirectInsertRequest(BaseModel):
    """Direct product insertion request for testing"""
    
    product_id: int = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    nutrition_info: Optional[NutritionInfo] = Field(None, description="Nutrition information")
    ingredients: Optional[List[str]] = Field(None, description="List of ingredients")


class ProductQueryResponse(BaseModel):
    """Product query response"""
    
    found: bool = Field(..., description="Whether product was found")
    product_data: Optional[Dict[str, Any]] = Field(None, description="Product data if found")


class DatabaseOperationResponse(BaseModel):
    """Database operation response"""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")