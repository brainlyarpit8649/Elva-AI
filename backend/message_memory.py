from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Initialize MongoDB client
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]
messages_collection = db["messages"]

MEMORY_LIMIT = int(os.environ.get("MEMORY_MESSAGE_LIMIT", 45))  # Default: last 45 messages
TTL_SECONDS = int(os.environ.get("MEMORY_TTL_SECONDS", 172800))  # 2 days

# -----------------------------
# Index Setup (TTL + Text Search)
# -----------------------------
async def ensure_indexes():
    try:
        # TTL index to auto-delete messages older than TTL_SECONDS
        await messages_collection.create_index(
            "timestamp",
            expireAfterSeconds=TTL_SECONDS
        )
        # Text index for faster search
        await messages_collection.create_index([("content", "text")])
        logger.info("✅ TTL & text indexes ensured for messages collection")
    except Exception as e:
        logger.error(f"❌ Error ensuring indexes: {e}")


# -----------------------------
# Save Message
# -----------------------------
async def save_message(session_id: str, role: str, content: str):
    """
    Save a message if not already stored (deduplicated).
    """
    try:
        existing = await messages_collection.find_one({
            "session_id": session_id,
            "role": role,
            "content": content
        })

        if existing:
            logger.info(f"⚠️ Duplicate message ignored for session {session_id}")
            return

        message_doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        await messages_collection.insert_one(message_doc)
        logger.info(f"💾 Saved {role} message for session {session_id}")
    except Exception as e:
        logger.error(f"❌ Error saving message: {e}")


# -----------------------------
# Retrieve Conversation History
# -----------------------------
async def get_conversation_history(session_id: str, limit: Optional[int] = None) -> List[Dict]:
    """
    Retrieve last N messages for a session in chronological order.
    """
    try:
        message_limit = limit or MEMORY_LIMIT
        cursor = messages_collection.find({"session_id": session_id}).sort("timestamp", 1).limit(message_limit)
        history = await cursor.to_list(length=None)

        # Convert timestamps for JSON compatibility
        for msg in history:
            if isinstance(msg["timestamp"], datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()

        logger.info(f"📖 Retrieved {len(history)} messages for session {session_id}")
        return history
    except Exception as e:
        logger.error(f"❌ Error retrieving conversation history: {e}")
        return []


# -----------------------------
# Build LLM Prompt
# -----------------------------
async def build_llm_prompt(session_id: str, current_message: str, limit: Optional[int] = None) -> str:
    """
    Build a prompt for LLM with limited history to avoid token overload.
    """
    try:
        history = await get_conversation_history(session_id, limit)
        prompt = "Previous conversation:\n"
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        prompt += f"\nUser: {current_message}\nAssistant:"
        logger.info(f"🔨 Built prompt with {len(history)} previous messages for session {session_id}")
        return prompt
    except Exception as e:
        logger.error(f"❌ Error building LLM prompt: {e}")
        return f"User: {current_message}\nAssistant:"


# -----------------------------
# Get Conversation Context for AI
# -----------------------------
async def get_conversation_context_for_ai(session_id: str) -> str:
    """
    Get formatted conversation context specifically for AI responses.
    This includes limited previous messages to maintain context without token overload.
    """
    try:
        history = await get_conversation_history(session_id, MEMORY_LIMIT)
        
        if not history:
            return "No previous conversation context."
        
        context_parts = ["=== CONVERSATION HISTORY ==="]
        
        for msg in history:
            role = msg["role"].capitalize()
            content = msg["content"]
            # Use string timestamp if already converted
            if isinstance(msg["timestamp"], str):
                timestamp = msg["timestamp"]
            else:
                timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            context_parts.append(f"[{timestamp}] {role}: {content}")
        
        context_parts.append("=== END CONVERSATION HISTORY ===")
        
        full_context = "\n".join(context_parts)
        logger.info(f"📋 Built conversation context with {len(history)} messages for AI")
        return full_context
        
    except Exception as e:
        logger.error(f"❌ Error building conversation context: {e}")
        return "Error retrieving conversation context."


# -----------------------------
# Search Messages
# -----------------------------
async def search_conversation_memory(session_id: str, search_query: str) -> List[Dict]:
    """
    Search messages using MongoDB text index for efficiency.
    """
    try:
        cursor = messages_collection.find({
            "session_id": session_id,
            "$text": {"$search": search_query}
        })
        results = await cursor.to_list(length=None)
        
        # Convert timestamps for JSON compatibility
        for msg in results:
            if isinstance(msg["timestamp"], datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        
        logger.info(f"🔍 Found {len(results)} messages matching '{search_query}' in session {session_id}")
        return results
    except Exception as e:
        logger.error(f"❌ Error searching messages: {e}")
        return []


# -----------------------------
# Clear Session
# -----------------------------
async def clear_session_messages(session_id: str):
    """
    Delete all messages for a session.
    """
    try:
        result = await messages_collection.delete_many({"session_id": session_id})
        logger.info(f"🗑️ Cleared {result.deleted_count} messages for session {session_id}")
        return result.deleted_count
    except Exception as e:
        logger.error(f"❌ Error clearing messages: {e}")
        return 0


# -----------------------------
# Memory Stats
# -----------------------------
async def get_memory_stats(session_id: str) -> Dict[str, Any]:
    """
    Get statistics about conversation memory for a session.
    """
    try:
        total_messages = await messages_collection.count_documents({"session_id": session_id})
        user_messages = await messages_collection.count_documents({"session_id": session_id, "role": "user"})
        assistant_messages = await messages_collection.count_documents({"session_id": session_id, "role": "assistant"})

        first_message = await messages_collection.find_one({"session_id": session_id}, sort=[("timestamp", 1)])
        last_message = await messages_collection.find_one({"session_id": session_id}, sort=[("timestamp", -1)])

        stats = {
            "session_id": session_id,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "first_message_time": first_message["timestamp"].isoformat() if first_message else None,
            "last_message_time": last_message["timestamp"].isoformat() if last_message else None
        }

        logger.info(f"📊 Memory stats for session {session_id}: {total_messages} total messages")
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting memory stats: {e}")
        return {"error": str(e)}