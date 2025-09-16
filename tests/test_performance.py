"""
Performance and optimization tests.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from decodeat.utils.performance import (
    PerformanceMonitor, 
    measure_time, 
    VectorSearchOptimizer,
    RecommendationCache,
    performance_monitor,
    recommendation_cache
)


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
        
    def test_record_metric(self):
        """Test metric recording."""
        self.monitor.record_metric("test_metric", 100.5, "ms")
        
        assert "test_metric" in self.monitor.metrics
        assert len(self.monitor.metrics["test_metric"]) == 1
        assert self.monitor.metrics["test_metric"][0]["value"] == 100.5
        assert self.monitor.metrics["test_metric"][0]["unit"] == "ms"
        
    def test_get_metric_stats(self):
        """Test metric statistics calculation."""
        # Record multiple values
        values = [100, 200, 150, 300, 250]
        for value in values:
            self.monitor.record_metric("test_metric", value)
            
        stats = self.monitor.get_metric_stats("test_metric")
        
        assert stats["count"] == 5
        assert stats["min"] == 100
        assert stats["max"] == 300
        assert stats["avg"] == 200
        assert stats["total"] == 1000
        
    def test_get_metric_stats_empty(self):
        """Test statistics for non-existent metric."""
        stats = self.monitor.get_metric_stats("nonexistent")
        assert stats == {}
        
    def test_clear_metrics(self):
        """Test clearing all metrics."""
        self.monitor.record_metric("test1", 100)
        self.monitor.record_metric("test2", 200)
        
        assert len(self.monitor.metrics) == 2
        
        self.monitor.clear_metrics()
        
        assert len(self.monitor.metrics) == 0


class TestMeasureTimeDecorator:
    """Test time measurement decorator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        performance_monitor.clear_metrics()
        
    def test_measure_sync_function(self):
        """Test measuring synchronous function."""
        @measure_time("sync_test")
        def slow_function():
            time.sleep(0.01)  # 10ms
            return "result"
            
        result = slow_function()
        
        assert result == "result"
        stats = performance_monitor.get_metric_stats("sync_test")
        assert stats["count"] == 1
        assert stats["avg"] >= 10  # At least 10ms
        
    @pytest.mark.asyncio
    async def test_measure_async_function(self):
        """Test measuring asynchronous function."""
        @measure_time("async_test")
        async def slow_async_function():
            await asyncio.sleep(0.01)  # 10ms
            return "async_result"
            
        result = await slow_async_function()
        
        assert result == "async_result"
        stats = performance_monitor.get_metric_stats("async_test")
        assert stats["count"] == 1
        assert stats["avg"] >= 10  # At least 10ms


class TestVectorSearchOptimizer:
    """Test vector search optimization."""
    
    def test_optimize_query_params_with_collection_size(self):
        """Test query parameter optimization with known collection size."""
        # Small collection
        params = VectorSearchOptimizer.optimize_query_params(100, collection_size=50)
        assert params["n_results"] == 25  # 50% of collection
        
        # Large collection
        params = VectorSearchOptimizer.optimize_query_params(10, collection_size=1000)
        assert params["n_results"] == 10  # Original request
        
        # Very large collection
        params = VectorSearchOptimizer.optimize_query_params(200, collection_size=1000)
        assert params["n_results"] == 200  # 50% of collection
        
    def test_optimize_query_params_without_collection_size(self):
        """Test query parameter optimization without collection size."""
        params = VectorSearchOptimizer.optimize_query_params(50)
        assert params["n_results"] == 50
        
        params = VectorSearchOptimizer.optimize_query_params(150)
        assert params["n_results"] == 100  # Capped at 100
        
    def test_should_use_batch_processing(self):
        """Test batch processing decision."""
        assert not VectorSearchOptimizer.should_use_batch_processing(10)
        assert not VectorSearchOptimizer.should_use_batch_processing(50)
        assert VectorSearchOptimizer.should_use_batch_processing(51)
        assert VectorSearchOptimizer.should_use_batch_processing(100)
        
    @pytest.mark.asyncio
    async def test_batch_vector_operations(self):
        """Test batch processing of vector operations."""
        async def mock_operation(item):
            await asyncio.sleep(0.001)  # Simulate work
            return item * 2
            
        items = list(range(25))  # 25 items
        results = await VectorSearchOptimizer.batch_vector_operations(
            items, mock_operation, batch_size=10
        )
        
        assert len(results) == 25
        assert results == [i * 2 for i in range(25)]
        
    @pytest.mark.asyncio
    async def test_batch_vector_operations_with_errors(self):
        """Test batch processing with some operations failing."""
        async def mock_operation_with_errors(item):
            if item == 5:
                raise ValueError("Test error")
            return item * 2
            
        items = list(range(10))
        results = await VectorSearchOptimizer.batch_vector_operations(
            items, mock_operation_with_errors, batch_size=5
        )
        
        # Should have 9 results (10 - 1 error)
        assert len(results) == 9
        assert 10 not in results  # Item 5 * 2 should not be in results


class TestRecommendationCache:
    """Test recommendation caching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = RecommendationCache(max_size=3, ttl_seconds=1)
        
    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        result = {"recommendations": [1, 2, 3]}
        
        # Set cache
        self.cache.set(result, user_id=123, limit=10)
        
        # Get from cache
        cached_result = self.cache.get(user_id=123, limit=10)
        assert cached_result == result
        
    def test_cache_miss(self):
        """Test cache miss."""
        result = self.cache.get(user_id=999, limit=10)
        assert result is None
        
    def test_cache_expiration(self):
        """Test cache expiration."""
        result = {"recommendations": [1, 2, 3]}
        
        # Set cache
        self.cache.set(result, user_id=123, limit=10)
        
        # Should be available immediately
        cached_result = self.cache.get(user_id=123, limit=10)
        assert cached_result == result
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        cached_result = self.cache.get(user_id=123, limit=10)
        assert cached_result is None
        
    def test_cache_size_limit(self):
        """Test cache size limit."""
        # Fill cache to capacity
        for i in range(3):
            self.cache.set(f"result_{i}", user_id=i, limit=10)
            
        assert len(self.cache.cache) == 3
        
        # Add one more (should evict oldest)
        self.cache.set("result_3", user_id=3, limit=10)
        
        assert len(self.cache.cache) == 3
        
        # First entry should be evicted
        cached_result = self.cache.get(user_id=0, limit=10)
        assert cached_result is None
        
        # Last entry should still be there
        cached_result = self.cache.get(user_id=3, limit=10)
        assert cached_result == "result_3"
        
    def test_cache_key_generation(self):
        """Test cache key generation with different parameter types."""
        result1 = {"test": 1}
        result2 = {"test": 2}
        
        # Different user_id should create different keys
        self.cache.set(result1, user_id=1, limit=10)
        self.cache.set(result2, user_id=2, limit=10)
        
        assert self.cache.get(user_id=1, limit=10) == result1
        assert self.cache.get(user_id=2, limit=10) == result2
        
        # Same parameters should return same result
        assert self.cache.get(user_id=1, limit=10) == result1
        
    def test_cache_stats(self):
        """Test cache statistics."""
        # Add some entries
        self.cache.set("result1", user_id=1)
        self.cache.set("result2", user_id=2)
        
        stats = self.cache.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 0
        assert stats["max_size"] == 3
        assert stats["ttl_seconds"] == 1
        
    def test_cache_clear(self):
        """Test cache clearing."""
        self.cache.set("result1", user_id=1)
        self.cache.set("result2", user_id=2)
        
        assert len(self.cache.cache) == 2
        
        self.cache.clear()
        
        assert len(self.cache.cache) == 0


if __name__ == "__main__":
    pytest.main([__file__])