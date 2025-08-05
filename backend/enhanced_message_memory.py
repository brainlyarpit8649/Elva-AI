"""
Enhanced Message Memory System for Elva AI
Unified high-performance memory system combining MongoDB for persistent storage with Redis for fast caching.
Replaces both message_memory.py and conversation_memory.py for simplified, stable architecture.
Provides context-aware conversations with optimized database operations and comprehensive error handling.
"""

from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import redis
import json
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import uuid

logger = logging.getLogger(__name__)

class EnhancedMessageMemory:
    def __init__(self):
        # MongoDB setup with optimized connection pool settings
        self.mongo_url = os.environ.get('MONGO_URL')
        self.mongo_client = AsyncIOMotorClient(
            self.mongo_url,
            maxPoolSize=25,  # Increased pool size for high performance
            minPoolSize=5,   # Minimum connections kept alive
            maxIdleTimeMS=30000,  # Keep connections for 30 seconds
            connectTimeoutMS=5000,  # 5 second connection timeout
            serverSelectionTimeoutMS=10000,  # 10 second server selection timeout
            socketTimeoutMS=20000,  # 20 second socket timeout
            heartbeatFrequencyMS=10000,  # Health check every 10 seconds
            retryWrites=True,  # Enable retry writes for resilience
            w="majority"  # Write concern for data safety
        )
        
        self.db = self.mongo_client[os.environ.get('DB_NAME', 'test_database')]
        self.messages_collection = self.db["enhanced_messages"]
        
        # Redis setup
        self.redis_client = None
        self.redis_connected = False
        
        # Performance Configuration (Optimized for User Requirements)
        self.CONTEXT_MEMORY_LIMIT = 100  # Fetch last 100+ messages from MongoDB for long-term context
        self.REDIS_CACHE_LIMIT = 30     # Cache last 30 messages in Redis for short-term speed
        self.REDIS_TTL_SECONDS = 3600    # 1 hour Redis cache TTL
        self.MONGO_TTL_DAYS = 30         # 30 days MongoDB retention
        self.MAX_CONTEXT_CHARS = 12000   # Maximum context size for AI
        
        # Timeout Configuration (From message_memory.py optimizations)
        self.MAX_TIMEOUT = 15.0  # Maximum timeout for any operation
        self.DEFAULT_TIMEOUT = 8.0  # Default timeout for most operations
        self.DB_OPERATION_TIMEOUT = 12.0  # Database operation timeout
        
        # Connection state tracking
        self._indexes_created = False
        self._redis_initialized = False
        self._connection_tested = False

    async def initialize(self):
        """Initialize MongoDB indexes and Redis connection"""
        try:
            await self._ensure_mongo_indexes()
            await self._initialize_redis()
            await self._test_connection()
            logger.info("✅ Enhanced Message Memory System initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Enhanced Message Memory: {e}")
            return False

    async def _safe_db_operation(self, operation_func, *args, timeout: float = None, **kwargs):
        """
        Safely execute database operations with timeout and retry logic.
        Enhanced version from message_memory.py optimizations.
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        max_retries = 2
        base_delay = 0.1
        
        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    operation_func(*args, **kwargs), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                if attempt == max_retries:
                    logger.error(f"❌ Database operation timed out after {max_retries} retries (timeout: {timeout}s)")
                    return None
                await asyncio.sleep(base_delay * (2 ** attempt))  # Exponential backoff
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"❌ Database operation failed after {max_retries} retries: {e}")
                    return None
                await asyncio.sleep(base_delay * (2 ** attempt))
        
        return None

    async def _test_connection(self):
        """Test MongoDB connection health"""
        if self._connection_tested:
            return True
            
        try:
            await asyncio.wait_for(self.db.admin.command('ping'), timeout=5.0)
            self._connection_tested = True
            logger.info("✅ MongoDB connection verified")
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB connection test failed: {e}")
            return False

    async def _ensure_mongo_indexes(self):
        """Create optimized MongoDB indexes"""
        if self._indexes_created:
            return
            
        try:
            # TTL index for automatic cleanup
            await self.messages_collection.create_index(
                "timestamp",
                expireAfterSeconds=self.MONGO_TTL_DAYS * 24 * 3600,
                background=True,
                name="message_ttl_index"
            )
            
            # Primary query index: session + timestamp
            await self.messages_collection.create_index(
                [("session_id", 1), ("timestamp", 1)],
                background=True,
                name="session_timestamp_index"
            )
            
            # Role filtering index
            await self.messages_collection.create_index(
                [("session_id", 1), ("role", 1), ("timestamp", 1)],
                background=True,
                name="session_role_timestamp_index"
            )
            
            # Content search index
            await self.messages_collection.create_index(
                [("content", "text")],
                background=True,
                name="content_search_index"
            )
            
            self._indexes_created = True
            logger.info("✅ MongoDB indexes created for enhanced message memory")
            
        except Exception as e:
            logger.error(f"❌ Error creating MongoDB indexes: {e}")

    async def _initialize_redis(self):
        """Initialize Redis connection with fallback handling"""
        if self._redis_initialized:
            return
            
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            # Use standard redis library with connection pooling
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
                retry_on_timeout=True,
                socket_connect_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            self.redis_connected = True
            self._redis_initialized = True
            logger.info("✅ Redis connection established for message caching")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable, using MongoDB only: {e}")
            self.redis_connected = False
            self._redis_initialized = True  # Mark as initialized even if failed

    async def save_message(self, session_id: str, role: str, content: str, metadata: Dict = None) -> bool:
        """
        Save message to both MongoDB and Redis cache with enhanced error handling and duplicate detection
        """
        try:
            # Ensure connection and indexes are ready
            if not await self._test_connection():
                logger.warning("⚠️ Database connection not available")
                return False
            
            # Check for duplicates with optimized query
            existing = await self._safe_db_operation(
                self.messages_collection.find_one,
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content
                },
                timeout=5.0
            )

            if existing:
                logger.info(f"⚠️ Duplicate message ignored for session {session_id}")
                return True  # Return True since message already exists
                
            # Prepare message document
            message_doc = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {},
                "indexed": True,
                "message_id": str(uuid.uuid4())  # Unique message ID for tracking
            }
            
            # Save to MongoDB with safe operation wrapper
            mongo_result = await self._safe_db_operation(
                self.messages_collection.insert_one,
                message_doc,
                timeout=8.0
            )
            
            if not mongo_result or not mongo_result.inserted_id:
                logger.error(f"❌ Failed to save message to MongoDB for session {session_id}")
                return False
            
            # Cache in Redis for fast retrieval (with fallback)
            if self.redis_connected:
                await self._cache_message_in_redis(session_id, message_doc)
            
            logger.info(f"💾 Saved {role} message for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")
            return False

    async def _cache_message_in_redis(self, session_id: str, message_doc: Dict):
        """Cache recent messages in Redis for fast access"""
        try:
            # Convert datetime to ISO string for JSON serialization
            cache_doc = message_doc.copy()
            cache_doc["timestamp"] = message_doc["timestamp"].isoformat()
            
            # Add to Redis list (latest messages at the beginning)
            redis_key = f"session_messages:{session_id}"
            
            # Execute Redis operations in thread pool
            loop = asyncio.get_event_loop()
            
            # Add new message to the beginning of the list
            await loop.run_in_executor(None, self.redis_client.lpush, redis_key, json.dumps(cache_doc))
            
            # Trim to keep only recent messages  
            await loop.run_in_executor(None, self.redis_client.ltrim, redis_key, 0, self.REDIS_CACHE_LIMIT - 1)
            
            # Set expiration
            await loop.run_in_executor(None, self.redis_client.expire, redis_key, self.REDIS_TTL_SECONDS)
            
        except Exception as e:
            logger.warning(f"⚠️ Error caching message in Redis: {e}")

    async def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history with Redis caching, MongoDB fallback, and enhanced error handling
        """
        try:
            message_limit = limit or self.CONTEXT_MEMORY_LIMIT
            
            # Ensure connection is available
            if not await self._test_connection():
                logger.warning("⚠️ Database not available for history retrieval")
                return []
            
            # Try Redis cache first for recent messages (optimized path)
            if self.redis_connected and message_limit <= self.REDIS_CACHE_LIMIT:
                cached_messages = await self._get_cached_messages(session_id, message_limit)
                if cached_messages:
                    logger.info(f"🚀 Retrieved {len(cached_messages)} cached messages from Redis")
                    return cached_messages
            
            # Fallback to MongoDB with safe operation wrapper
            messages = await self._get_messages_from_mongodb(session_id, message_limit)
            
            # Cache the results in Redis for future requests (background task)
            if self.redis_connected and messages:
                asyncio.create_task(self._update_redis_cache(session_id, messages[:self.REDIS_CACHE_LIMIT]))
            
            logger.info(f"📖 Retrieved {len(messages)} messages from MongoDB for session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error retrieving conversation history: {e}")
            return []

    async def _get_cached_messages(self, session_id: str, limit: int) -> Optional[List[Dict]]:
        """Get messages from Redis cache"""
        try:
            redis_key = f"session_messages:{session_id}"
            
            # Execute Redis operations in thread pool
            loop = asyncio.get_event_loop()
            cached_data = await loop.run_in_executor(None, self.redis_client.lrange, redis_key, 0, limit - 1)
            
            if not cached_data:
                return None
            
            messages = []
            for msg_json in reversed(cached_data):  # Reverse to get chronological order
                try:
                    msg = json.loads(msg_json)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
            
            return messages
            
        except Exception as e:
            logger.warning(f"⚠️ Error getting cached messages: {e}")
            return None

    async def _get_messages_from_mongodb(self, session_id: str, limit: int) -> List[Dict]:
        """Get messages from MongoDB with optimized query and safe operation wrapper"""
        try:
            # Use optimized query with projection for better performance
            cursor = self.messages_collection.find(
                {"session_id": session_id},
                {
                    "session_id": 1,
                    "role": 1,
                    "content": 1,
                    "timestamp": 1,
                    "metadata": 1,
                    "_id": 0  # Exclude _id for better performance
                }
            ).sort("timestamp", 1).limit(limit)
            
            # Execute with safe operation wrapper
            messages = await self._safe_db_operation(
                cursor.to_list,
                length=None,
                timeout=self.DB_OPERATION_TIMEOUT
            )
            
            if messages is None:
                logger.warning(f"⚠️ MongoDB query timed out for session {session_id}")
                return []
            
            # Optimize timestamp conversion
            for msg in messages:
                if isinstance(msg.get("timestamp"), datetime):
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error querying MongoDB: {e}")
            return []

    async def _update_redis_cache(self, session_id: str, messages: List[Dict]):
        """Update Redis cache with fresh messages from MongoDB"""
        try:
            redis_key = f"session_messages:{session_id}"
            
            # Execute Redis operations in thread pool
            loop = asyncio.get_event_loop()
            
            # Clear existing cache
            await loop.run_in_executor(None, self.redis_client.delete, redis_key)
            
            # Add messages in reverse order (newest first in Redis)
            for msg in reversed(messages):
                await loop.run_in_executor(None, self.redis_client.lpush, redis_key, json.dumps(msg))
            
            # Set expiration
            await loop.run_in_executor(None, self.redis_client.expire, redis_key, self.REDIS_TTL_SECONDS)
            
        except Exception as e:
            logger.warning(f"⚠️ Error updating Redis cache: {e}")

    async def get_context_for_ai(self, session_id: str, max_chars: int = None) -> str:
        """
        Get formatted conversation context optimized for AI consumption
        """
        try:
            max_chars = max_chars or self.MAX_CONTEXT_CHARS
            
            # Get conversation history
            history = await self.get_conversation_history(session_id, self.CONTEXT_MEMORY_LIMIT)
            
            if not history:
                return "No previous conversation context available."
            
            # Build context with size optimization
            context_parts = ["=== CONVERSATION CONTEXT ==="]
            total_chars = len(context_parts[0])
            
            # Start from recent messages and work backwards
            for msg in reversed(history):
                role = msg["role"].upper()
                content = msg["content"]
                timestamp = msg.get("timestamp", "")
                
                # Format timestamp
                if timestamp and "T" in timestamp:
                    timestamp = timestamp.split("T")[0] + " " + timestamp.split("T")[1][:8]
                
                message_line = f"[{timestamp}] {role}: {content}"
                
                # Check size limit
                if total_chars + len(message_line) + 50 > max_chars:  # Leave room for footer
                    break
                
                context_parts.insert(1, message_line)  # Insert at beginning for chronological order
                total_chars += len(message_line)
            
            context_parts.append("=== END CONTEXT ===")
            context_parts.append(f"[Total messages: {len(context_parts)-2}]")
            
            full_context = "\n".join(context_parts)
            
            logger.info(f"📋 Built AI context: {len(full_context)} chars, {len(context_parts)-2} messages")
            return full_context
            
        except Exception as e:
            logger.error(f"❌ Error building context for AI: {e}")
            return "Error building conversation context."

    async def search_conversations(self, session_id: str, query: str, limit: int = 20) -> List[Dict]:
        """Search conversation messages using text index"""
        try:
            if not query.strip():
                return []
                
            cursor = self.messages_collection.find(
                {
                    "session_id": session_id,
                    "$text": {"$search": query}
                },
                {
                    "score": {"$meta": "textScore"},
                    "session_id": 1,
                    "role": 1,
                    "content": 1,
                    "timestamp": 1,
                    "_id": 0
                }
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = await asyncio.wait_for(
                cursor.to_list(length=None),
                timeout=10.0
            )
            
            # Convert timestamps
            for result in results:
                if isinstance(result.get("timestamp"), datetime):
                    result["timestamp"] = result["timestamp"].isoformat()
            
            logger.info(f"🔍 Found {len(results)} search results for query: {query[:50]}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching conversations: {e}")
            return []

    async def clear_session_history(self, session_id: str) -> bool:
        """Clear conversation history for a session"""
        try:
            # Clear MongoDB
            mongo_result = await self.messages_collection.delete_many(
                {"session_id": session_id}
            )
            
            # Clear Redis cache
            if self.redis_connected:
                redis_key = f"session_messages:{session_id}"
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.redis_client.delete, redis_key)
            
            logger.info(f"🗑️ Cleared {mongo_result.deleted_count} messages for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing session history: {e}")
            return False

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a conversation session"""
        try:
            # Count total messages
            total_count = await self.messages_collection.count_documents(
                {"session_id": session_id}
            )
            
            # Count by role
            user_count = await self.messages_collection.count_documents(
                {"session_id": session_id, "role": "user"}
            )
            
            assistant_count = await self.messages_collection.count_documents(
                {"session_id": session_id, "role": "assistant"}
            )
            
            # Get first and last message timestamps
            first_msg = await self.messages_collection.find_one(
                {"session_id": session_id},
                sort=[("timestamp", 1)]
            )
            
            last_msg = await self.messages_collection.find_one(
                {"session_id": session_id},
                sort=[("timestamp", -1)]
            )
            
            return {
                "session_id": session_id,
                "total_messages": total_count,
                "user_messages": user_count,
                "assistant_messages": assistant_count,
                "first_message": first_msg.get("timestamp").isoformat() if first_msg else None,
                "last_message": last_msg.get("timestamp").isoformat() if last_msg else None,
                "redis_cache_available": self.redis_connected
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting session stats: {e}")
            return {"session_id": session_id, "error": str(e)}

    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old conversation sessions"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self.messages_collection.delete_many(
                {"timestamp": {"$lt": cutoff_date}}
            )
            
            logger.info(f"🧹 Cleaned up {result.deleted_count} old messages")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old sessions: {e}")
            return 0

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the memory system"""
        try:
            # Test MongoDB
            mongo_healthy = False
            try:
                await self.db.admin.command('ping')
                mongo_healthy = True
            except:
                pass
            
            # Test Redis
            redis_healthy = False
            if self.redis_connected:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.redis_client.ping)
                    redis_healthy = True
                except:
                    self.redis_connected = False
            
            return {
                "mongodb_connected": mongo_healthy,
                "redis_connected": redis_healthy,
                "indexes_created": self._indexes_created,
                "context_memory_limit": self.CONTEXT_MEMORY_LIMIT,
                "redis_cache_limit": self.REDIS_CACHE_LIMIT,
                "status": "healthy" if mongo_healthy else "degraded"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global instance
_enhanced_memory: Optional[EnhancedMessageMemory] = None

async def get_enhanced_memory() -> EnhancedMessageMemory:
    """Get or create the global enhanced memory instance"""
    global _enhanced_memory
    if _enhanced_memory is None:
        _enhanced_memory = EnhancedMessageMemory()
        await _enhanced_memory.initialize()
    return _enhanced_memory

async def initialize_enhanced_message_memory() -> EnhancedMessageMemory:
    """Initialize the enhanced message memory system"""
    try:
        memory = await get_enhanced_memory()
        logger.info("✅ Enhanced Message Memory System ready")
        return memory
    except Exception as e:
        logger.error(f"❌ Failed to initialize Enhanced Message Memory System: {e}")
        raise