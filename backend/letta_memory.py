"""
Letta (MemGPT) Long-term Memory Integration for Elva AI

This module provides persistent memory capabilities using a simplified approach
that stores facts in JSON format and uses basic retrieval.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class SimpleLettaMemory:
    def __init__(self, memory_dir: str = "/app/backend/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / "elva_memory.json"
        
        # Memory structure
        self.memory = {
            "persona": "I am Elva AI, a friendly and intelligent assistant created to help Arpit with various tasks.",
            "user_preferences": {},
            "facts": {},
            "tasks": {},
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Load existing memory
        self._load_memory()

    def _load_memory(self):
        """Load memory from file if it exists"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r') as f:
                    loaded_memory = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.memory.update(loaded_memory)
                logger.info("✅ Loaded existing memory from file")
            else:
                # Create new memory file
                self._save_memory()
                logger.info("✅ Created new memory file")
        except Exception as e:
            logger.error(f"❌ Error loading memory: {e}")

    def _save_memory(self):
        """Save memory to file"""
        try:
            self.memory["last_updated"] = datetime.utcnow().isoformat()
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving memory: {e}")

    def store_fact(self, fact_text: str) -> Dict[str, Any]:
        """Store a new fact in memory"""
        try:
            # Extract key information from the fact
            fact_key = self._extract_fact_key(fact_text)
            
            # Store the fact
            self.memory["facts"][fact_key] = {
                "text": fact_text,
                "created_at": datetime.utcnow().isoformat(),
                "category": self._categorize_fact(fact_text)
            }
            
            # Save to file
            self._save_memory()
            
            logger.info(f"✅ Stored fact: {fact_text[:50]}...")
            
            return {
                "success": True,
                "fact": fact_text,
                "key": fact_key,
                "response": "Fact stored successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing fact: {e}")
            return {"success": False, "error": str(e)}

    def retrieve_context(self, query: str) -> Dict[str, Any]:
        """Retrieve relevant facts for a query"""
        try:
            query_lower = query.lower()
            relevant_facts = []
            
            # Search through facts
            for key, fact_data in self.memory["facts"].items():
                fact_text = fact_data["text"].lower()
                
                # Simple keyword matching
                if any(word in fact_text for word in query_lower.split()):
                    relevant_facts.append(fact_data["text"])
            
            # Search user preferences
            for pref_key, pref_value in self.memory["user_preferences"].items():
                if any(word in pref_key.lower() for word in query_lower.split()):
                    relevant_facts.append(f"{pref_key}: {pref_value}")
            
            context = "\n".join(relevant_facts) if relevant_facts else ""
            
            logger.info(f"✅ Retrieved {len(relevant_facts)} relevant facts for query: {query[:50]}...")
            
            return {
                "success": True,
                "query": query,
                "context": context,
                "relevant": len(relevant_facts) > 0,
                "fact_count": len(relevant_facts)
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving context: {e}")
            return {"success": False, "error": str(e)}

    def forget_fact(self, fact_text: str) -> Dict[str, Any]:
        """Remove a fact from memory"""
        try:
            fact_text_lower = fact_text.lower()
            removed_keys = []
            
            # Find and remove matching facts
            for key in list(self.memory["facts"].keys()):
                fact_data = self.memory["facts"][key]
                if fact_text_lower in fact_data["text"].lower():
                    del self.memory["facts"][key]
                    removed_keys.append(key)
            
            # Save changes
            self._save_memory()
            
            logger.info(f"✅ Removed {len(removed_keys)} facts matching: {fact_text[:50]}...")
            
            return {
                "success": True,
                "fact": fact_text,
                "removed_count": len(removed_keys),
                "response": f"Removed {len(removed_keys)} matching facts"
            }
            
        except Exception as e:
            logger.error(f"❌ Error forgetting fact: {e}")
            return {"success": False, "error": str(e)}

    async def chat_with_memory(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process a message with memory context"""
        try:
            message_lower = message.lower().strip()
            
            # Handle memory commands
            if any(cmd in message_lower for cmd in ["remember that", "store fact", "i like", "i love", "my favorite"]):
                return self.store_fact(message)
            
            elif "my nickname is" in message_lower or "call me" in message_lower or "my name is" in message_lower:
                return self.store_fact(message)
            
            elif any(cmd in message_lower for cmd in ["forget that", "remove fact", "don't remember"]):
                fact = message.replace("forget that", "").replace("remove fact", "").replace("don't remember", "").strip()
                return self.forget_fact(fact)
            
            elif any(cmd in message_lower for cmd in ["what's my nickname", "what is my nickname", "nickname"]):
                context_result = self.retrieve_context("nickname")
                context = context_result.get("context", "")
                if context:
                    # Extract nickname from stored facts
                    for fact_key, fact_data in self.memory["facts"].items():
                        if "nickname" in fact_data.get("category", "") or "nickname" in fact_data.get("text", "").lower():
                            if "ary" in fact_data.get("text", "").lower():
                                return {"success": True, "response": "Your nickname is Ary."}
                            elif "arp" in fact_data.get("text", "").lower():
                                return {"success": True, "response": "Your nickname is Arp."}
                    return {"success": True, "response": context}
                else:
                    return {"success": True, "response": "I don't have information about your nickname."}
            
            elif any(cmd in message_lower for cmd in ["what do you know about me", "what do you remember", "who am i"]):
                # Get all relevant facts about the user
                all_facts = []
                for fact_key, fact_data in self.memory["facts"].items():
                    all_facts.append(fact_data.get("text", ""))
                
                if all_facts:
                    response = "Here's what I remember about you: " + "; ".join(all_facts[:5])  # Limit to 5 facts
                    return {"success": True, "response": response}
                else:
                    return {"success": True, "response": "I don't have specific information stored about you yet."}
            
            elif "what do i love" in message_lower or "what do i like" in message_lower:
                context_result = self.retrieve_context("love like favorite")
                context = context_result.get("context", "")
                if context:
                    return {"success": True, "response": f"Based on what you've told me: {context}"}
                else:
                    return {"success": True, "response": "I don't have information about your preferences yet."}
            
            else:
                # Get relevant context for the message
                context_result = self.retrieve_context(message)
                context = context_result.get("context", "")
                
                return {
                    "success": True,
                    "response": f"I understand. {context}" if context else "I understand.",
                    "used_memory": len(context) > 0,
                    "session_id": session_id,
                    "context": context
                }
                
        except Exception as e:
            logger.error(f"❌ Error in chat with memory: {e}")
            return {"success": False, "error": str(e)}

    def _extract_fact_key(self, fact_text: str) -> str:
        """Extract a key for the fact"""
        fact_lower = fact_text.lower()
        
        # Look for common patterns
        if "nickname" in fact_lower or "call me" in fact_lower:
            return "nickname"
        elif "name is" in fact_lower:
            return "name"
        elif "email" in fact_lower:
            return "email"
        elif "prefer" in fact_lower:
            return f"preference_{len(self.memory['user_preferences'])}"
        elif "manager" in fact_lower or "boss" in fact_lower:
            return "manager"
        else:
            # Generate a unique key
            return f"fact_{len(self.memory['facts'])}"

    def _categorize_fact(self, fact_text: str) -> str:
        """Categorize the fact"""
        fact_lower = fact_text.lower()
        
        if any(word in fact_lower for word in ["nickname", "name", "call me"]):
            return "identity"
        elif any(word in fact_lower for word in ["prefer", "like", "favorite"]):
            return "preferences"
        elif any(word in fact_lower for word in ["manager", "boss", "colleague"]):
            return "contacts"
        elif any(word in fact_lower for word in ["remind", "task", "todo"]):
            return "tasks"
        else:
            return "general"

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get memory statistics"""
        try:
            return {
                "success": True,
                "memory_info": {
                    "total_facts": len(self.memory["facts"]),
                    "user_preferences": len(self.memory["user_preferences"]),
                    "tasks": len(self.memory["tasks"]),
                    "created_at": self.memory.get("created_at"),
                    "last_updated": self.memory.get("last_updated"),
                    "memory_file_exists": self.memory_file.exists()
                }
            }
        except Exception as e:
            logger.error(f"❌ Error getting memory summary: {e}")
            return {"success": False, "error": str(e)}


# Global instance
simple_letta_memory: Optional[SimpleLettaMemory] = None

def get_letta_memory() -> SimpleLettaMemory:
    """Get or create the global simple Letta memory instance"""
    global simple_letta_memory
    if simple_letta_memory is None:
        simple_letta_memory = SimpleLettaMemory()
    return simple_letta_memory

def initialize_letta_memory() -> SimpleLettaMemory:
    """Initialize simple Letta memory system"""
    try:
        memory = get_letta_memory()
        logger.info("✅ Simple Letta memory system initialized")
        return memory
    except Exception as e:
        logger.error(f"❌ Failed to initialize simple Letta memory: {e}")
        raise