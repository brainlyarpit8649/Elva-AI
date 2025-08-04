"""
Letta (MemGPT) Long-term Memory Integration for Elva AI

This module provides persistent memory capabilities using Letta SDK, allowing Elva AI to:
- Remember facts and instructions across sessions
- Self-edit memory blocks when updated
- Retrieve relevant context for better responses
- Forget facts when requested

Memory Architecture:
- Persona: Friendly assistant for Arpit
- User Preferences: Communication styles, settings
- Facts & Tasks: Important information and reminders
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Letta imports
from letta import create_client, Client
from letta.schemas.agent import CreateAgentRequest
from letta.schemas.memory import Block, CreateBlock
from letta.schemas.user import User
from letta.client.client import LocalClient
from letta.schemas.llm_config import LLMConfig
from letta.schemas.embedding_config import EmbeddingConfig

logger = logging.getLogger(__name__)

class LettaMemory:
    def __init__(self, memory_dir: str = "/app/backend/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / "elva_memory.json"
        
        self.client: Optional[LocalClient] = None
        self.agent_id: Optional[str] = None
        self.agent_state: Dict[str, Any] = {}
        
        # Initialize the Letta client and agent
        self._initialize_client()
        self._load_or_create_agent()

    def _initialize_client(self):
        """Initialize Letta client with appropriate configuration"""
        try:
            # Create a local Letta client (no external server required)
            self.client = create_client()
            
            # Ensure we have a default user
            try:
                users = self.client.list_users()
                if not users:
                    # Create default user
                    user = self.client.create_user()
                    logger.info(f"✅ Created default Letta user: {user.id}")
                else:
                    user = users[0]
                    logger.info(f"✅ Using existing Letta user: {user.id}")
            except Exception as e:
                logger.warning(f"⚠️ User setup warning: {e}")
                
            logger.info("✅ Letta client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Letta client: {e}")
            raise

    def _load_or_create_agent(self):
        """Load existing agent from memory file or create a new one"""
        try:
            if self.memory_file.exists():
                # Load existing agent state
                with open(self.memory_file, 'r') as f:
                    self.agent_state = json.load(f)
                
                agent_id = self.agent_state.get('agent_id')
                if agent_id:
                    # Try to get the existing agent
                    try:
                        agent = self.client.get_agent(agent_id)
                        self.agent_id = agent_id
                        logger.info(f"✅ Loaded existing Letta agent: {agent_id}")
                        return
                    except Exception:
                        logger.warning(f"⚠️ Agent {agent_id} not found, creating new one")
            
            # Create new agent
            self._create_new_agent()
            
        except Exception as e:
            logger.error(f"❌ Error loading/creating agent: {e}")
            # Fallback: create new agent
            self._create_new_agent()

    def _create_new_agent(self):
        """Create a new Letta agent with initial memory blocks"""
        try:
            # Define initial memory blocks for Elva AI
            memory_blocks = [
                {
                    "name": "persona",
                    "value": "I am Elva AI, a friendly and intelligent assistant created to help Arpit with various tasks. I am knowledgeable, professional, and always eager to assist. I maintain a warm but efficient communication style."
                },
                {
                    "name": "user_preferences", 
                    "value": "User (Arpit) preferences: Prefers short, professional responses. Values efficiency and clear communication."
                },
                {
                    "name": "facts_and_tasks",
                    "value": "Important facts and tasks I need to remember about the user and their requests."
                }
            ]
            
            # Create the agent with memory blocks
            agent_request = CreateAgentRequest(
                name="elva_agent",
                description="Elva AI's persistent memory agent for long-term context and facts",
                memory_blocks=memory_blocks,
                system="You are Elva AI's memory system. Store important facts, user preferences, and tasks. Always update memory when new information is provided. Be concise and accurate."
            )
            
            agent = self.client.create_agent(agent_request)
            self.agent_id = agent.id
            
            # Save agent state
            self.agent_state = {
                'agent_id': agent.id,
                'created_at': datetime.utcnow().isoformat(),
                'memory_blocks': memory_blocks
            }
            self._save_memory()
            
            logger.info(f"✅ Created new Letta agent: {agent.id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create new agent: {e}")
            raise

    def _save_memory(self):
        """Save agent state to persistent storage"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.agent_state, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save memory: {e}")

    def store_fact(self, fact_text: str) -> Dict[str, Any]:
        """
        Store a new fact in Letta's memory
        
        Args:
            fact_text: The fact to store
            
        Returns:
            Dictionary with success status and details
        """
        try:
            if not self.client or not self.agent_id:
                return {"success": False, "error": "Agent not initialized"}
            
            # Send message to agent to store the fact
            message = f"STORE_FACT: {fact_text}"
            response = self.client.send_message(
                agent_id=self.agent_id,
                message=message,
                role="user"
            )
            
            # Update our local state tracking
            self.agent_state['last_updated'] = datetime.utcnow().isoformat()
            self._save_memory()
            
            logger.info(f"✅ Stored fact: {fact_text[:50]}...")
            
            return {
                "success": True,
                "fact": fact_text,
                "response": response.messages[-1].text if response.messages else "Fact stored successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing fact: {e}")
            return {"success": False, "error": str(e)}

    def retrieve_context(self, query: str) -> Dict[str, Any]:
        """
        Retrieve relevant facts and context for a given query
        
        Args:
            query: The query to search for relevant context
            
        Returns:
            Dictionary with relevant context information
        """
        try:
            if not self.client or not self.agent_id:
                return {"success": False, "error": "Agent not initialized"}
            
            # Send query to agent to retrieve relevant information
            message = f"RETRIEVE_CONTEXT: {query}"
            response = self.client.send_message(
                agent_id=self.agent_id,
                message=message,
                role="user"
            )
            
            context = response.messages[-1].text if response.messages else ""
            
            logger.info(f"✅ Retrieved context for: {query[:50]}...")
            
            return {
                "success": True,
                "query": query,
                "context": context,
                "relevant": len(context) > 10  # Simple relevance check
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving context: {e}")
            return {"success": False, "error": str(e)}

    def chat_with_memory(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Process a chat message using Letta's memory system
        
        Args:
            message: User's message
            session_id: Current session ID
            
        Returns:
            Dictionary with response and memory information
        """
        try:
            if not self.client or not self.agent_id:
                return {"success": False, "error": "Agent not initialized"}
            
            # Check if this is a memory command
            message_lower = message.lower().strip()
            
            # Handle memory commands
            if any(cmd in message_lower for cmd in ["remember that", "store fact", "teach elva"]):
                fact = message.replace("remember that", "").replace("store fact", "").replace("teach elva", "").strip()
                return self.store_fact(fact)
            
            elif any(cmd in message_lower for cmd in ["forget that", "remove fact", "delete"]):
                fact = message.replace("forget that", "").replace("remove fact", "").replace("delete", "").strip()
                return self.forget_fact(fact)
            
            elif any(cmd in message_lower for cmd in ["what do you know about", "tell me about", "recall"]):
                query = message.replace("what do you know about", "").replace("tell me about", "").replace("recall", "").strip()
                return self.retrieve_context(query)
            
            else:
                # Regular chat with memory context
                response = self.client.send_message(
                    agent_id=self.agent_id,
                    message=message,
                    role="user"
                )
                
                return {
                    "success": True,
                    "response": response.messages[-1].text if response.messages else "I understand.",
                    "used_memory": True,
                    "session_id": session_id
                }
                
        except Exception as e:
            logger.error(f"❌ Error in chat with memory: {e}")
            return {"success": False, "error": str(e)}

    def forget_fact(self, fact_text: str) -> Dict[str, Any]:
        """
        Remove/forget a specific fact from memory
        
        Args:
            fact_text: The fact to forget/remove
            
        Returns:
            Dictionary with success status
        """
        try:
            if not self.client or not self.agent_id:
                return {"success": False, "error": "Agent not initialized"}
            
            # Send message to agent to forget the fact
            message = f"FORGET_FACT: {fact_text}"
            response = self.client.send_message(
                agent_id=self.agent_id,
                message=message,
                role="user"
            )
            
            logger.info(f"✅ Forgot fact: {fact_text[:50]}...")
            
            return {
                "success": True,
                "fact": fact_text,
                "response": response.messages[-1].text if response.messages else "Fact forgotten successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error forgetting fact: {e}")
            return {"success": False, "error": str(e)}

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current memory state
        
        Returns:
            Dictionary with memory statistics and summary
        """
        try:
            if not self.client or not self.agent_id:
                return {"success": False, "error": "Agent not initialized"}
            
            # Get agent memory blocks
            agent = self.client.get_agent(self.agent_id)
            memory_info = {
                "agent_id": self.agent_id,
                "memory_blocks": len(agent.memory.blocks) if hasattr(agent, 'memory') and hasattr(agent.memory, 'blocks') else 0,
                "last_updated": self.agent_state.get('last_updated', 'Unknown'),
                "created_at": self.agent_state.get('created_at', 'Unknown'),
                "memory_file_exists": self.memory_file.exists()
            }
            
            return {
                "success": True,
                "memory_info": memory_info
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting memory summary: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_memory(self):
        """Clean up resources and save final state"""
        try:
            if self.agent_state:
                self.agent_state['last_cleanup'] = datetime.utcnow().isoformat()
                self._save_memory()
            logger.info("✅ Letta memory cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")


# Global instance
letta_memory: Optional[LettaMemory] = None

def get_letta_memory() -> LettaMemory:
    """Get or create the global Letta memory instance"""
    global letta_memory
    if letta_memory is None:
        letta_memory = LettaMemory()
    return letta_memory

def initialize_letta_memory() -> LettaMemory:
    """Initialize Letta memory system"""
    try:
        memory = get_letta_memory()
        logger.info("✅ Letta memory system initialized")
        return memory
    except Exception as e:
        logger.error(f"❌ Failed to initialize Letta memory: {e}")
        raise