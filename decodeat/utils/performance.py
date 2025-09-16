"""
Performance monitoring and optimization utilities.
"""
import time
import asyncio
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import asynccontextmanager

from decodeat.utils.logging import LoggingService

logger = LoggingService(__name__)


class PerformanceMonitor:
    """Performance monitoring utility."""
    
    def __init__(self):
        self.metrics = {}
        
    def record_metric(self, name: str, value: float, unit: str = "ms"):
        """Record a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'unit': unit,
            'timestamp': time.time()
        })
        
    def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a metric."""
        if name not in self.metrics:
            return {}
            
        values = [m['value'] for m in self.metrics[name]]
        
        if not values:
            return {}
            
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'total': sum(values),
            'unit': self.metrics[name][0]['unit'] if self.metrics[name] else 'ms'
        }
        
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all metrics."""
        return {name: self.get_metric_stats(name) for name in self.metrics.keys()}
        
    def clear_metrics(self):
        """Clear all recorded metrics."""
        self.metrics.clear()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def measure_time(metric_name: str):
    """Decorator to measure function execution time."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    performance_monitor.record_metric(metric_name, duration_ms)
                    logger.debug(f"{metric_name}: {duration_ms:.2f}ms")
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    performance_monitor.record_metric(metric_name, duration_ms)
                    logger.debug(f"{metric_name}: {duration_ms:.2f}ms")
            return sync_wrapper
    return decorator


@asynccontextmanager
async def measure_async_operation(metric_name: str):
    """Context manager to measure async operation time."""
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        performance_monitor.record_metric(metric_name, duration_ms)
        logger.debug(f"{metric_name}: {duration_ms:.2f}ms")


class VectorSearchOptimizer:
    """Optimizer for vector search operations."""
    
    @staticmethod
    def optimize_query_params(
        n_results: int, 
        collection_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Optimize ChromaDB query parameters based on collection size."""
        params = {}
        
        # Optimize n_results based on collection size
        if collection_size:
            # Don't query more than 50% of collection for performance
            max_results = max(10, min(n_results, collection_size // 2))
            params['n_results'] = max_results
        else:
            params['n_results'] = min(n_results, 100)  # Cap at 100 for performance
            
        return params
        
    @staticmethod
    def should_use_batch_processing(item_count: int, threshold: int = 50) -> bool:
        """Determine if batch processing should be used."""
        return item_count > threshold
        
    @staticmethod
    async def batch_vector_operations(
        items: list, 
        operation: Callable, 
        batch_size: int = 10
    ) -> list:
        """Process vector operations in batches for better performance."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[operation(item) for item in batch],
                return_exceptions=True
            )
            
            # Filter out exceptions and log them
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch operation failed for item {i + j}: {result}")
                else:
                    results.append(result)
                    
        return results


class RecommendationCache:
    """Simple in-memory cache for recommendations."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
    def _generate_key(self, **kwargs) -> str:
        """Generate cache key from parameters."""
        key_parts = []
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (list, dict)):
                key_parts.append(f"{k}:{hash(str(v))}")
            else:
                key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)
        
    def get(self, **kwargs) -> Optional[Any]:
        """Get cached result."""
        key = self._generate_key(**kwargs)
        
        if key in self.cache:
            result, timestamp = self.cache[key]
            
            # Check if cache entry is still valid
            if time.time() - timestamp < self.ttl_seconds:
                logger.debug(f"Cache hit for key: {key}")
                return result
            else:
                # Remove expired entry
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")
                
        return None
        
    def set(self, result: Any, **kwargs):
        """Set cached result."""
        key = self._generate_key(**kwargs)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            
        self.cache[key] = (result, time.time())
        logger.debug(f"Cache set for key: {key}")
        
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.debug("Cache cleared")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1 for _, timestamp in self.cache.values()
            if current_time - timestamp < self.ttl_seconds
        )
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self.cache) - valid_entries,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }


# Global recommendation cache instance
recommendation_cache = RecommendationCache()