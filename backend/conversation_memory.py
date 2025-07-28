"""
Enhanced Conversation Memory System for Elva AI
Implements Langchain memory modules with Redis caching for better conversation context and continuity
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory
from langchain.memory.chat_message_histories import MongoDBChatMessageHistory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.chat import LlmChat, UserMessage
import aioredis
import pickle

logger = logging.getLogger(__name__)

class ElvaConversationMemory:
    """
    Enhanced conversation memory system that combines Langchain's memory modules
    with Elva AI's hybrid architecture for optimal context retention and retrieval.
    """
    
    def __init__(self, db):
        self.db = db
        
        # Initialize Groq LLM for memory summarization
        self.groq_llm = ChatOpenAI(
            temperature=0.1,
            openai_api_key=os.getenv("GROQ_API_KEY"),
            model="llama3-8b-8192",
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Claude API key for enhanced memory processing
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        
        # Memory configurations
        self.buffer_memory_sessions: Dict[str, ConversationBufferMemory] = {}
        self.summary_memory_sessions: Dict[str, ConversationSummaryBufferMemory] = {}
        
        # Memory settings
        self.max_token_limit = 1000  # For summary buffer memory
        self.buffer_window_size = 10  # Number of recent messages to keep in buffer
        self.memory_cleanup_interval = timedelta(hours=24)  # Clean old memories
        
        logger.info("🧠 Enhanced Conversation Memory System initialized")

    async def get_buffer_memory(self, session_id: str) -> ConversationBufferMemory:
        """
        Get or create buffer memory for a session.
        Keeps recent conversation turns in memory for immediate context.
        """
        if session_id not in self.buffer_memory_sessions:
            # Create MongoDB chat message history for this session
            message_history = await self._get_mongodb_history(session_id)
            
            # Initialize buffer memory with chat history
            memory = ConversationBufferMemory(
                chat_memory=message_history,
                return_messages=True,
                memory_key="chat_history",
                input_key="input",
                output_key="output"
            )
            
            self.buffer_memory_sessions[session_id] = memory
            logger.info(f"🆕 Created buffer memory for session: {session_id}")
            
        return self.buffer_memory_sessions[session_id]

    async def get_summary_memory(self, session_id: str) -> ConversationSummaryBufferMemory:
        """
        Get or create summary buffer memory for a session.
        Maintains conversation summary when buffer gets too long.
        """
        if session_id not in self.summary_memory_sessions:
            # Create MongoDB chat message history for this session  
            message_history = await self._get_mongodb_history(session_id)
            
            # Initialize summary buffer memory
            memory = ConversationSummaryBufferMemory(
                llm=self.groq_llm,
                chat_memory=message_history,
                max_token_limit=self.max_token_limit,
                return_messages=True,
                memory_key="chat_history",
                input_key="input", 
                output_key="output"
            )
            
            self.summary_memory_sessions[session_id] = memory
            logger.info(f"🧠 Created summary memory for session: {session_id}")
            
        return self.summary_memory_sessions[session_id]

    async def _get_mongodb_history(self, session_id: str):
        """
        Create a MongoDB chat message history adapter for Langchain.
        This bridges our existing MongoDB storage with Langchain memory.
        """
        try:
            # Retrieve existing messages from our MongoDB collection
            messages = await self.db.chat_messages.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).to_list(1000)
            
            # Convert our message format to Langchain format
            langchain_messages = []
            for msg in messages:
                # Add human message
                langchain_messages.append(HumanMessage(content=msg.get("message", "")))
                
                # Add AI response
                if msg.get("response"):
                    langchain_messages.append(AIMessage(content=msg.get("response", "")))
            
            return SimpleChatMessageHistory(messages=langchain_messages)
            
        except Exception as e:
            logger.error(f"Error creating MongoDB history for session {session_id}: {e}")
            return SimpleChatMessageHistory(messages=[])

    async def add_message_to_memory(self, session_id: str, user_message: str, ai_response: str, intent_data: dict = None):
        """
        Add a conversation turn to both buffer and summary memory.
        """
        try:
            # Get both memory types
            buffer_memory = await self.get_buffer_memory(session_id)
            summary_memory = await self.get_summary_memory(session_id)
            
            # Add to buffer memory
            buffer_memory.chat_memory.add_user_message(user_message)
            buffer_memory.chat_memory.add_ai_message(ai_response)
            
            # Add to summary memory
            summary_memory.chat_memory.add_user_message(user_message)
            summary_memory.chat_memory.add_ai_message(ai_response)
            
            # Store enhanced context if intent data available
            if intent_data:
                await self._store_intent_context(session_id, intent_data)
                
            logger.info(f"💾 Added message to memory for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error adding message to memory: {e}")

    async def get_conversation_context(self, session_id: str, use_summary: bool = False) -> str:
        """
        Retrieve conversation context for the session.
        
        Args:
            session_id: Session identifier
            use_summary: If True, uses summary memory; if False, uses buffer memory
            
        Returns:
            Formatted conversation context as string
        """
        try:
            if use_summary:
                memory = await self.get_summary_memory(session_id)
            else:
                memory = await self.get_buffer_memory(session_id)
                
            # Get memory variables
            memory_vars = memory.load_memory_variables({})
            chat_history = memory_vars.get("chat_history", [])
            
            # Format conversation context
            context_parts = []
            for message in chat_history[-self.buffer_window_size:]:  # Last N messages
                if isinstance(message, HumanMessage):
                    context_parts.append(f"Human: {message.content}")
                elif isinstance(message, AIMessage):
                    context_parts.append(f"Assistant: {message.content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""

    async def get_relevant_context(self, session_id: str, query: str) -> str:
        """
        Get contextually relevant conversation history based on current query.
        Uses Claude for intelligent context selection.
        """
        try:
            # Get full conversation context
            full_context = await self.get_conversation_context(session_id, use_summary=True)
            
            if not full_context:
                return ""
                
            # Use Claude to extract relevant context
            if self.claude_api_key:
                claude_chat = LlmChat(
                    api_key=self.claude_api_key,
                    session_id=f"context_{session_id}",
                    system_message="""You are a context analyzer. Given a conversation history and a new query, 
                    extract the most relevant parts of the conversation that would help provide a better response.
                    
                    Return only the relevant conversation excerpts, maintaining the Human/Assistant format.
                    If no relevant context exists, return 'No relevant context found.'"""
                ).with_model("anthropic", "claude-3-5-sonnet-20241022").with_max_tokens(2048)
                
                context_query = f"Conversation History:\n{full_context}\n\nNew Query: {query}\n\nRelevant Context:"
                relevant_context = await claude_chat.send_message(UserMessage(text=context_query))
                
                return relevant_context if relevant_context != "No relevant context found." else ""
            else:
                # Fallback to recent context if Claude unavailable
                return await self.get_conversation_context(session_id, use_summary=False)
                
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return await self.get_conversation_context(session_id, use_summary=False)

    async def _store_intent_context(self, session_id: str, intent_data: dict):
        """
        Store additional intent context for better memory retrieval.
        """
        try:
            context_doc = {
                "session_id": session_id,
                "intent": intent_data.get("intent"),
                "context_data": intent_data,
                "timestamp": datetime.utcnow(),
                "type": "intent_context"
            }
            
            await self.db.conversation_context.insert_one(context_doc)
            
        except Exception as e:
            logger.error(f"Error storing intent context: {e}")

    async def get_session_summary(self, session_id: str) -> str:
        """
        Get an AI-generated summary of the entire conversation session.
        """
        try:
            summary_memory = await self.get_summary_memory(session_id)
            
            # Get the summary from Langchain's summary memory
            if hasattr(summary_memory, 'buffer'):
                return summary_memory.buffer
            else:
                # Generate summary using Claude
                full_context = await self.get_conversation_context(session_id, use_summary=False)
                
                if not full_context or not self.claude_api_key:
                    return "No conversation summary available."
                    
                claude_chat = LlmChat(
                    api_key=self.claude_api_key,
                    session_id=f"summary_{session_id}",
                    system_message="""You are a conversation summarizer. Create a concise, helpful summary 
                    of the conversation that captures key topics, user preferences, and important context.
                    
                    Focus on information that would be useful for future interactions."""
                ).with_model("anthropic", "claude-3-5-sonnet-20241022").with_max_tokens(1024)
                
                summary = await claude_chat.send_message(UserMessage(text=f"Summarize this conversation:\n\n{full_context}"))
                return summary
                
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return "Unable to generate conversation summary."

    async def clear_session_memory(self, session_id: str):
        """
        Clear memory for a specific session.
        """
        try:
            # Remove from active memory sessions
            if session_id in self.buffer_memory_sessions:
                del self.buffer_memory_sessions[session_id]
                
            if session_id in self.summary_memory_sessions:
                del self.summary_memory_sessions[session_id]
                
            # Clear context data from database
            await self.db.conversation_context.delete_many({"session_id": session_id})
            
            logger.info(f"🧹 Cleared memory for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing session memory: {e}")

    async def cleanup_old_memories(self):
        """
        Cleanup old memory sessions to prevent memory leaks.
        """
        try:
            cutoff_time = datetime.utcnow() - self.memory_cleanup_interval
            
            # Remove old context data
            result = await self.db.conversation_context.delete_many({
                "timestamp": {"$lt": cutoff_time}
            })
            
            logger.info(f"🧹 Cleaned up {result.deleted_count} old memory records")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")

    def get_memory_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a session.
        """
        stats = {
            "session_id": session_id,
            "has_buffer_memory": session_id in self.buffer_memory_sessions,
            "has_summary_memory": session_id in self.summary_memory_sessions,
            "memory_cleanup_interval": str(self.memory_cleanup_interval),
            "max_token_limit": self.max_token_limit,
            "buffer_window_size": self.buffer_window_size,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return stats


class SimpleChatMessageHistory:
    """
    Simple chat message history adapter for Langchain compatibility.
    """
    
    def __init__(self, messages: List[BaseMessage] = None):
        self.messages: List[BaseMessage] = messages or []
        
    def add_user_message(self, message: str):
        """Add a user message to the history."""
        self.messages.append(HumanMessage(content=message))
        
    def add_ai_message(self, message: str):
        """Add an AI message to the history."""
        self.messages.append(AIMessage(content=message))
        
    def clear(self):
        """Clear the message history."""
        self.messages = []


# Global instance to be used across the application
conversation_memory: Optional[ElvaConversationMemory] = None

def initialize_conversation_memory(db):
    """Initialize the global conversation memory instance."""
    global conversation_memory
    conversation_memory = ElvaConversationMemory(db)
    return conversation_memory

def get_conversation_memory() -> ElvaConversationMemory:
    """Get the global conversation memory instance."""
    if conversation_memory is None:
        raise RuntimeError("Conversation memory not initialized. Call initialize_conversation_memory first.")
    return conversation_memory