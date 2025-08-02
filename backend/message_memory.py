# message_memory.py
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Initialize MongoDB client
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]
messages_collection = db["messages"]

async def save_message(session_id: str, role: str, content: str):
    """
    Save a user or assistant message into MongoDB.
    Args:
        session_id: Session identifier
        role: 'user' or 'assistant' 
        content: Message content
    """
    try:
        message_doc = {
            "session_id": session_id,
            "role": role,  # 'user' or 'assistant'
            "content": content,
            "timestamp": datetime.utcnow()
        }
        await messages_collection.insert_one(message_doc)
        logger.info(f"💾 Saved {role} message for session {session_id}")
    except Exception as e:
        logger.error(f"❌ Error saving message: {e}")

async def get_conversation_history(session_id: str, limit: Optional[int] = None) -> List[Dict]:
    """
    Retrieve ALL messages for a session in chronological order.
    Args:
        session_id: Session identifier
        limit: Optional limit (None means get ALL messages)
    Returns:
        List of message dictionaries ordered by timestamp
    """
    try:
        query = {"session_id": session_id}
        cursor = messages_collection.find(query).sort("timestamp", 1)
        
        if limit:
            cursor = cursor.limit(limit)
            
        history = await cursor.to_list(length=None)
        logger.info(f"📖 Retrieved {len(history)} messages for session {session_id}")
        return history
    except Exception as e:
        logger.error(f"❌ Error retrieving conversation history: {e}")
        return []

async def build_llm_prompt(session_id: str, current_message: str, limit: Optional[int] = None) -> str:
    """
    Build the full conversation prompt for the LLM
    by combining ALL previous messages + current user message.
    Args:
        session_id: Session identifier
        current_message: Current user message
        limit: Optional limit (None means use ALL messages)
    Returns:
        Complete conversation context for LLM
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

async def get_conversation_context_for_ai(session_id: str) -> str:
    """
    Get formatted conversation context specifically for AI responses.
    This includes ALL previous messages to maintain full context.
    """
    try:
        history = await get_conversation_history(session_id)
        
        if not history:
            return "No previous conversation context."
        
        context_parts = ["=== FULL CONVERSATION HISTORY ==="]
        
        for msg in history:
            role = msg["role"].capitalize()
            content = msg["content"]
            timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            context_parts.append(f"[{timestamp}] {role}: {content}")
        
        context_parts.append("=== END CONVERSATION HISTORY ===")
        
        full_context = "\n".join(context_parts)
        logger.info(f"📋 Built full conversation context with {len(history)} messages for AI")
        return full_context
        
    except Exception as e:
        logger.error(f"❌ Error building conversation context: {e}")
        return "Error retrieving conversation context."

async def search_conversation_memory(session_id: str, search_query: str) -> List[Dict]:
    """
    Search through conversation history for specific content.
    Useful for finding mentions of names, topics, etc.
    """
    try:
        history = await get_conversation_history(session_id)
        matching_messages = []
        
        search_lower = search_query.lower()
        
        for msg in history:
            if search_lower in msg["content"].lower():
                matching_messages.append(msg)
        
        logger.info(f"🔍 Found {len(matching_messages)} messages matching '{search_query}' in session {session_id}")
        return matching_messages
        
    except Exception as e:
        logger.error(f"❌ Error searching conversation memory: {e}")
        return []

async def clear_session_messages(session_id: str):
    """
    Delete all messages for a session (if needed).
    """
    try:
        result = await messages_collection.delete_many({"session_id": session_id})
        logger.info(f"🗑️ Cleared {result.deleted_count} messages for session {session_id}")
        return result.deleted_count
    except Exception as e:
        logger.error(f"❌ Error clearing session messages: {e}")
        return 0

async def get_memory_stats(session_id: str) -> Dict[str, Any]:
    """
    Get statistics about conversation memory for a session.
    """
    try:
        total_messages = await messages_collection.count_documents({"session_id": session_id})
        user_messages = await messages_collection.count_documents({"session_id": session_id, "role": "user"})
        assistant_messages = await messages_collection.count_documents({"session_id": session_id, "role": "assistant"})
        
        # Get first and last message timestamps
        first_message = await messages_collection.find_one({"session_id": session_id}, sort=[("timestamp", 1)])
        last_message = await messages_collection.find_one({"session_id": session_id}, sort=[("timestamp", -1)])
        
        stats = {
            "session_id": session_id,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "first_message_time": first_message["timestamp"] if first_message else None,
            "last_message_time": last_message["timestamp"] if last_message else None
        }
        
        logger.info(f"📊 Memory stats for session {session_id}: {total_messages} total messages")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting memory stats: {e}")
        return {"error": str(e)}