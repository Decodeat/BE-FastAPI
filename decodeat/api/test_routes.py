"""
Test API routes for ChromaDB management and direct data insertion
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from decodeat.api.models import (
    DirectInsertRequest,
    ProductQueryResponse,
    DatabaseOperationResponse,
    NutritionInfo
)
from decodeat.services.enhanced_vector_service import EnhancedVectorService
from decodeat.utils.logging import LoggingService
from decodeat.config import settings

logger = LoggingService(__name__)

# Create the test router
test_router = APIRouter()


async def get_enhanced_vector_service() -> EnhancedVectorService:
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


@test_router.delete(
    "/chromadb/clear",
    response_model=DatabaseOperationResponse,
    summary="Clear all ChromaDB data",
    description="Delete all products from ChromaDB for testing purposes"
)
async def clear_chromadb(
    vector_service: EnhancedVectorService = Depends(get_enhanced_vector_service)
):
    """Clear all data from ChromaDB"""
    try:
        logger.info("Clearing all ChromaDB data")
        
        if not vector_service.is_chromadb_available():
            raise HTTPException(
                status_code=503,
                detail="ChromaDB is not available"
            )
        
        # Get collection info
        collection_info = await vector_service.get_collection_info()
        initial_count = collection_info.get('count', 0)
        
        if initial_count == 0:
            return DatabaseOperationResponse(
                success=True,
                message="ChromaDB is already empty",
                details={"initial_count": 0, "deleted_count": 0}
            )
        
        # Get all IDs and delete them
        try:
            all_data = vector_service.collection.get(include=[])
            all_ids = all_data.get('ids', [])
            
            if all_ids:
                vector_service.collection.delete(ids=all_ids)
                logger.info(f"Deleted {len(all_ids)} products from ChromaDB")
            
            # Verify deletion
            final_info = await vector_service.get_collection_info()
            final_count = final_info.get('count', 0)
            
            return DatabaseOperationResponse(
                success=True,
                message=f"Successfully cleared ChromaDB",
                details={
                    "initial_count": initial_count,
                    "deleted_count": len(all_ids),
                    "final_count": final_count
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clear ChromaDB: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error clearing ChromaDB: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@test_router.post(
    "/chromadb/insert",
    response_model=DatabaseOperationResponse,
    summary="Direct product insertion",
    description="Insert product data directly into ChromaDB with enhanced format"
)
async def insert_product_direct(
    request: DirectInsertRequest,
    vector_service: EnhancedVectorService = Depends(get_enhanced_vector_service)
):
    """Insert product data directly into ChromaDB"""
    try:
        logger.info(f"Direct insertion of product {request.product_id}")
        
        if not vector_service.is_chromadb_available():
            raise HTTPException(
                status_code=503,
                detail="ChromaDB is not available"
            )
        
        # Convert request to product data format
        product_data = {
            'product_name': request.product_name,
            'nutrition_info': {},
            'ingredients': request.ingredients or []
        }
        
        # Convert nutrition info if provided
        if request.nutrition_info:
            nutrition_dict = request.nutrition_info.dict()
            # Remove None values
            product_data['nutrition_info'] = {
                k: v for k, v in nutrition_dict.items() if v is not None
            }
        
        # Store using enhanced vector service
        success = await vector_service.store_product_with_id(
            request.product_id, 
            product_data
        )
        
        if success:
            # Verify storage
            stored_product = await vector_service.get_product_by_id(request.product_id)
            
            return DatabaseOperationResponse(
                success=True,
                message=f"Successfully inserted product {request.product_id}",
                details={
                    "product_id": request.product_id,
                    "product_name": request.product_name,
                    "has_nutrition_ratios": bool(stored_product and stored_product.get('nutrition_ratios')),
                    "ingredient_count": len(request.ingredients or []),
                    "stored_data": stored_product
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store product {request.product_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error inserting product {request.product_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@test_router.get(
    "/chromadb/product/{product_id}",
    response_model=ProductQueryResponse,
    summary="Query product by ID",
    description="Retrieve product data from ChromaDB by product ID"
)
async def get_product_by_id(
    product_id: int,
    vector_service: EnhancedVectorService = Depends(get_enhanced_vector_service)
):
    """Get product data by ID from ChromaDB"""
    try:
        logger.info(f"Querying product {product_id}")
        
        if not vector_service.is_chromadb_available():
            raise HTTPException(
                status_code=503,
                detail="ChromaDB is not available"
            )
        
        # Query product
        product_data = await vector_service.get_product_by_id(product_id)
        
        if product_data:
            return ProductQueryResponse(
                found=True,
                product_data=product_data
            )
        else:
            return ProductQueryResponse(
                found=False,
                product_data=None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error querying product {product_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@test_router.get(
    "/chromadb/stats",
    response_model=Dict[str, Any],
    summary="Get ChromaDB statistics",
    description="Get statistics about ChromaDB collection"
)
async def get_chromadb_stats(
    vector_service: EnhancedVectorService = Depends(get_enhanced_vector_service)
):
    """Get ChromaDB collection statistics"""
    try:
        logger.info("Getting ChromaDB statistics")
        
        if not vector_service.is_chromadb_available():
            raise HTTPException(
                status_code=503,
                detail="ChromaDB is not available"
            )
        
        # Get collection info
        collection_info = await vector_service.get_collection_info()
        
        # Get sample data if available
        sample_data = None
        if collection_info.get('count', 0) > 0:
            try:
                sample_results = vector_service.collection.get(
                    limit=3,
                    include=['metadatas']
                )
                sample_data = sample_results.get('metadatas', [])
            except Exception as e:
                logger.warning(f"Failed to get sample data: {e}")
        
        return {
            "collection_info": collection_info,
            "sample_products": sample_data,
            "enhanced_format_count": len([
                meta for meta in (sample_data or [])
                if 'carbohydrate_ratio' in meta
            ]) if sample_data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting ChromaDB stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@test_router.post(
    "/chromadb/migrate",
    response_model=DatabaseOperationResponse,
    summary="Migrate existing data to enhanced format",
    description="Convert existing ChromaDB data to enhanced format with nutrition ratios"
)
async def migrate_to_enhanced_format(
    vector_service: EnhancedVectorService = Depends(get_enhanced_vector_service)
):
    """Migrate existing data to enhanced format"""
    try:
        logger.info("Starting migration to enhanced format")
        
        if not vector_service.is_chromadb_available():
            raise HTTPException(
                status_code=503,
                detail="ChromaDB is not available"
            )
        
        # Get all existing data
        collection_info = await vector_service.get_collection_info()
        total_count = collection_info.get('count', 0)
        
        if total_count == 0:
            return DatabaseOperationResponse(
                success=True,
                message="No data to migrate",
                details={"total_count": 0, "migrated_count": 0}
            )
        
        # Get all products
        all_data = vector_service.collection.get(
            include=['metadatas', 'embeddings'],
            limit=total_count
        )
        
        migrated_count = 0
        failed_count = 0
        
        for i, (product_id, metadata, embedding) in enumerate(zip(
            all_data.get('ids', []),
            all_data.get('metadatas', []),
            all_data.get('embeddings', [])
        )):
            try:
                # Check if already in enhanced format
                if 'carbohydrate_ratio' in metadata:
                    logger.debug(f"Product {product_id} already in enhanced format")
                    continue
                
                # Convert old format to new format
                product_data = {
                    'product_name': metadata.get('product_name', ''),
                    'nutrition_info': {},
                    'ingredients': []
                }
                
                # Extract nutrition info from old metadata
                for key in ['energy', 'protein', 'fat', 'carbohydrate', 'sodium']:
                    if key in metadata and metadata[key] is not None:
                        product_data['nutrition_info'][key] = str(metadata[key])
                
                # Extract ingredients from old metadata
                if 'main_ingredients' in metadata and metadata['main_ingredients']:
                    ingredients_str = metadata['main_ingredients']
                    if isinstance(ingredients_str, str):
                        product_data['ingredients'] = [
                            ing.strip() for ing in ingredients_str.split(',') if ing.strip()
                        ]
                
                # Re-store with enhanced format
                success = await vector_service.store_product_with_id(
                    int(product_id), 
                    product_data
                )
                
                if success:
                    migrated_count += 1
                    logger.debug(f"Migrated product {product_id}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to migrate product {product_id}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error migrating product {product_id}: {e}")
        
        return DatabaseOperationResponse(
            success=True,
            message=f"Migration completed",
            details={
                "total_count": total_count,
                "migrated_count": migrated_count,
                "failed_count": failed_count,
                "already_enhanced": total_count - migrated_count - failed_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )