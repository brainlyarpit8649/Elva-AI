"""
Performance Optimization Module for Elva AI
Provides caching, async processing, and response time optimizations.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    def __init__(self):
        # Response cache for frequently asked questions
        self.response_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Query optimization
        self.query_patterns = {}
        self.performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "avg_response_time": 0,
            "slow_queries": []
        }
    
    async def optimize_chat_processing(self, request_data: Dict) -> Tuple[bool, Optional[Dict]]:
        """Optimize chat processing with caching and fast paths"""
        try:
            start_time = time.time()
            
            # Check cache for similar queries
            cache_key = self._generate_cache_key(request_data.get("message", ""))
            cached_response = self._get_cached_response(cache_key)
            
            if cached_response:
                self.performance_stats["cache_hits"] += 1
                logger.info(f"🚀 Cache hit for query: {request_data.get('message', '')[:50]}...")
                return True, cached_response
            
            # Track performance
            self.performance_stats["total_requests"] += 1
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)
            
            return False, None
            
        except Exception as e:
            logger.error(f"❌ Error in chat processing optimization: {e}")
            return False, None
    
    def cache_response(self, message: str, response_data: Dict):
        """Cache response for future use"""
        try:
            cache_key = self._generate_cache_key(message)
            self.response_cache[cache_key] = {
                "data": response_data,
                "timestamp": datetime.utcnow(),
                "hits": 0
            }
            
            # Clean old cache entries
            self._cleanup_cache()
            
        except Exception as e:
            logger.error(f"❌ Error caching response: {e}")
    
    def _generate_cache_key(self, message: str) -> str:
        """Generate cache key for message"""
        # Normalize message for better cache hits
        normalized = message.lower().strip()
        
        # Remove personal identifiers for better cache sharing
        common_patterns = ["my name is", "i am", "call me"]
        for pattern in common_patterns:
            if pattern in normalized:
                normalized = pattern + " [USER]"
                break
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if valid"""
        if cache_key in self.response_cache:
            cache_entry = self.response_cache[cache_key]
            
            # Check if cache is still valid
            time_diff = (datetime.utcnow() - cache_entry["timestamp"]).seconds
            if time_diff < self.cache_ttl:
                cache_entry["hits"] += 1
                return cache_entry["data"]
            else:
                # Remove expired cache
                del self.response_cache[cache_key]
        
        return None
    
    def _cleanup_cache(self):
        """Remove old cache entries"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, entry in self.response_cache.items():
            time_diff = (current_time - entry["timestamp"]).seconds
            if time_diff > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.response_cache[key]
        
        # Also limit cache size
        if len(self.response_cache) > 100:  # Max 100 cached responses
            # Remove least recently used
            sorted_cache = sorted(
                self.response_cache.items(),
                key=lambda x: x[1]["hits"],
                reverse=True
            )
            
            # Keep top 80 most used
            self.response_cache = dict(sorted_cache[:80])
    
    def _update_performance_stats(self, processing_time: float):
        """Update performance statistics"""
        # Update average response time
        total = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_response_time"]
        new_avg = ((current_avg * (total - 1)) + processing_time) / total
        self.performance_stats["avg_response_time"] = new_avg
        
        # Track slow queries
        if processing_time > 2.0:  # Queries taking more than 2 seconds
            self.performance_stats["slow_queries"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time": processing_time
            })
            
            # Keep only last 20 slow queries
            if len(self.performance_stats["slow_queries"]) > 20:
                self.performance_stats["slow_queries"] = self.performance_stats["slow_queries"][-20:]
    
    async def optimize_memory_operations(self, operation: str, data: Any) -> Tuple[bool, Any]:
        """Optimize memory operations for better performance"""
        try:
            start_time = time.time()
            
            # Fast path for common memory operations
            if operation == "recall" and isinstance(data, str):
                # Check if this is a simple recall that we can optimize
                optimized_result = await self._optimize_recall_operation(data)
                if optimized_result:
                    processing_time = time.time() - start_time
                    logger.info(f"⚡ Optimized memory recall in {processing_time:.3f}s")
                    return True, optimized_result
            
            return False, None
            
        except Exception as e:
            logger.error(f"❌ Error optimizing memory operations: {e}")
            return False, None
    
    async def _optimize_recall_operation(self, query: str) -> Optional[Dict]:
        """Optimize memory recall operations"""
        try:
            # Simple pattern matching for common queries
            query_lower = query.lower()
            
            if "what's my name" in query_lower or "my name" in query_lower:
                # This is a name query - can be optimized
                return {
                    "optimized": True,
                    "query_type": "name_query",
                    "fast_response": "Let me check what name information I have for you..."
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in recall optimization: {e}")
            return None
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        return {
            "cache_stats": {
                "total_cached_responses": len(self.response_cache),
                "cache_hit_ratio": self.performance_stats["cache_hits"] / max(self.performance_stats["total_requests"], 1) * 100,
                "cache_ttl_minutes": self.cache_ttl / 60
            },
            "performance_stats": self.performance_stats.copy()
        }
    
    async def preload_common_responses(self):
        """Preload responses for common queries"""
        try:
            common_queries = [
                "hello",
                "hi",
                "what's my name",
                "who am i",
                "what do you remember about me",
                "help",
                "thank you"
            ]
            
            # Pre-generate cache keys for common queries
            for query in common_queries:
                cache_key = self._generate_cache_key(query)
                # Pre-populate with placeholder that will be replaced with real responses
                self.response_cache[cache_key] = {
                    "preloaded": True,
                    "timestamp": datetime.utcnow()
                }
            
            logger.info(f"✅ Preloaded {len(common_queries)} common query patterns")
            
        except Exception as e:
            logger.error(f"❌ Error preloading common responses: {e}")


# Global performance optimizer instance
performance_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get or create the global performance optimizer instance"""
    global performance_optimizer
    if performance_optimizer is None:
        performance_optimizer = PerformanceOptimizer()
    return performance_optimizer

async def initialize_performance_optimizer() -> PerformanceOptimizer:
    """Initialize performance optimizer"""
    try:
        optimizer = get_performance_optimizer()
        await optimizer.preload_common_responses()
        logger.info("✅ Performance optimizer initialized")
        return optimizer
    except Exception as e:
        logger.error(f"❌ Failed to initialize performance optimizer: {e}")
        raise