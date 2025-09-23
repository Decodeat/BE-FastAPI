"""
Vector embedding and similarity search service using ChromaDB and sentence-transformers.
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

from decodeat.utils.logging import LoggingService
from decodeat.utils.performance import measure_time, VectorSearchOptimizer
from decodeat.utils.model_cache import model_cache
from decodeat.utils.model_optimization import optimize_model_loading

logger = LoggingService(__name__)


class VectorService:
    """Service for generating embeddings and performing vector similarity search."""
    
    def __init__(self, chroma_host: str = "localhost", chroma_port: int = 8000):
        """
        Initialize the vector service.
        
        Args:
            chroma_host: ChromaDB host address
            chroma_port: ChromaDB port
        """
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.client = None
        self.collection = None
        self.model = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize ChromaDB client and sentence transformer model."""
        try:
            # Use cached sentence transformer model
            if model_cache.is_model_loaded():
                logger.info("Using cached sentence transformer model")
                self.model = model_cache.get_model()
            else:
                logger.info("Loading sentence transformer model...")
                self.model = model_cache.get_model()
                if self.model:
                    logger.info("Sentence transformer model loaded successfully")
                else:
                    raise RuntimeError("Failed to load sentence transformer model")
            
            # Try to initialize ChromaDB client
            try:
                logger.info(f"Connecting to ChromaDB at {self.chroma_host}:{self.chroma_port}")
                self.client = chromadb.HttpClient(
                    host=self.chroma_host,
                    port=self.chroma_port,
                    settings=Settings(allow_reset=True)
                )
                
                # Get or create collection for product vectors
                self.collection = self.client.get_or_create_collection(
                    name="product_vectors",
                    metadata={"description": "Product nutrition and ingredient embeddings"}
                )
                
                logger.info("ChromaDB connection established successfully")
                
            except Exception as chroma_error:
                logger.warning(f"ChromaDB connection failed: {chroma_error}")
                logger.info("Vector service will work in vector-generation-only mode")
                self.client = None
                self.collection = None
            
            logger.info("Vector service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise
            
    async def close(self):
        """Clean up resources."""
        self.client = None
        self.collection = None
        self.model = None
        logger.info("Vector service closed")
        
    def is_chromadb_available(self) -> bool:
        """Check if ChromaDB is available for vector storage operations."""
        return self.client is not None and self.collection is not None
        
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the product vectors collection."""
        if not self.is_chromadb_available():
            return {"error": "ChromaDB not available", "count": 0}
            
        try:
            count = self.collection.count()
            return {
                "name": "product_vectors",
                "count": count,
                "description": "Product nutrition and ingredient embeddings",
                "status": "available"
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"error": str(e), "count": 0}
            
    async def delete_product_vector(self, product_id: int) -> bool:
        """
        Delete a product vector from ChromaDB.
        
        Args:
            product_id: Product ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for delete operation")
            return False
            
        try:
            self.collection.delete(ids=[str(product_id)])
            logger.info(f"Deleted vector for product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete product vector for {product_id}: {e}")
            return False
            
    async def update_product_vector(
        self, 
        product_id: int, 
        product_data: Dict[str, Any]
    ) -> bool:
        """
        Update a product vector in ChromaDB.
        
        Args:
            product_id: Product ID to update
            product_data: Updated product information
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for update operation")
            return False
            
        try:
            # Delete existing vector first
            await self.delete_product_vector(product_id)
            
            # Store new vector
            return await self.store_product_vector(product_id, product_data)
            
        except Exception as e:
            logger.error(f"Failed to update product vector for {product_id}: {e}")
            return False
        
    def convert_nutrition_to_text(self, nutrition_data: Dict[str, Any]) -> str:
        """
        Convert nutrition data to Korean text format for embedding generation.
        
        Args:
            nutrition_data: Dictionary containing nutrition information
            
        Returns:
            Formatted Korean text representation of nutrition data
        """
        if not nutrition_data:
            return ""
            
        nutrition_parts = []
        
        # Basic nutrition components with Korean labels
        nutrition_mapping = {
            'energy': ('열량', 'kcal'),
            'protein': ('단백질', 'g'),
            'fat': ('지방', 'g'),
            'carbohydrate': ('탄수화물', 'g'),
            'sugar': ('당류', 'g'),
            'sodium': ('나트륨', 'mg'),
            'cholesterol': ('콜레스테롤', 'mg'),
            'saturated_fat': ('포화지방', 'g'),
            'trans_fat': ('트랜스지방', 'g'),
            'fiber': ('식이섬유', 'g'),
            'calcium': ('칼슘', 'mg'),
            'iron': ('철분', 'mg'),
            'potassium': ('칼륨', 'mg'),
            'vitamin_c': ('비타민C', 'mg'),
            'vitamin_a': ('비타민A', 'μg')
        }
        
        for key, (korean_name, unit) in nutrition_mapping.items():
            value = nutrition_data.get(key)
            if value is not None and value != 0:
                nutrition_parts.append(f"{korean_name} {value}{unit}")
        
        return f"영양성분: {' '.join(nutrition_parts)}" if nutrition_parts else ""
    
    def convert_ingredients_to_text(self, ingredients_data: List[str]) -> str:
        """
        Convert ingredients list to Korean text format for embedding generation.
        
        Args:
            ingredients_data: List of ingredient names
            
        Returns:
            Formatted Korean text representation of ingredients
        """
        if not ingredients_data or len(ingredients_data) == 0:
            return ""
            
        # Clean and format ingredients
        cleaned_ingredients = []
        for ingredient in ingredients_data:
            if ingredient and ingredient.strip():
                cleaned_ingredients.append(ingredient.strip())
        
        if not cleaned_ingredients:
            return ""
            
        return f"원재료: {', '.join(cleaned_ingredients)}"
    
    @measure_time("text_to_vector_conversion")
    def convert_text_to_vector(self, text: str) -> List[float]:
        """
        Convert text to 384-dimensional vector using multilingual sentence transformer.
        
        Args:
            text: Input text to convert to vector
            
        Returns:
            384-dimensional embedding vector as list of floats
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 384
            
        try:
            # Generate embedding using multilingual sentence transformer
            embedding = self.model.encode(text.strip(), convert_to_tensor=False)
            
            # Convert to list
            vector = embedding.tolist()
            
            # Validate vector dimensions
            expected_dim = 384
            if len(vector) != expected_dim:
                logger.warning(f"Expected {expected_dim} dimensions, got {len(vector)}")
                
                # If vector is larger, truncate to 384 dimensions
                if len(vector) > expected_dim:
                    vector = vector[:expected_dim]
                    logger.info(f"Truncated vector to {expected_dim} dimensions")
                # If vector is smaller, pad with zeros
                elif len(vector) < expected_dim:
                    vector.extend([0.0] * (expected_dim - len(vector)))
                    logger.info(f"Padded vector to {expected_dim} dimensions")
                
            return vector
            
        except Exception as e:
            logger.error(f"Failed to convert text to vector: {e}")
            # Return zero vector on error
            return [0.0] * 384
    
    def _create_product_text(self, product_data: Dict[str, Any]) -> str:
        """
        Convert product data to text for embedding generation.
        
        Args:
            product_data: Dictionary containing product information
            
        Returns:
            Formatted text representation of the product
        """
        text_parts = []
        
        # Add product name if available
        if product_data.get('product_name'):
            text_parts.append(f"제품명: {product_data['product_name']}")
            
        # Add nutrition information using dedicated function
        if product_data.get('nutrition_info'):
            nutrition_text = self.convert_nutrition_to_text(product_data['nutrition_info'])
            if nutrition_text:
                text_parts.append(nutrition_text)
            
        # Add ingredients using dedicated function
        if product_data.get('ingredients'):
            ingredients_text = self.convert_ingredients_to_text(product_data['ingredients'])
            if ingredients_text:
                text_parts.append(ingredients_text)
            
        return " ".join(text_parts)
        
    async def generate_product_vector(self, product_data: Dict[str, Any]) -> List[float]:
        """
        Generate embedding vector for a product.
        
        Args:
            product_data: Dictionary containing product information
            
        Returns:
            384-dimensional embedding vector
        """
        try:
            product_text = self._create_product_text(product_data)
            logger.debug(f"Generated product text: {product_text[:100]}...")
            
            # Generate embedding using dedicated text-to-vector function
            vector = self.convert_text_to_vector(product_text)
            return vector
            
        except Exception as e:
            logger.error(f"Failed to generate product vector: {e}")
            raise
            
    async def store_product_vector(
        self, 
        product_id: int, 
        product_data: Dict[str, Any]
    ) -> bool:
        """
        Store product vector in ChromaDB.
        
        Args:
            product_id: Unique product identifier
            product_data: Product information dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for store operation")
            return False
            
        try:
            # Generate vector
            vector = await self.generate_product_vector(product_data)
            
            # Prepare metadata
            metadata = {
                "product_id": product_id,
                "product_name": product_data.get('product_name', ''),
            }
            
            # Add key nutrition info to metadata for filtering
            if product_data.get('nutrition_info'):
                nutrition = product_data['nutrition_info']
                if nutrition.get('energy'):
                    metadata['energy'] = float(nutrition['energy'])
                if nutrition.get('protein'):
                    metadata['protein'] = float(nutrition['protein'])
                if nutrition.get('fat'):
                    metadata['fat'] = float(nutrition['fat'])
                if nutrition.get('carbohydrate'):
                    metadata['carbohydrate'] = float(nutrition['carbohydrate'])
                if nutrition.get('sodium'):
                    metadata['sodium'] = float(nutrition['sodium'])
                    
            # Add main ingredients to metadata (as string)
            if product_data.get('ingredients'):
                main_ingredients = product_data['ingredients'][:3]  # First 3 ingredients
                metadata['main_ingredients'] = ', '.join(main_ingredients) if main_ingredients else ''
                
            # Store in ChromaDB
            self.collection.add(
                embeddings=[vector],
                metadatas=[metadata],
                ids=[str(product_id)]
            )
            
            logger.info(f"Stored vector for product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store product vector for {product_id}: {e}")
            return False
            
    @measure_time("vector_similarity_search")
    async def find_similar_products(
        self, 
        product_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find products similar to the given product.
        
        Args:
            product_id: Reference product ID
            limit: Maximum number of similar products to return
            
        Returns:
            List of similar products with similarity scores
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for similarity search")
            return []
            
        try:
            # Get the reference product vector
            results = self.collection.get(
                ids=[str(product_id)],
                include=['embeddings', 'metadatas']
            )
            
            if not results['embeddings']:
                logger.warning(f"No vector found for product {product_id}")
                return []
                
            reference_vector = results['embeddings'][0]
            
            # Search for similar products
            similar_results = self.collection.query(
                query_embeddings=[reference_vector],
                n_results=limit + 1,  # +1 to exclude the reference product itself
                include=['metadatas', 'distances']
            )
            
            logger.debug(f"ChromaDB returned {len(similar_results['metadatas'][0])} results for product {product_id}")
            
            similar_products = []
            for i, (metadata, distance) in enumerate(zip(
                similar_results['metadatas'][0],
                similar_results['distances'][0]
            )):
                # Skip the reference product itself
                if metadata['product_id'] == product_id:
                    logger.debug(f"Skipping reference product {product_id} from similarity results")
                    continue
                    
                # Convert distance to similarity score (0-1, higher is more similar)
                similarity_score = max(0, 1 - distance)
                
                similar_products.append({
                    'product_id': metadata['product_id'],
                    'similarity_score': round(similarity_score, 3),
                    'recommendation_reason': self._generate_recommendation_reason(
                        metadata, similarity_score
                    )
                })
                
            logger.info(f"Found {len(similar_products)} similar products for product {product_id} (requested limit: {limit})")
            
            # Return results (may be less than limit if DB has fewer products)
            return similar_products[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar products for {product_id}: {e}")
            return []
            
    @measure_time("user_preference_search")
    async def search_by_user_preferences(
        self, 
        user_preference_vector: List[float], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for products based on user preference vector.
        
        Args:
            user_preference_vector: User's preference embedding
            limit: Maximum number of products to return
            
        Returns:
            List of recommended products with similarity scores
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for user preference search")
            return []
            
        try:
            # Search for products matching user preferences
            results = self.collection.query(
                query_embeddings=[user_preference_vector],
                n_results=limit,
                include=['metadatas', 'distances']
            )
            
            recommendations = []
            for metadata, distance in zip(
                results['metadatas'][0],
                results['distances'][0]
            ):
                # Convert distance to similarity score
                similarity_score = max(0, 1 - distance)
                
                recommendations.append({
                    'product_id': metadata['product_id'],
                    'similarity_score': round(similarity_score, 3),
                    'recommendation_reason': self._generate_user_recommendation_reason(
                        metadata, similarity_score
                    )
                })
                
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to search by user preferences: {e}")
            return []
            
    async def search_by_nutrition_filter(
        self, 
        nutrition_filters: Dict[str, Any], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for products based on nutrition criteria.
        
        Args:
            nutrition_filters: Dictionary with nutrition criteria
                e.g., {"energy": {"$lt": 200}, "protein": {"$gt": 10}}
            limit: Maximum number of products to return
            
        Returns:
            List of products matching nutrition criteria
        """
        if not self.is_chromadb_available():
            logger.warning("ChromaDB not available for nutrition filter search")
            return []
            
        try:
            # Build where clause for ChromaDB
            where_clause = {}
            for key, condition in nutrition_filters.items():
                if isinstance(condition, dict):
                    for operator, value in condition.items():
                        where_clause[key] = {operator: value}
                else:
                    where_clause[key] = condition
            
            # Query with filters
            results = self.collection.get(
                where=where_clause,
                limit=limit,
                include=['metadatas']
            )
            
            filtered_products = []
            for metadata in results['metadatas']:
                filtered_products.append({
                    'product_id': metadata['product_id'],
                    'product_name': metadata.get('product_name', ''),
                    'energy': metadata.get('energy', 0),
                    'protein': metadata.get('protein', 0),
                    'fat': metadata.get('fat', 0),
                    'carbohydrate': metadata.get('carbohydrate', 0),
                    'sodium': metadata.get('sodium', 0)
                })
                
            return filtered_products
            
        except Exception as e:
            logger.error(f"Failed to search by nutrition filter: {e}")
            return []
            
    def _generate_recommendation_reason(
        self, 
        metadata: Dict[str, Any], 
        similarity_score: float
    ) -> str:
        """Generate recommendation reason for product-based recommendations."""
        if similarity_score > 0.9:
            return "영양성분과 원재료가 매우 유사"
        elif similarity_score > 0.8:
            return "영양성분이 유사한 제품"
        elif similarity_score > 0.7:
            return "원재료가 비슷한 제품"
        else:
            return "관련 제품"
            
    def _generate_user_recommendation_reason(
        self, 
        metadata: Dict[str, Any], 
        similarity_score: float
    ) -> str:
        """Generate recommendation reason for user-based recommendations."""
        if similarity_score > 0.9:
            return "사용자가 선호하는 제품과 매우 유사한 영양성분"
        elif similarity_score > 0.8:
            return "사용자 취향에 맞는 제품"
        elif similarity_score > 0.7:
            return "사용자가 관심있어 할 만한 제품"
        elif similarity_score > 0.6:
            return "사용자 선호도와 유사한 제품"
        else:
            return "사용자 관심사와 관련된 제품"