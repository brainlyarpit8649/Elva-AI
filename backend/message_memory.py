from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Initialize MongoDB client with optimized settings
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=25,  # Increased pool size
    minPoolSize=5,   # Minimum connections
    maxIdleTimeMS=30000,  # Keep connections for 30s
    connectTimeoutMS=5000,  # 5s connection timeout
    serverSelectionTimeoutMS=10000,  # 10s server selection
    socketTimeoutMS=20000,  # 20s socket timeout
    heartbeatFrequencyMS=10000,  # Health check every 10s
    retryWrites=True,  # Enable retry writes
    w="majority"  # Write concern
)

db = client[os.environ.get('DB_NAME', 'test_database')]
messages_collection = db["messages"]

# Configuration
MEMORY_LIMIT = int(os.environ.get("MEMORY_MESSAGE_LIMIT", 45))
TTL_SECONDS = int(os.environ.get("MEMORY_TTL_SECONDS", 172800))  # 2 days
MAX_TIMEOUT = 15.0  # Maximum timeout for any operation
DEFAULT_TIMEOUT = 8.0  # Default timeout for most operations

# Global connection state tracking
_indexes_created = False
_connection_tested = False

# -----------------------------
# Optimized Index Setup
# -----------------------------
async def ensure_indexes():
    """Create optimized indexes for better query performance"""
    global _indexes_created
    
    if _indexes_created:
        return True
        
    try:
        # TTL index for automatic cleanup
        await messages_collection.create_index(
            "timestamp",
            expireAfterSeconds=TTL_SECONDS,
            background=True,
            name="ttl_index"
        )
        
        # Compound index for session queries (most common)
        await messages_collection.create_index(
            [("session_id", 1), ("timestamp", 1)],
            background=True,
            name="session_timestamp_index"
        )
        
        # Text search index for content search
        await messages_collection.create_index(
            [("content", "text")],
            background=True,
            name="content_text_index"
        )
        
        # Session + role index for filtering
        await messages_collection.create_index(
            [("session_id", 1), ("role", 1), ("timestamp", 1)],
            background=True,
            name="session_role_timestamp_index"
        )
        
        _indexes_created = True
        logger.info("✅ Optimized indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating optimized indexes: {e}")
        return False

async def test_connection():
    """Test MongoDB connection health"""
    global _connection_tested
    
    if _connection_tested:
        return True
        
    try:
        await asyncio.wait_for(db.admin.command('ping'), timeout=5.0)
        _connection_tested = True
        logger.info("✅ MongoDB connection verified")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection test failed: {e}")
        return False

# -----------------------------
# Safe Operation Wrapper
# -----------------------------
async def safe_db_operation(operation_func, *args, timeout: float = DEFAULT_TIMEOUT, **kwargs):
    """
    Safely execute database operations with timeout and retry logic
    """
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
                logger.error(f"❌ Database operation timed out after {max_retries} retries")
                return None
            await asyncio.sleep(base_delay * (2 ** attempt))  # Exponential backoff
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"❌ Database operation failed after {max_retries} retries: {e}")
                return None
            await asyncio.sleep(base_delay * (2 ** attempt))
    
    return None

# -----------------------------
# Optimized Save Message
# -----------------------------
async def save_message(session_id: str, role: str, content: str, max_retries: int = 2):
    """
    Save a message with duplicate detection and optimized performance
    """
    try:
        # Ensure connection and indexes
        if not await test_connection():
            logger.warning("⚠️ Database connection not available")
            return
            
        if not await ensure_indexes():
            logger.warning("⚠️ Could not ensure indexes")
        
        # Check for duplicates with optimized query
        existing = await safe_db_operation(
            messages_collection.find_one,
            {
                "session_id": session_id,
                "role": role,
                "content": content
            },
            timeout=5.0
        )

        if existing:
            logger.info(f"⚠️ Duplicate message ignored for session {session_id}")
            return

        message_doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "indexed": True  # Mark for efficient queries
        }
        
        # Insert with timeout protection
        result = await safe_db_operation(
            messages_collection.insert_one,
            message_doc,
            timeout=6.0
        )
        
        if result:
            logger.info(f"💾 Saved {role} message for session {session_id}")
        else:
            logger.error(f"❌ Failed to save message for session {session_id}")
            
    except Exception as e:
        logger.error(f"❌ Error in save_message: {e}")

# -----------------------------
# Optimized Conversation History
# -----------------------------
async def get_conversation_history(session_id: str, limit: Optional[int] = None) -> List[Dict]:
    """
    Retrieve conversation history with optimized query and caching
    """
    try:
        if not await test_connection():
            logger.warning("⚠️ Database not available for history retrieval")
            return []
            
        message_limit = limit or MEMORY_LIMIT
        
        # Use optimized query with projection for better performance
        cursor = messages_collection.find(
            {"session_id": session_id},
            {
                "session_id": 1,
                "role": 1,
                "content": 1,
                "timestamp": 1,
                "_id": 0  # Exclude _id for better performance
            }
        ).sort("timestamp", 1).limit(message_limit)
        
        # Execute with timeout
        history = await safe_db_operation(
            cursor.to_list,
            length=None,
            timeout=12.0
        )
        
        if history is None:
            logger.warning(f"⚠️ History query timed out for session {session_id}")
            return []
        
        # Optimize timestamp conversion
        for msg in history:
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()

        logger.info(f"📖 Retrieved {len(history)} messages for session {session_id}")
        return history
        
    except Exception as e:
        logger.error(f"❌ Error retrieving conversation history: {e}")
        return []

# -----------------------------
# Optimized Context Building
# -----------------------------
async def get_conversation_context_for_ai(session_id: str, max_chars: int = 8000) -> str:
    """
    Get formatted conversation context with size optimization
    """
    try:
        # Get recent history with smaller limit first
        history = await get_conversation_history(session_id, MEMORY_LIMIT)
        
        if not history:
            return "No previous conversation context."
        
        context_parts = ["=== CONVERSATION HISTORY ==="]
        total_chars = len(context_parts[0])
        
        # Build context with size limit to prevent token overflow
        for msg in reversed(history):  # Start from recent messages
            role = msg["role"].capitalize()
            content = msg["content"]
            
            # Use string timestamp if already converted
            if isinstance(msg.get("timestamp"), str):
                timestamp = msg["timestamp"][:19]  # Truncate microseconds
            else:
                timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                
            message_line = f"[{timestamp}] {role}: {content}"
            
            # Check size limit
            if total_chars + len(message_line) > max_chars:
                break
                
            context_parts.insert(1, message_line)  # Insert at beginning (reverse order)
            total_chars += len(message_line)
        
        context_parts.append("=== END CONVERSATION HISTORY ===")
        
        full_context = "\n".join(context_parts)
        logger.info(f"📋 Built optimized conversation context ({len(full_context)} chars) for AI")
        return full_context
        
    except Exception as e:
        logger.error(f"❌ Error building conversation context: {e}")
        return "Error retrieving conversation context."

# -----------------------------
# Optimized Search
# -----------------------------
async def search_conversation_memory(session_id: str, search_query: str, limit: int = 20) -> List[Dict]:
    """
    Search messages using optimized text index
    """
    try:
        if not await test_connection():
            return []
            
        # Use optimized text search with session filter
        cursor = messages_collection.find(
            {
                "session_id": session_id,
                "$text": {"$search": search_query}
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
        
        results = await safe_db_operation(
            cursor.to_list,
            length=None,
            timeout=10.0
        )
        
        if results is None:
            logger.warning(f"⚠️ Search query timed out for session {session_id}")
            return []
        
        # Convert timestamps
        for msg in results:
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        
        logger.info(f"🔍 Found {len(results)} messages matching '{search_query}' in session {session_id}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error searching messages: {e}")
        return []

# -----------------------------
# Batch Operations
# -----------------------------
async def save_messages_batch(messages: List[Dict], session_id: str):
    """
    Save multiple messages in a single batch operation for better performance
    """
    try:
        if not messages:
            return 0
            
        if not await test_connection():
            return 0
            
        # Prepare documents with timestamps
        documents = []
        for msg in messages:
            doc = {
                "session_id": session_id,
                "role": msg.get("role", "unknown"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", datetime.utcnow()),
                "indexed": True
            }
            documents.append(doc)
        
        # Batch insert with timeout
        result = await safe_db_operation(
            messages_collection.insert_many,
            documents,
            timeout=15.0
        )
        
        if result:
            inserted_count = len(result.inserted_ids) if hasattr(result, 'inserted_ids') else 0
            logger.info(f"💾 Batch saved {inserted_count} messages for session {session_id}")
            return inserted_count
        else:
            logger.error(f"❌ Batch insert failed for session {session_id}")
            return 0
            
    except Exception as e:
        logger.error(f"❌ Error in batch save: {e}")
        return 0

# -----------------------------
# Enhanced Session Management
# -----------------------------
async def clear_session_messages(session_id: str):
    """
    Delete all messages for a session with optimized query
    """
    try:
        if not await test_connection():
            return 0
            
        result = await safe_db_operation(
            messages_collection.delete_many,
            {"session_id": session_id},
            timeout=10.0
        )
        
        deleted_count = result.deleted_count if result else 0
        logger.info(f"🗑️ Cleared {deleted_count} messages for session {session_id}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Error clearing messages: {e}")
        return 0

async def get_session_stats(session_id: str) -> Dict[str, Any]:
    """
    Get optimized statistics about conversation memory
    """
    try:
        if not await test_connection():
            return {"error": "Database not available"}
            
        # Use aggregation pipeline for better performance
        pipeline = [
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": "$session_id",
                    "total_messages": {"$sum": 1},
                    "user_messages": {
                        "$sum": {"$cond": [{"$eq": ["$role", "user"]}, 1, 0]}
                    },
                    "assistant_messages": {
                        "$sum": {"$cond": [{"$eq": ["$role", "assistant"]}, 1, 0]}
                    },
                    "first_message_time": {"$min": "$timestamp"},
                    "last_message_time": {"$max": "$timestamp"}
                }
            }
        ]
        
        result = await safe_db_operation(
            messages_collection.aggregate(pipeline).to_list,
            length=None,
            timeout=8.0
        )
        
        if not result:
            return {
                "session_id": session_id,
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "first_message_time": None,
                "last_message_time": None
            }
        
        stats = result[0]
        stats["session_id"] = session_id
        
        # Convert timestamps
        if stats.get("first_message_time"):
            stats["first_message_time"] = stats["first_message_time"].isoformat()
        if stats.get("last_message_time"):
            stats["last_message_time"] = stats["last_message_time"].isoformat()
        
        logger.info(f"📊 Memory stats for session {session_id}: {stats['total_messages']} total messages")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting memory stats: {e}")
        return {"error": str(e)}

# -----------------------------
# Connection Health Monitoring
# -----------------------------
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for the message memory system
    """
    try:
        health_info = {
            "status": "unknown",
            "connection": "unknown",
            "indexes": "unknown",
            "performance": {},
            "configuration": {
                "memory_limit": MEMORY_LIMIT,
                "ttl_seconds": TTL_SECONDS,
                "max_timeout": MAX_TIMEOUT,
                "pool_size": client.options.max_pool_size
            }
        }
        
        # Test connection
        connection_start = asyncio.get_event_loop().time()
        connection_ok = await test_connection()
        connection_time = asyncio.get_event_loop().time() - connection_start
        
        health_info["connection"] = "connected" if connection_ok else "failed"
        health_info["performance"]["connection_time_ms"] = round(connection_time * 1000, 2)
        
        if connection_ok:
            # Test indexes
            indexes_ok = await ensure_indexes()
            health_info["indexes"] = "ready" if indexes_ok else "missing"
            
            # Test query performance
            query_start = asyncio.get_event_loop().time()
            test_count = await safe_db_operation(
                messages_collection.count_documents,
                {},
                timeout=5.0
            )
            query_time = asyncio.get_event_loop().time() - query_start
            
            health_info["performance"]["query_time_ms"] = round(query_time * 1000, 2)
            health_info["performance"]["total_messages"] = test_count or 0
            
            health_info["status"] = "healthy" if indexes_ok else "degraded"
        else:
            health_info["status"] = "unhealthy"
        
        return health_info
        
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "connection": "failed"
        }

# -----------------------------
# Cleanup and Maintenance
# -----------------------------
async def cleanup_old_sessions(days_old: int = 7):
    """
    Clean up old sessions beyond TTL for maintenance
    """
    try:
        if not await test_connection():
            return 0
            
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await safe_db_operation(
            messages_collection.delete_many,
            {"timestamp": {"$lt": cutoff_date}},
            timeout=30.0
        )
        
        deleted_count = result.deleted_count if result else 0
        logger.info(f"🧹 Cleaned up {deleted_count} old messages (>{days_old} days)")
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        return 0

# Export optimized functions
__all__ = [
    'save_message',
    'get_conversation_history', 
    'get_conversation_context_for_ai',
    'search_conversation_memory',
    'clear_session_messages',
    'get_session_stats',
    'save_messages_batch',
    'ensure_indexes',
    'health_check',
    'cleanup_old_sessions'
]