"""
Pydantic models for API requests and responses.
Designed to match Spring server's database structure.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
from enum import Enum


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