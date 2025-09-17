"""
API routes for nutrition label analysis.
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from decodeat.api.models import AnalyzeRequest, AnalyzeResponse, DecodeStatus, ErrorResponse
from decodeat.services.image_download_service import ImageDownloadService
from decodeat.services.ocr_service import OCRService
from decodeat.services.validation_service import ValidationService
from decodeat.services.analysis_service import AnalysisService
from decodeat.services.vector_service import VectorService
from decodeat.utils.logging import LoggingService
from decodeat.config import settings

logger = LoggingService(__name__)

# Create the main API router
router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_nutrition_label(request: AnalyzeRequest):
    """
    Analyze nutrition label from image URLs.
    
    This endpoint accepts 1-2 image URLs and returns structured nutrition information.
    - Single image: Analyzes the image for nutrition information
    - Two images: Validates they belong to the same product and combines analysis
    
    Implements requirements:
    - 1.2: Handle 1 or 2 image URLs accordingly
    - 1.3: Return validation error for >2 or 0 image URLs (handled by Pydantic)
    - 1.4: Assume one image contains ingredients, other contains nutrition info for 2 images
    - 1.5: Return JSON response with nutrition data and status information
    
    Args:
        request: AnalyzeRequest containing image URLs
        
    Returns:
        AnalyzeResponse with structured nutrition data and processing status
    """
    logger.info(f"Starting nutrition analysis for {len(request.image_urls)} image(s)")
    
    # Initialize services
    image_service = ImageDownloadService()
    ocr_service = OCRService()
    validation_service = ValidationService()
    analysis_service = AnalysisService()
    
    try:
        async with image_service:
            # Step 1: Download images
            logger.info("Downloading images...")
            try:
                if len(request.image_urls) == 1:
                    image_bytes = await image_service.download_image(request.image_urls[0])
                    images_bytes = [image_bytes]
                else:  # len == 2
                    images_bytes = await image_service.download_multiple_images(request.image_urls)
            except Exception as e:
                logger.error(f"Image download failed: {e}")
                return AnalyzeResponse(
                    decodeStatus=DecodeStatus.FAILED,
                    message=f"Failed to download images: {str(e)}",
                    product_name=None,
                    nutrition_info=None,
                    ingredients=None
                )
            
            # Step 2: Extract text using OCR
            logger.info("Extracting text from images...")
            try:
                async with ocr_service:
                    if len(images_bytes) == 1:
                        extracted_text = await ocr_service.extract_text(images_bytes[0])
                        texts = [extracted_text]
                    else:  # len == 2
                        texts = await ocr_service.extract_text_from_multiple_images(images_bytes)
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
                return AnalyzeResponse(
                    decodeStatus=DecodeStatus.FAILED,
                    message=f"Failed to extract text from images: {str(e)}",
                    product_name=None,
                    nutrition_info=None,
                    ingredients=None
                )
            
            # Step 3: Validate content
            logger.info("Validating image content...")
            try:
                if len(texts) == 1:
                    # Single image validation
                    is_valid = await validation_service.validate_single_image(texts[0])
                    if not is_valid:
                        logger.info("Single image validation failed - not nutrition related")
                        return AnalyzeResponse(
                            decodeStatus=DecodeStatus.CANCELLED,
                            message="Image does not contain nutrition or ingredient information",
                            product_name=None,
                            nutrition_info=None,
                            ingredients=None
                        )
                    combined_text = texts[0]
                else:  # len == 2
                    # Validate each image individually first
                    text1_valid = await validation_service.validate_single_image(texts[0])
                    text2_valid = await validation_service.validate_single_image(texts[1])
                    
                    if not text1_valid and not text2_valid:
                        logger.info("Both images validation failed - not nutrition related")
                        return AnalyzeResponse(
                            decodeStatus=DecodeStatus.CANCELLED,
                            message="Neither image contains nutrition or ingredient information",
                            product_name=None,
                            nutrition_info=None,
                            ingredients=None
                        )
                    
                    if not text1_valid or not text2_valid:
                        logger.info("One image validation failed - using valid image only")
                        combined_text = texts[0] if text1_valid else texts[1]
                    else:
                        # Both images are valid, check if they belong to the same product
                        is_same_product = await validation_service.validate_image_pair(texts[0], texts[1])
                        if not is_same_product:
                            logger.info("Image pair validation failed - different products")
                            return AnalyzeResponse(
                                decodeStatus=DecodeStatus.CANCELLED,
                                message="Images appear to be from different products",
                                product_name=None,
                                nutrition_info=None,
                                ingredients=None
                            )
                        # Combine texts for analysis
                        combined_text = f"{texts[0]}\n\n{texts[1]}"
                        
            except Exception as e:
                logger.error(f"Content validation failed: {e}")
                return AnalyzeResponse(
                    decodeStatus=DecodeStatus.FAILED,
                    message=f"Failed to validate image content: {str(e)}",
                    product_name=None,
                    nutrition_info=None,
                    ingredients=None
                )
            
            # Step 4: Analyze nutrition information
            logger.info("Analyzing nutrition information...")
            try:
                analysis_result = await analysis_service.analyze_nutrition_info(combined_text)
                
                # Convert the analysis result to AnalyzeResponse
                response = AnalyzeResponse(
                    decodeStatus=analysis_result["decodeStatus"],
                    product_name=analysis_result["product_name"],
                    nutrition_info=analysis_result["nutrition_info"],
                    ingredients=analysis_result["ingredients"],
                    message=analysis_result["message"]
                )
                
                logger.info(f"Analysis completed with status: {response.decodeStatus}")
                
                # Auto-generate and store vector if analysis was successful
                if response.decodeStatus == DecodeStatus.COMPLETED:
                    await _auto_generate_product_vector(response)
                
                return response
                
            except Exception as e:
                logger.error(f"Nutrition analysis failed: {e}")
                return AnalyzeResponse(
                    decodeStatus=DecodeStatus.FAILED,
                    message=f"Failed to analyze nutrition information: {str(e)}",
                    product_name=None,
                    nutrition_info=None,
                    ingredients=None
                )
    
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        return AnalyzeResponse(
            decodeStatus=DecodeStatus.FAILED,
            message=f"Unexpected error during analysis: {str(e)}",
            product_name=None,
            nutrition_info=None,
            ingredients=None
        )


async def _auto_generate_product_vector(analysis_result: AnalyzeResponse):
    """
    Automatically generate and store product vector after successful analysis.
    
    This function implements requirement 4.1: Auto-generate vectors when products are analyzed.
    It runs in the background and doesn't affect the main analysis response.
    
    Args:
        analysis_result: The successful analysis result
    """
    try:
        # Only proceed if we have sufficient data for vector generation
        if not analysis_result.product_name and not analysis_result.nutrition_info and not analysis_result.ingredients:
            logger.debug("Insufficient data for vector generation - skipping")
            return
            
        logger.info(f"Auto-generating vector for product: {analysis_result.product_name or 'Unknown Product'}")
        
        # Initialize vector service
        vector_service = VectorService(
            chroma_host=settings.chroma_host,
            chroma_port=settings.chroma_port
        )
        
        async with vector_service:
            # Prepare product data for vector generation
            product_data = {
                'product_name': analysis_result.product_name or 'Unknown Product',
                'nutrition_info': {},
                'ingredients': analysis_result.ingredients or []
            }
            
            # Convert nutrition info to dict if available
            if analysis_result.nutrition_info:
                nutrition_dict = {}
                for field, value in analysis_result.nutrition_info.dict().items():
                    if value is not None:
                        # Try to extract numeric value for key nutrients
                        try:
                            if field in ['energy', 'protein', 'fat', 'carbohydrate', 'sodium', 'sugar', 'fiber', 'calcium']:
                                # Extract numeric part from strings like "160kcal" or "10.5g"
                                import re
                                numeric_match = re.search(r'(\d+\.?\d*)', str(value))
                                if numeric_match:
                                    nutrition_dict[field] = float(numeric_match.group(1))
                                else:
                                    # If no numeric value found, store as string
                                    nutrition_dict[field] = str(value)
                            else:
                                nutrition_dict[field] = str(value) if value else None
                        except (ValueError, AttributeError):
                            nutrition_dict[field] = str(value) if value else None
                            
                product_data['nutrition_info'] = nutrition_dict
            
            # Generate a deterministic product ID based on content
            import hashlib
            import json
            
            # Create a consistent hash based on product data
            content_for_hash = {
                'name': product_data['product_name'],
                'nutrition': sorted(product_data['nutrition_info'].items()) if product_data['nutrition_info'] else [],
                'ingredients': sorted(product_data['ingredients']) if product_data['ingredients'] else []
            }
            content_str = json.dumps(content_for_hash, sort_keys=True)
            temp_product_id = int(hashlib.md5(content_str.encode()).hexdigest()[:8], 16)
            
            logger.debug(f"Generated product ID: {temp_product_id} for vector storage")
            
            # Store the vector (this will work even if ChromaDB is not available)
            success = await vector_service.store_product_vector(temp_product_id, product_data)
            
            if success:
                logger.info(f"Successfully stored vector for product {temp_product_id}")
                
                # Log vector generation details
                collection_info = await vector_service.get_collection_info()
                logger.debug(f"Collection info after storage: {collection_info}")
            else:
                logger.warning(f"Failed to store vector for product {temp_product_id} (ChromaDB may not be available)")
                
    except Exception as e:
        # Don't let vector generation errors affect the main analysis response
        logger.error(f"Error during auto vector generation: {e}", exc_info=True)