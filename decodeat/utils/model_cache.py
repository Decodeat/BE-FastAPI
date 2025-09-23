"""
Global model cache for sentence transformers to avoid repeated loading
"""
import os
import threading
from typing import Optional
from sentence_transformers import SentenceTransformer
from decodeat.utils.logging import LoggingService

logger = LoggingService(__name__)

class ModelCache:
    """Global cache for sentence transformer models"""
    
    _instance = None
    _lock = threading.Lock()
    _model = None
    _model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelCache, cls).__new__(cls)
        return cls._instance
    
    def get_model(self) -> Optional[SentenceTransformer]:
        """Get cached model or load if not available"""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        logger.info(f"Loading sentence transformer model: {self._model_name}")
                        
                        # Set cache directory to avoid repeated downloads
                        cache_dir = os.environ.get('SENTENCE_TRANSFORMERS_HOME', '/tmp/sentence_transformers')
                        os.makedirs(cache_dir, exist_ok=True)
                        
                        # Load model with caching
                        self._model = SentenceTransformer(
                            self._model_name,
                            cache_folder=cache_dir
                        )
                        
                        logger.info("Sentence transformer model loaded and cached successfully")
                        
                    except Exception as e:
                        logger.error(f"Failed to load sentence transformer model: {e}")
                        return None
        
        return self._model
    
    def is_model_loaded(self) -> bool:
        """Check if model is already loaded"""
        return self._model is not None
    
    def clear_cache(self):
        """Clear cached model (for testing purposes)"""
        with self._lock:
            self._model = None
            logger.info("Model cache cleared")

# Global instance
model_cache = ModelCache()