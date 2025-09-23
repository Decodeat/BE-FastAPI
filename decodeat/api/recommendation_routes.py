"""
API routes for recommendation system.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from decodeat.api.models import (
    UserBasedRecommendationRequest,
    ProductBasedRecommendationRequest,
    RecommendationResponse,
    RecommendationResult,
    EnhancedRecommendationResult,
    NutritionRatios,
    ErrorResponse
)
from decodeat.services.enhanced_vector_service import EnhancedVectorService
from decodeat.services.recommendation_service import RecommendationService
from decodeat.utils.logging import LoggingService
from decodeat.config import settings

logger = LoggingService(__name__)

# Create the recommendation router
recommendation_router = APIRouter()


async def get_vector_service() -> EnhancedVectorService:
    """Dependency to get enhanced vector service instance."""
    vector_service = EnhancedVectorService(
        chroma_host=settings.chroma_host,
        chroma_port=settings.chroma_port
    )
    try:
        await vector_service.initialize()
        yield vector_service
    finally:
        await vector_service.close()


@recommendation_router.post(
    "/user-based", 
    response_model=RecommendationResponse,
    summary="Get user-based recommendations",
    description="Generate personalized recommendations based on user behavior history"
)
async def get_user_based_recommendations(
    request: UserBasedRecommendationRequest,
    vector_service: EnhancedVectorService = Depends(get_vector_service)
):
    """
    Generate personalized recommendations based on user behavior.
    
    Implements requirements:
    - 5.1: Analyze user behavior data with weighted scoring
    - 5.3: Generate personalized recommendations
    - 5.5: Return recommendations with reasons
    
    Args:
        request: User behavior data and preferences
        vector_service: Vector service for similarity search
        
    Returns:
        RecommendationResponse with personalized recommendations
    """
    logger.info(f"Generating user-based recommendations for user {request.user_id}")
    
    try:
        # Initialize recommendation service
        recommendation_service = RecommendationService(vector_service)
        
        # Convert behavior data to dict format
        behavior_data = [
            {
                'product_id': behavior.product_id,
                'behavior_type': behavior.behavior_type,
                'timestamp': behavior.timestamp
            }
            for behavior in request.behavior_data
        ]
        
        # Generate enhanced recommendations with personalized reasons
        recommendations = await recommendation_service.get_enhanced_user_based_recommendations(
            user_id=request.user_id,
            behavior_data=behavior_data,
            limit=request.limit
        )
        
        # Convert to response format
        recommendation_results = [
            RecommendationResult(
                product_id=rec['product_id'],
                similarity_score=rec['similarity_score'],
                recommendation_reason=rec['recommendation_reason']
            )
            for rec in recommendations
        ]
        
        # Evaluate recommendation quality
        behavior_data_dict = [
            {
                'product_id': behavior.product_id,
                'behavior_type': behavior.behavior_type,
                'timestamp': behavior.timestamp
            }
            for behavior in request.behavior_data
        ]
        behavior_analysis = recommendation_service.analyze_user_behavior_patterns(behavior_data_dict)
        data_quality = recommendation_service.evaluate_recommendation_quality(recommendations, behavior_analysis)
        
        # Determine recommendation type and message
        if not recommendations:
            # Try popularity-based fallback
            fallback_recommendations = await recommendation_service.get_popularity_based_fallback(request.limit)
            
            if fallback_recommendations:
                recommendation_results = [
                    RecommendationResult(
                        product_id=rec['product_id'],
                        similarity_score=rec['similarity_score'],
                        recommendation_reason=rec['recommendation_reason']
                    )
                    for rec in fallback_recommendations
                ]
                recommendation_type = "fallback"
                message = "개인화 데이터가 부족하여 인기 제품을 추천합니다"
                data_quality = "fair"
            else:
                recommendation_type = "none"
                message = "추천할 제품이 없습니다. 더 많은 활동 후 다시 시도해주세요"
                data_quality = "poor"
        else:
            recommendation_type = "user-based"
            engagement_level = behavior_analysis.get('engagement_level', 'low')
            if engagement_level in ['very_high', 'high']:
                message = "사용자 활동을 기반으로 맞춤 추천을 제공합니다"
            elif engagement_level == 'medium':
                message = "사용자 관심사를 반영한 추천입니다"
            else:
                message = "더 많은 활동으로 추천 품질을 향상시킬 수 있습니다"
        
        response = RecommendationResponse(
            recommendations=recommendation_results,
            total_count=len(recommendation_results),
            user_id=request.user_id,
            recommendation_type=recommendation_type,
            data_quality=data_quality,
            message=message
        )
        
        logger.info(f"Generated {len(recommendation_results)} {recommendation_type} recommendations for user {request.user_id} (quality: {data_quality})")
        return response
        
    except ValueError as e:
        logger.error(f"Invalid request for user-based recommendations: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_REQUEST",
                "error_message": str(e),
                "fallback_available": False
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate user-based recommendations: {e}")
        
        # Try to provide fallback recommendations even on error
        try:
            fallback_recommendations = await recommendation_service.get_popularity_based_fallback(request.limit)
            if fallback_recommendations:
                recommendation_results = [
                    RecommendationResult(
                        product_id=rec['product_id'],
                        similarity_score=rec['similarity_score'],
                        recommendation_reason=rec['recommendation_reason']
                    )
                    for rec in fallback_recommendations
                ]
                
                response = RecommendationResponse(
                    recommendations=recommendation_results,
                    total_count=len(recommendation_results),
                    user_id=request.user_id,
                    recommendation_type="fallback",
                    data_quality="fair",
                    message="시스템 오류로 인해 인기 제품을 추천합니다"
                )
                
                logger.info(f"Provided fallback recommendations due to error for user {request.user_id}")
                return response
        except Exception as fallback_error:
            logger.error(f"Fallback recommendations also failed: {fallback_error}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "RECOMMENDATION_FAILED",
                "error_message": "추천 시스템에 일시적인 문제가 발생했습니다",
                "details": {"original_error": str(e)},
                "fallback_available": False
            }
        )


@recommendation_router.post(
    "/product-based", 
    response_model=RecommendationResponse,
    summary="Get product-based recommendations",
    description="Find products similar to a given product"
)
async def get_product_based_recommendations(
    request: ProductBasedRecommendationRequest,
    vector_service: EnhancedVectorService = Depends(get_vector_service)
):
    """
    Generate recommendations based on product similarity.
    
    Implements requirements:
    - 5.2: Find similar products using vector similarity
    - 5.5: Return recommendations with reasons
    
    Args:
        request: Reference product ID and limit
        vector_service: Vector service for similarity search
        
    Returns:
        RecommendationResponse with similar products
    """
    logger.info(f"Generating product-based recommendations for product {request.product_id}")
    
    try:
        # Initialize recommendation service
        recommendation_service = RecommendationService(vector_service)
        
        # Generate recommendations
        recommendations = await recommendation_service.get_product_based_recommendations(
            product_id=request.product_id,
            limit=request.limit
        )
        
        # Get collection info for debugging
        collection_info = await vector_service.get_collection_info()
        total_products_in_db = collection_info.get('count', 0)
        
        logger.debug(f"Total products in DB: {total_products_in_db}, "
                    f"Requested limit: {request.limit}, "
                    f"Actual recommendations: {len(recommendations)}")
        
        # Convert to enhanced response format
        recommendation_results = []
        for rec in recommendations:
            # Check if this is an enhanced recommendation with nutrition/ingredient data
            if 'nutrition_similarity' in rec and 'ingredient_similarity' in rec:
                # Create enhanced result with nutrition ratios
                nutrition_ratios = None
                if rec.get('nutrition_ratios'):
                    nutrition_ratios = NutritionRatios(
                        carbohydrate_ratio=rec['nutrition_ratios'].get('carbohydrate_ratio', 0),
                        protein_ratio=rec['nutrition_ratios'].get('protein_ratio', 0),
                        fat_ratio=rec['nutrition_ratios'].get('fat_ratio', 0),
                        total_calories=rec['nutrition_ratios'].get('total_calories', 0)
                    )
                
                recommendation_results.append(EnhancedRecommendationResult(
                    product_id=rec['product_id'],
                    similarity_score=rec['similarity_score'],
                    recommendation_reason=rec['recommendation_reason'],
                    nutrition_similarity=rec.get('nutrition_similarity'),
                    ingredient_similarity=rec.get('ingredient_similarity'),
                    nutrition_ratios=nutrition_ratios,
                    main_ingredients=rec.get('main_ingredients', [])
                ))
            else:
                # Fallback to basic result for compatibility
                recommendation_results.append(RecommendationResult(
                    product_id=rec['product_id'],
                    similarity_score=rec['similarity_score'],
                    recommendation_reason=rec['recommendation_reason']
                ))
        
        # Evaluate recommendation quality
        data_quality = recommendation_service.evaluate_recommendation_quality(recommendations)
        
        # Determine recommendation type and message
        if not recommendations:
            # Try popularity-based fallback
            fallback_recommendations = await recommendation_service.get_popularity_based_fallback(request.limit)
            
            if fallback_recommendations:
                recommendation_results = [
                    RecommendationResult(
                        product_id=rec['product_id'],
                        similarity_score=rec['similarity_score'],
                        recommendation_reason=rec['recommendation_reason']
                    )
                    for rec in fallback_recommendations
                ]
                recommendation_type = "fallback"
                message = f"제품 {request.product_id}와 유사한 제품을 찾을 수 없어 인기 제품을 추천합니다"
                data_quality = "fair"
            else:
                recommendation_type = "none"
                message = f"제품 {request.product_id}와 관련된 추천을 찾을 수 없습니다"
                data_quality = "poor"
        else:
            recommendation_type = "product-based"
            avg_similarity = sum(rec['similarity_score'] for rec in recommendations) / len(recommendations)
            if avg_similarity >= 0.8:
                message = "매우 유사한 제품들을 찾았습니다"
            elif avg_similarity >= 0.7:
                message = "유사한 제품들을 추천합니다"
            else:
                message = "관련 제품들을 추천합니다"
                
            # Add context about available vs requested count
            if len(recommendations) < request.limit and total_products_in_db <= request.limit:
                message += f" (DB에 총 {total_products_in_db}개 제품 중 {len(recommendations)}개 추천)"
        
        response = RecommendationResponse(
            recommendations=recommendation_results,
            total_count=len(recommendation_results),
            reference_product_id=request.product_id,
            recommendation_type=recommendation_type,
            data_quality=data_quality,
            message=message
        )
        
        # Log information about the result count
        if len(recommendation_results) < request.limit:
            logger.info(f"Generated {len(recommendation_results)} {recommendation_type} recommendations for product {request.product_id} "
                       f"(requested: {request.limit}, available: {len(recommendation_results)}, quality: {data_quality})")
        else:
            logger.info(f"Generated {len(recommendation_results)} {recommendation_type} recommendations for product {request.product_id} (quality: {data_quality})")
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid request for product-based recommendations: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_REQUEST",
                "error_message": str(e),
                "fallback_available": False
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate product-based recommendations: {e}")
        
        # Try to provide fallback recommendations even on error
        try:
            fallback_recommendations = await recommendation_service.get_popularity_based_fallback(request.limit)
            if fallback_recommendations:
                recommendation_results = [
                    RecommendationResult(
                        product_id=rec['product_id'],
                        similarity_score=rec['similarity_score'],
                        recommendation_reason=rec['recommendation_reason']
                    )
                    for rec in fallback_recommendations
                ]
                
                response = RecommendationResponse(
                    recommendations=recommendation_results,
                    total_count=len(recommendation_results),
                    reference_product_id=request.product_id,
                    recommendation_type="fallback",
                    data_quality="fair",
                    message="시스템 오류로 인해 인기 제품을 추천합니다"
                )
                
                logger.info(f"Provided fallback recommendations due to error for product {request.product_id}")
                return response
        except Exception as fallback_error:
            logger.error(f"Fallback recommendations also failed: {fallback_error}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "RECOMMENDATION_FAILED",
                "error_message": "추천 시스템에 일시적인 문제가 발생했습니다",
                "details": {"original_error": str(e)},
                "fallback_available": False
            }
        )


@recommendation_router.get(
    "/health",
    summary="Recommendation service health check",
    description="Check if recommendation services are healthy"
)
async def recommendation_health_check():
    """Health check for recommendation services."""
    try:
        # Test ChromaDB connection
        vector_service = VectorService()
        async with vector_service:
            # Simple connection test
            pass
            
        return {
            "status": "healthy",
            "service": "recommendation-system",
            "components": {
                "vector_service": "healthy",
                "chroma_db": "connected"
            }
        }
        
    except Exception as e:
        logger.error(f"Recommendation health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "recommendation-system",
                "error": str(e)
            }
        )