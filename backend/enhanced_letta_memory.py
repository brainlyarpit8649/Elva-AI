"""
Enhanced Letta Memory System for Elva AI
Provides advanced long-term memory capabilities with periodic summarization,
natural language power commands, and performance optimizations.
"""

import json
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import re
from collections import defaultdict
import hashlib
import httpx

logger = logging.getLogger(__name__)

class EnhancedLettaMemory:
    def __init__(self, memory_dir: str = "/app/backend/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / "elva_enhanced_memory.json"
        self.conversation_summaries_file = self.memory_dir / "conversation_summaries.json"
        
        # Enhanced memory structure with periodic summarization
        self.memory = {
            "persona": "I am Elva AI, a friendly and intelligent assistant. I learn and remember information about users to provide personalized assistance.",
            "user_facts": {},  # Personal information, preferences, relationships
            "user_preferences": {},  # Settings, likes/dislikes, communication style
            "conversation_summaries": {},  # Periodic summaries of conversations by session
            "daily_summaries": {},  # Daily conversation summaries
            "weekly_summaries": {},  # Weekly conversation patterns
            "tasks_and_reminders": {},  # User tasks, reminders, and scheduling
            "interaction_patterns": {},  # User behavior patterns and preferences
            "learned_contexts": {},  # Context learned from conversations
            "memory_metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "last_summarization": datetime.utcnow().isoformat(),
                "last_daily_summary": datetime.utcnow().isoformat(),
                "total_facts": 0,
                "total_conversations": 0,
                "summarization_interval": 3600,  # 1 hour in seconds
                "conversation_threshold": 10  # Min messages before summarizing
            }
        }
        
        # Performance optimization - memory cache
        self._memory_cache = {}
        self._cache_timestamp = None
        self.CACHE_TTL = 300  # 5 minutes cache TTL
        
        # Summarization settings
        self.SUMMARIZATION_INTERVAL = 3600  # 1 hour
        self.MIN_MESSAGES_FOR_SUMMARY = 10  # Minimum messages before creating summary
        self.MAX_SUMMARY_AGE = 86400  # 24 hours
        
        # Load existing memory
        self._load_memory()

    def _load_memory(self):
        """Load memory from file with caching"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r') as f:
                    loaded_memory = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.memory.update(loaded_memory)
                    
                self._update_cache()
                logger.info("✅ Loaded enhanced memory from file")
            else:
                # Create new memory file
                self._save_memory()
                logger.info("✅ Created new enhanced memory file")
        except Exception as e:
            logger.error(f"❌ Error loading enhanced memory: {e}")

    def _save_memory(self):
        """Save memory to file with metadata updates"""
        try:
            self.memory["memory_metadata"]["last_updated"] = datetime.utcnow().isoformat()
            self.memory["memory_metadata"]["total_facts"] = len(self.memory["user_facts"])
            
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
                
            self._update_cache()
            logger.info("✅ Enhanced memory saved successfully")
        except Exception as e:
            logger.error(f"❌ Error saving enhanced memory: {e}")

    def _update_cache(self):
        """Update memory cache for performance"""
        self._memory_cache = self.memory.copy()
        self._cache_timestamp = datetime.utcnow()

    def _is_cache_valid(self) -> bool:
        """Check if memory cache is still valid"""
        if not self._cache_timestamp:
            return False
        return (datetime.utcnow() - self._cache_timestamp).seconds < self.CACHE_TTL

    def process_natural_language_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process natural language memory commands with enhanced intelligence"""
        try:
            message_lower = message.lower().strip()
            
            # STORE/REMEMBER commands
            if self._is_store_command(message_lower):
                return self._process_store_command(message, session_id)
            
            # FORGET commands
            elif self._is_forget_command(message_lower):
                return self._process_forget_command(message, session_id)
            
            # RECALL/RETRIEVE commands
            elif self._is_recall_command(message_lower):
                return self._process_recall_command(message, session_id)
            
            # MEMORY MANAGEMENT commands
            elif self._is_memory_management_command(message_lower):
                return self._process_memory_management_command(message, session_id)
            
            # PREFERENCE SETTING commands
            elif self._is_preference_command(message_lower):
                return self._process_preference_command(message, session_id)
            
            # TASK/REMINDER commands
            elif self._is_task_command(message_lower):
                return self._process_task_command(message, session_id)
            
            else:
                # Not a memory command, but check if we should enhance response with context
                context = self._get_relevant_context(message, session_id)
                return {
                    "is_memory_command": False,
                    "relevant_context": context,
                    "context_used": len(context) > 0
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing natural language command: {e}")
            return {"success": False, "error": str(e), "is_memory_command": False}

    def _is_store_command(self, message: str) -> bool:
        """Check if message is a store/remember command"""
        store_patterns = [
            "remember that", "remember this", "store fact", "save fact", "teach elva",
            "my name is", "call me", "i am", "my nickname is", "remember:", "note that",
            "keep in mind that", "don't forget that", "make sure you remember"
        ]
        return any(pattern in message for pattern in store_patterns)

    def _is_forget_command(self, message: str) -> bool:
        """Check if message is a forget command"""
        forget_patterns = [
            "forget that", "forget about", "remove fact", "delete fact", "don't remember",
            "stop remembering", "clear fact", "remove from memory", "erase", "delete"
        ]
        return any(pattern in message for pattern in forget_patterns)

    def _is_recall_command(self, message: str) -> bool:
        """Check if message is a recall/retrieve command"""
        recall_patterns = [
            "what do you remember", "what do you know about me", "tell me about",
            "what's my", "who am i", "what are my", "list my", "show my",
            "recall", "remind me", "what did i tell you about"
        ]
        return any(pattern in message for pattern in recall_patterns)

    def _is_memory_management_command(self, message: str) -> bool:
        """Check if message is a memory management command"""
        management_patterns = [
            "summarize memory", "memory summary", "clear all memory", "export memory",
            "memory stats", "what do you remember about", "list all facts"
        ]
        return any(pattern in message for pattern in management_patterns)

    def _is_preference_command(self, message: str) -> bool:
        """Check if message is a preference setting command"""
        preference_patterns = [
            "i prefer", "i like", "i don't like", "my preference is", "set preference",
            "always remember to", "my style is", "communicate with me", "tone should be"
        ]
        return any(pattern in message for pattern in preference_patterns)

    def _is_task_command(self, message: str) -> bool:
        """Check if message is a task/reminder command"""
        task_patterns = [
            "remind me to", "remember to remind me", "set a reminder", "task:",
            "schedule", "don't let me forget", "make sure i", "help me remember"
        ]
        return any(pattern in message for pattern in task_patterns)

    def _process_store_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process store/remember commands with intelligent extraction"""
        try:
            # Extract the fact to store
            fact = self._extract_fact_from_store_command(message)
            category = self._categorize_fact(fact)
            fact_key = self._generate_fact_key(fact, category)
            
            # Store the fact
            fact_data = {
                "text": fact,
                "original_message": message,
                "category": category,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "confidence": self._calculate_fact_confidence(fact)
            }
            
            if category == "preferences":
                self.memory["user_preferences"][fact_key] = fact_data
            else:
                self.memory["user_facts"][fact_key] = fact_data
            
            self._save_memory()
            
            logger.info(f"✅ Stored enhanced fact: {fact[:50]}...")
            
            return {
                "success": True,
                "is_memory_command": True,
                "action": "store_fact",
                "fact": fact,
                "category": category,
                "response": f"✅ I'll remember that: {fact}",
                "intent_data": {"intent": "store_memory", "fact": fact, "category": category}
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing store command: {e}")
            return {
                "success": False,
                "is_memory_command": True,
                "error": str(e),
                "response": "⚠️ I had trouble storing that information."
            }

    def _process_forget_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process forget commands with intelligent matching"""
        try:
            # Extract what to forget
            fact_to_forget = self._extract_fact_from_forget_command(message)
            removed_items = []
            
            # Search and remove from user_facts
            for key in list(self.memory["user_facts"].keys()):
                fact_data = self.memory["user_facts"][key]
                if self._fact_matches_query(fact_data["text"], fact_to_forget):
                    removed_items.append(fact_data["text"])
                    del self.memory["user_facts"][key]
            
            # Search and remove from user_preferences
            for key in list(self.memory["user_preferences"].keys()):
                pref_data = self.memory["user_preferences"][key]
                if self._fact_matches_query(pref_data["text"], fact_to_forget):
                    removed_items.append(pref_data["text"])
                    del self.memory["user_preferences"][key]
            
            self._save_memory()
            
            if removed_items:
                response = f"✅ I've forgotten {len(removed_items)} item(s) related to: {fact_to_forget}"
            else:
                response = "I don't have any information matching what you asked me to forget."
            
            logger.info(f"✅ Processed forget command - removed {len(removed_items)} items")
            
            return {
                "success": True,
                "is_memory_command": True,
                "action": "forget_fact",
                "query": fact_to_forget,
                "removed_count": len(removed_items),
                "response": response,
                "intent_data": {"intent": "forget_memory", "removed_count": len(removed_items)}
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing forget command: {e}")
            return {
                "success": False,
                "is_memory_command": True,
                "error": str(e),
                "response": "⚠️ I had trouble forgetting that information."
            }

    def _process_recall_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process recall commands with intelligent context assembly"""
        try:
            query = message.lower().strip()
            relevant_facts = []
            
            # Enhanced search through all memory categories
            all_facts = []
            
            # Collect facts from user_facts
            for key, fact_data in self.memory["user_facts"].items():
                all_facts.append(fact_data)
            
            # Collect facts from user_preferences
            for key, pref_data in self.memory["user_preferences"].items():
                all_facts.append(pref_data)
            
            # Intelligent matching with scoring
            scored_facts = []
            for fact_data in all_facts:
                score = self._calculate_relevance_score(fact_data["text"], query)
                if score > 0.1:  # Minimum relevance threshold
                    scored_facts.append((fact_data, score))
            
            # Sort by relevance score
            scored_facts.sort(key=lambda x: x[1], reverse=True)
            
            # Format response based on query type
            if scored_facts:
                response = self._format_recall_response(query, scored_facts[:5])  # Top 5 most relevant
            else:
                response = "I don't have specific information about that."
            
            logger.info(f"✅ Processed recall command - found {len(scored_facts)} relevant facts")
            
            return {
                "success": True,
                "is_memory_command": True,
                "action": "recall_memory",
                "query": message,
                "fact_count": len(scored_facts),
                "response": response,
                "intent_data": {"intent": "recall_memory", "fact_count": len(scored_facts)}
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing recall command: {e}")
            return {
                "success": False,
                "is_memory_command": True,
                "error": str(e),
                "response": "⚠️ I had trouble retrieving that information."
            }

    def _process_memory_management_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process memory management commands"""
        try:
            message_lower = message.lower()
            
            if "summarize memory" in message_lower or "memory summary" in message_lower:
                summary = self._generate_memory_summary()
                return {
                    "success": True,
                    "is_memory_command": True,
                    "action": "memory_summary",
                    "response": summary,
                    "intent_data": {"intent": "memory_summary"}
                }
            
            elif "clear all memory" in message_lower:
                cleared_count = self._clear_all_memory()
                return {
                    "success": True,
                    "is_memory_command": True,
                    "action": "clear_memory",
                    "cleared_count": cleared_count,
                    "response": f"✅ Cleared {cleared_count} memory items.",
                    "intent_data": {"intent": "clear_memory", "cleared_count": cleared_count}
                }
            
            else:
                return {
                    "success": False,
                    "is_memory_command": True,
                    "error": "Unknown memory management command"
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing memory management command: {e}")
            return {
                "success": False,
                "is_memory_command": True,
                "error": str(e)
            }

    def _process_preference_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process preference setting commands"""
        try:
            preference = self._extract_preference_from_message(message)
            pref_key = self._generate_preference_key(preference)
            
            pref_data = {
                "text": preference,
                "original_message": message,
                "category": "preferences",
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.memory["user_preferences"][pref_key] = pref_data
            self._save_memory()
            
            return {
                "success": True,
                "is_memory_command": True,
                "action": "set_preference",
                "preference": preference,
                "response": f"✅ I've noted your preference: {preference}",
                "intent_data": {"intent": "set_preference", "preference": preference}
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing preference command: {e}")
            return {
                "success": False,
                "is_memory_command": True,
                "error": str(e)
            }

    def _process_task_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process task/reminder commands"""
        try:
            task = self._extract_task_from_message(message)
            task_key = f"task_{len(self.memory['tasks_and_reminders'])}"
            
            task_data = {
                "text": task,
                "original_message": message,
                "category": "tasks",
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }
            
            self.memory["tasks_and_reminders"][task_key] = task_data
            self._save_memory()
            
            return {
                "success": True,
                "is_memory_command": True,
                "action": "add_task",
                "task": task,
                "response": f"✅ I'll remember to remind you: {task}",
                "intent_data": {"intent": "add_task", "task": task}
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing task command: {e}")
            return {
                "success": False,
                "is_memory_command": True,
                "error": str(e)
            }

    async def periodic_conversation_summary(self, session_id: str, messages: List[Dict]) -> Dict[str, Any]:
        """Periodically summarize conversations for long-term memory"""
        try:
            if len(messages) < 5:  # Don't summarize very short conversations
                return {"success": True, "summarized": False, "reason": "Too few messages"}
            
            # Check if we need to summarize
            last_summary_time = self.memory["conversation_summaries"].get(session_id, {}).get("last_summary_time")
            if last_summary_time:
                last_time = datetime.fromisoformat(last_summary_time)
                if (datetime.utcnow() - last_time).hours < 1:  # Don't summarize too frequently
                    return {"success": True, "summarized": False, "reason": "Too recent"}
            
            # Generate conversation summary
            summary = self._generate_conversation_summary(messages)
            
            # Extract key information for memory
            key_info = self._extract_key_information_from_conversation(messages)
            
            # Store summary
            if session_id not in self.memory["conversation_summaries"]:
                self.memory["conversation_summaries"][session_id] = {
                    "summaries": [],
                    "key_information": {},
                    "total_messages": 0
                }
            
            self.memory["conversation_summaries"][session_id]["summaries"].append({
                "summary": summary,
                "message_count": len(messages),
                "timestamp": datetime.utcnow().isoformat(),
                "key_info": key_info
            })
            
            self.memory["conversation_summaries"][session_id]["total_messages"] += len(messages)
            self.memory["conversation_summaries"][session_id]["last_summary_time"] = datetime.utcnow().isoformat()
            
            # Auto-store important facts discovered in conversation
            for fact in key_info.get("discovered_facts", []):
                self._auto_store_discovered_fact(fact, session_id)
            
            self._save_memory()
            
            logger.info(f"✅ Generated conversation summary for session {session_id}")
            
            return {
                "success": True,
                "summarized": True,
                "summary": summary,
                "discovered_facts": len(key_info.get("discovered_facts", []))
            }
            
        except Exception as e:
            logger.error(f"❌ Error in periodic conversation summary: {e}")
            return {"success": False, "error": str(e)}

    def _get_relevant_context(self, message: str, session_id: str) -> str:
        """Get relevant context for enhancing regular chat responses"""
        try:
            relevant_context = []
            
            # Get facts that might be relevant to the current message
            query_words = message.lower().split()
            
            # Check user_facts
            for key, fact_data in self.memory["user_facts"].items():
                fact_text = fact_data["text"].lower()
                if any(word in fact_text for word in query_words if len(word) > 2):
                    relevant_context.append(fact_data["text"])
            
            # Check user_preferences
            for key, pref_data in self.memory["user_preferences"].items():
                pref_text = pref_data["text"].lower()
                if any(word in pref_text for word in query_words if len(word) > 2):
                    relevant_context.append(pref_data["text"])
            
            # Check conversation summaries
            if session_id in self.memory["conversation_summaries"]:
                for summary_data in self.memory["conversation_summaries"][session_id]["summaries"][-3:]:  # Last 3 summaries
                    summary_text = summary_data["summary"].lower()
                    if any(word in summary_text for word in query_words if len(word) > 2):
                        relevant_context.append(f"Previous conversation: {summary_data['summary'][:100]}...")
            
            return "\n".join(relevant_context[:3])  # Limit to top 3 most relevant
            
        except Exception as e:
            logger.error(f"❌ Error getting relevant context: {e}")
            return ""

    # Helper methods for fact extraction and processing

    def _extract_fact_from_store_command(self, message: str) -> str:
        """Extract the actual fact from a store command"""
        message = message.strip()
        
        # Remove common store command prefixes
        prefixes = [
            "remember that", "remember this", "store fact", "save fact", "teach elva",
            "note that", "keep in mind that", "don't forget that", "make sure you remember"
        ]
        
        for prefix in prefixes:
            if message.lower().startswith(prefix):
                return message[len(prefix):].strip()
        
        # Handle "my X is Y" patterns
        if " is " in message and any(word in message.lower() for word in ["my", "i am", "call me"]):
            return message
        
        return message

    def _extract_fact_from_forget_command(self, message: str) -> str:
        """Extract what to forget from a forget command"""
        message_lower = message.lower()
        
        forget_prefixes = [
            "forget that", "forget about", "remove fact", "delete fact", "don't remember",
            "stop remembering", "clear fact", "remove from memory"
        ]
        
        for prefix in forget_prefixes:
            if message_lower.startswith(prefix):
                return message[len(prefix):].strip()
        
        return message

    def _categorize_fact(self, fact: str) -> str:
        """Categorize facts for better organization"""
        fact_lower = fact.lower()
        
        if any(word in fact_lower for word in ["nickname", "name", "call me", "i am"]):
            return "identity"
        elif any(word in fact_lower for word in ["prefer", "like", "favorite", "love", "hate", "dislike"]):
            return "preferences"
        elif any(word in fact_lower for word in ["manager", "boss", "colleague", "friend", "family", "work"]):
            return "relationships"
        elif any(word in fact_lower for word in ["email", "phone", "address", "contact"]):
            return "contact_info"
        elif any(word in fact_lower for word in ["remind", "task", "todo", "schedule", "meeting"]):
            return "tasks"
        elif any(word in fact_lower for word in ["skill", "knowledge", "experience", "expertise"]):
            return "abilities"
        else:
            return "general"

    def _generate_fact_key(self, fact: str, category: str) -> str:
        """Generate a unique key for facts"""
        fact_hash = hashlib.md5(fact.lower().encode()).hexdigest()[:8]
        return f"{category}_{fact_hash}"

    def _calculate_fact_confidence(self, fact: str) -> float:
        """Calculate confidence score for a fact"""
        # Simple heuristic based on fact characteristics
        confidence = 0.8  # Base confidence
        
        if any(word in fact.lower() for word in ["my", "i am", "i prefer"]):
            confidence += 0.1  # Personal statements are more confident
        
        if len(fact.split()) > 10:
            confidence += 0.1  # Longer facts tend to be more detailed
        
        return min(confidence, 1.0)

    def _fact_matches_query(self, fact: str, query: str) -> bool:
        """Check if a fact matches a forget query"""
        fact_lower = fact.lower()
        query_lower = query.lower()
        
        # Direct substring match
        if query_lower in fact_lower:
            return True
        
        # Word-based matching
        fact_words = set(fact_lower.split())
        query_words = set(query_lower.split())
        
        # If more than 50% of query words are in fact
        if len(query_words.intersection(fact_words)) / len(query_words) > 0.5:
            return True
        
        return False

    def _calculate_relevance_score(self, fact: str, query: str) -> float:
        """Calculate relevance score between fact and query"""
        fact_lower = fact.lower()
        query_lower = query.lower()
        
        score = 0.0
        
        # Direct substring match
        if query_lower in fact_lower:
            score += 0.8
        
        # Word overlap
        fact_words = set(fact_lower.split())
        query_words = set(query_lower.split())
        
        if len(query_words) > 0:
            overlap_ratio = len(fact_words.intersection(query_words)) / len(query_words)
            score += overlap_ratio * 0.6
        
        # Keyword matching
        important_words = [word for word in query_words if len(word) > 3]
        for word in important_words:
            if word in fact_lower:
                score += 0.2
        
        return min(score, 1.0)

    def _format_recall_response(self, query: str, scored_facts: List[Tuple]) -> str:
        """Format recall response based on query and facts"""
        if not scored_facts:
            return "I don't have specific information about that."
        
        query_lower = query.lower()
        
        # Check what type of information is being requested
        if "what's my" in query_lower or "my" in query_lower:
            # Personal information request
            response = "Here's what I know about you:\n\n"
        elif "what do you remember" in query_lower:
            # General memory request
            response = "Here's what I remember:\n\n"
        else:
            # Specific query
            response = "Based on what I know:\n\n"
        
        for i, (fact_data, score) in enumerate(scored_facts[:3], 1):  # Top 3 results
            response += f"{i}. {fact_data['text']}\n"
        
        if len(scored_facts) > 3:
            response += f"\n...and {len(scored_facts) - 3} more items."
        
        return response

    def _generate_memory_summary(self) -> str:
        """Generate a comprehensive memory summary"""
        total_facts = len(self.memory["user_facts"])
        total_prefs = len(self.memory["user_preferences"])
        total_tasks = len(self.memory["tasks_and_reminders"])
        total_sessions = len(self.memory["conversation_summaries"])
        
        categories = defaultdict(int)
        for fact_data in self.memory["user_facts"].values():
            categories[fact_data["category"]] += 1
        
        summary = f"📊 **Memory Summary**\n\n"
        summary += f"• Total Facts: {total_facts}\n"
        summary += f"• User Preferences: {total_prefs}\n"
        summary += f"• Tasks & Reminders: {total_tasks}\n"
        summary += f"• Conversation Sessions: {total_sessions}\n\n"
        
        if categories:
            summary += "**Fact Categories:**\n"
            for category, count in categories.items():
                summary += f"• {category.title()}: {count}\n"
        
        return summary

    def _clear_all_memory(self) -> int:
        """Clear all memory and return count of cleared items"""
        total_cleared = (
            len(self.memory["user_facts"]) + 
            len(self.memory["user_preferences"]) + 
            len(self.memory["tasks_and_reminders"]) + 
            len(self.memory["conversation_summaries"])
        )
        
        self.memory["user_facts"] = {}
        self.memory["user_preferences"] = {}
        self.memory["tasks_and_reminders"] = {}
        self.memory["conversation_summaries"] = {}
        
        self._save_memory()
        return total_cleared

    def _extract_preference_from_message(self, message: str) -> str:
        """Extract preference from preference command"""
        # Remove common preference prefixes
        prefixes = ["i prefer", "i like", "i don't like", "my preference is", "set preference to"]
        
        message_lower = message.lower()
        for prefix in prefixes:
            if message_lower.startswith(prefix):
                return message[len(prefix):].strip()
        
        return message

    def _generate_preference_key(self, preference: str) -> str:
        """Generate key for preferences"""
        pref_hash = hashlib.md5(preference.lower().encode()).hexdigest()[:8]
        return f"pref_{pref_hash}"

    def _extract_task_from_message(self, message: str) -> str:
        """Extract task from task command"""
        prefixes = ["remind me to", "remember to remind me", "set a reminder", "don't let me forget"]
        
        message_lower = message.lower()
        for prefix in prefixes:
            if message_lower.startswith(prefix):
                return message[len(prefix):].strip()
        
        return message

    def _generate_conversation_summary(self, messages: List[Dict]) -> str:
        """Generate a concise summary of conversation messages"""
        # Simple summarization - in a real implementation, you might use an AI model
        topics = []
        key_points = []
        
        for msg in messages:
            if msg.get("role") == "user":
                text = msg.get("content", "").lower()
                if any(word in text for word in ["help", "question", "problem", "issue"]):
                    topics.append("user seeking help")
                elif any(word in text for word in ["thank", "thanks", "appreciate"]):
                    topics.append("user expressing gratitude")
                elif "?" in text:
                    topics.append("user asking questions")
        
        if not topics:
            return "General conversation with user"
        
        return f"Conversation involving: {', '.join(set(topics))}"

    def _extract_key_information_from_conversation(self, messages: List[Dict]) -> Dict:
        """Extract key information that should be remembered from conversation"""
        discovered_facts = []
        user_preferences = []
        
        for msg in messages:
            if msg.get("role") == "user":
                text = msg.get("content", "")
                
                # Look for personal information reveals
                if any(phrase in text.lower() for phrase in ["my name is", "i am", "call me"]):
                    discovered_facts.append(text)
                elif any(phrase in text.lower() for phrase in ["i prefer", "i like", "i love", "i hate"]):
                    user_preferences.append(text)
        
        return {
            "discovered_facts": discovered_facts,
            "user_preferences": user_preferences
        }

    def _auto_store_discovered_fact(self, fact: str, session_id: str):
        """Automatically store facts discovered during conversation"""
        try:
            category = self._categorize_fact(fact)
            fact_key = self._generate_fact_key(fact, category)
            
            fact_data = {
                "text": fact,
                "category": category,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "auto_discovered": True,
                "confidence": 0.6  # Lower confidence for auto-discovered facts
            }
            
            if category == "preferences":
                self.memory["user_preferences"][fact_key] = fact_data
            else:
                self.memory["user_facts"][fact_key] = fact_data
            
            logger.info(f"✅ Auto-stored discovered fact: {fact[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Error auto-storing discovered fact: {e}")

    async def periodic_conversation_summarization(self, session_id: str, messages: List[Dict]) -> Dict[str, Any]:
        """
        Advanced periodic conversation summarization with AI-powered insights
        """
        try:
            logger.info(f"🔄 Starting periodic summarization for session: {session_id}")
            
            # Check if summarization is needed
            if not self._should_create_summary(session_id, messages):
                return {"success": False, "reason": "Summarization not needed yet"}
            
            # Create conversation summary using AI
            summary_result = await self._create_ai_conversation_summary(messages)
            
            # Extract key insights and patterns
            insights = self._extract_conversation_insights(messages)
            
            # Create comprehensive summary entry
            summary_entry = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "message_count": len(messages),
                "summary": summary_result["summary"],
                "key_topics": summary_result["topics"],
                "user_intent_patterns": insights["intent_patterns"],
                "discovered_facts": insights["discovered_facts"],
                "mood_indicators": insights["mood_indicators"],
                "interaction_quality": insights["interaction_quality"],
                "follow_up_needed": insights["follow_up_needed"]
            }
            
            # Store summary
            self.memory["conversation_summaries"][session_id] = summary_entry
            
            # Update daily aggregation
            await self._update_daily_summary(summary_entry)
            
            # Auto-store any discovered facts
            for fact in insights["discovered_facts"]:
                self._auto_store_discovered_fact(fact, session_id)
            
            # Update memory metadata
            self.memory["memory_metadata"]["last_summarization"] = datetime.utcnow().isoformat()
            self.memory["memory_metadata"]["total_conversations"] += 1
            
            self._save_memory()
            
            logger.info(f"✅ Periodic summarization completed for session: {session_id}")
            return {
                "success": True,
                "summary": summary_entry,
                "facts_discovered": len(insights["discovered_facts"])
            }
            
        except Exception as e:
            logger.error(f"❌ Error in periodic conversation summarization: {e}")
            return {"success": False, "error": str(e)}

    def _should_create_summary(self, session_id: str, messages: List[Dict]) -> bool:
        """Determine if conversation summary should be created"""
        try:
            # Check message count threshold
            if len(messages) < self.MIN_MESSAGES_FOR_SUMMARY:
                return False
            
            # Check if recent summary exists
            existing_summary = self.memory["conversation_summaries"].get(session_id)
            if existing_summary:
                last_summary_time = datetime.fromisoformat(existing_summary["created_at"])
                time_since_summary = (datetime.utcnow() - last_summary_time).total_seconds()
                if time_since_summary < self.SUMMARIZATION_INTERVAL:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking if summary should be created: {e}")
            return False

    async def _create_ai_conversation_summary(self, messages: List[Dict]) -> Dict[str, Any]:
        """Create AI-powered conversation summary using Groq"""
        try:
            # Prepare conversation context
            conversation_text = self._format_conversation_for_summary(messages)
            
            # Use advanced hybrid AI for summarization
            from advanced_hybrid_ai import advanced_hybrid_ai
            
            summary_prompt = f"""Analyze this conversation and provide a comprehensive summary:

{conversation_text}

Please provide:
1. A concise summary (2-3 sentences)
2. Key topics discussed (list)
3. User's main intents/needs
4. Any important facts about the user mentioned
5. Overall conversation quality (1-10 scale)

Format as JSON with keys: summary, topics, intents, user_facts, quality_score"""

            result = await advanced_hybrid_ai(
                message=summary_prompt,
                session_id="memory_summarization",
                context="conversation_analysis"
            )
            
            # Parse AI response
            try:
                import json
                parsed_result = json.loads(result.get("response", "{}"))
                return {
                    "summary": parsed_result.get("summary", "Conversation with user"),
                    "topics": parsed_result.get("topics", []),
                    "intents": parsed_result.get("intents", []),
                    "user_facts": parsed_result.get("user_facts", []),
                    "quality_score": parsed_result.get("quality_score", 7)
                }
            except:
                # Fallback to simple summary
                return self._create_simple_summary(messages)
                
        except Exception as e:
            logger.error(f"❌ Error creating AI conversation summary: {e}")
            return self._create_simple_summary(messages)

    def _format_conversation_for_summary(self, messages: List[Dict]) -> str:
        """Format conversation messages for AI summarization"""
        formatted_lines = []
        for msg in messages[-20:]:  # Use last 20 messages to avoid token limits
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                formatted_lines.append(f"{role.upper()}: {content[:200]}")  # Truncate long messages
        
        return "\n".join(formatted_lines)

    def _create_simple_summary(self, messages: List[Dict]) -> Dict[str, Any]:
        """Fallback simple conversation summary"""
        topics = set()
        user_messages = []
        
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                user_messages.append(content)
                
                # Extract topics
                if "email" in content:
                    topics.add("email")
                if "calendar" in content or "meeting" in content:
                    topics.add("scheduling")
                if "gmail" in content:
                    topics.add("gmail")
                if "weather" in content:
                    topics.add("weather")
        
        return {
            "summary": f"User engaged in conversation covering {len(topics)} main topics",
            "topics": list(topics),
            "intents": ["general_assistance"],
            "user_facts": [],
            "quality_score": 7
        }

    def _extract_conversation_insights(self, messages: List[Dict]) -> Dict[str, Any]:
        """Extract deep insights from conversation patterns"""
        insights = {
            "intent_patterns": [],
            "discovered_facts": [],
            "mood_indicators": [],
            "interaction_quality": 7,
            "follow_up_needed": []
        }
        
        try:
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            
            # Analyze intent patterns
            intents = []
            for msg in user_messages:
                content = msg.get("content", "").lower()
                if "send email" in content or "email" in content:
                    intents.append("email_assistance")
                elif "schedule" in content or "calendar" in content:
                    intents.append("scheduling")
                elif "remember" in content or "remind" in content:
                    intents.append("memory_management")
                elif "?" in content:
                    intents.append("information_seeking")
            
            insights["intent_patterns"] = list(set(intents))
            
            # Extract discovered facts
            for msg in user_messages:
                content = msg.get("content", "")
                if any(phrase in content.lower() for phrase in ["my name is", "i am", "call me"]):
                    insights["discovered_facts"].append(content)
                elif any(phrase in content.lower() for phrase in ["i prefer", "i like", "i work"]):
                    insights["discovered_facts"].append(content)
            
            # Analyze mood indicators
            mood_words = {
                "positive": ["great", "awesome", "perfect", "thanks", "love", "excellent"],
                "negative": ["problem", "issue", "frustrated", "annoying", "bad"],
                "neutral": ["okay", "fine", "alright"]
            }
            
            for msg in user_messages:
                content = msg.get("content", "").lower()
                for mood, words in mood_words.items():
                    if any(word in content for word in words):
                        insights["mood_indicators"].append(mood)
            
            # Determine follow-up needs
            last_messages = user_messages[-3:]  # Check last 3 user messages
            for msg in last_messages:
                content = msg.get("content", "").lower()
                if any(word in content for word in ["later", "tomorrow", "remind", "follow up"]):
                    insights["follow_up_needed"].append("schedule_followup")
                elif "more info" in content or "tell me more" in content:
                    insights["follow_up_needed"].append("provide_more_info")
            
            # Calculate interaction quality
            total_exchanges = len(messages) / 2  # Approximate user-AI exchanges
            if total_exchanges > 10:
                insights["interaction_quality"] = 9
            elif total_exchanges > 5:
                insights["interaction_quality"] = 8
            else:
                insights["interaction_quality"] = 7
            
        except Exception as e:
            logger.error(f"❌ Error extracting conversation insights: {e}")
        
        return insights

    async def _update_daily_summary(self, summary_entry: Dict[str, Any]):
        """Update daily conversation summaries"""
        try:
            today = datetime.utcnow().date().isoformat()
            
            if today not in self.memory["daily_summaries"]:
                self.memory["daily_summaries"][today] = {
                    "date": today,
                    "conversation_count": 0,
                    "total_messages": 0,
                    "dominant_topics": [],
                    "user_facts_discovered": 0,
                    "quality_average": 0,
                    "sessions": []
                }
            
            daily_summary = self.memory["daily_summaries"][today]
            daily_summary["conversation_count"] += 1
            daily_summary["total_messages"] += summary_entry["message_count"]
            daily_summary["user_facts_discovered"] += len(summary_entry["discovered_facts"])
            daily_summary["sessions"].append(summary_entry["session_id"])
            
            # Update dominant topics
            all_topics = daily_summary["dominant_topics"] + summary_entry["key_topics"]
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Keep top 5 topics
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            daily_summary["dominant_topics"] = [topic for topic, count in sorted_topics[:5]]
            
            # Update quality average
            total_quality = sum(session.get("interaction_quality", 7) 
                              for session in [summary_entry] + 
                              [self.memory["conversation_summaries"].get(sid, {}) 
                               for sid in daily_summary["sessions"][:-1]])
            daily_summary["quality_average"] = round(total_quality / daily_summary["conversation_count"], 1)
            
            # Update last daily summary timestamp
            self.memory["memory_metadata"]["last_daily_summary"] = datetime.utcnow().isoformat()
            
            logger.info(f"✅ Updated daily summary for {today}")
            
        except Exception as e:
            logger.error(f"❌ Error updating daily summary: {e}")

    async def trigger_periodic_summarization_if_needed(self, session_id: str) -> Dict[str, Any]:
        """
        Check if periodic summarization is needed and trigger it
        This should be called after significant conversation activity
        """
        try:
            # Get recent conversation messages from message_memory
            from message_memory import get_conversation_history
            messages = await get_conversation_history(session_id, limit=50)
            
            if not messages:
                return {"success": False, "reason": "No messages to summarize"}
            
            # Convert to format expected by summarization
            formatted_messages = []
            for msg in messages:
                role = "user" if msg.get("isUser", False) else "assistant"
                content = msg.get("message") or msg.get("response", "")
                if content:
                    formatted_messages.append({"role": role, "content": content})
            
            # Trigger summarization if needed
            return await self.periodic_conversation_summarization(session_id, formatted_messages)
            
        except Exception as e:
            logger.error(f"❌ Error checking for periodic summarization: {e}")
            return {"success": False, "error": str(e)}

    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get existing conversation summary for a session"""
        return self.memory["conversation_summaries"].get(session_id)

    def get_daily_summary(self, date: str = None) -> Optional[Dict[str, Any]]:
        """Get daily conversation summary"""
        if not date:
            date = datetime.utcnow().date().isoformat()
        return self.memory["daily_summaries"].get(date)

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        return {
            "total_facts": len(self.memory["user_facts"]),
            "total_preferences": len(self.memory["user_preferences"]),
            "conversation_summaries": len(self.memory["conversation_summaries"]),
            "daily_summaries": len(self.memory["daily_summaries"]),
            "tasks_and_reminders": len(self.memory["tasks_and_reminders"]),
            "memory_metadata": self.memory["memory_metadata"],
            "cache_status": {
                "is_valid": self._is_cache_valid(),
                "last_updated": self._cache_timestamp.isoformat() if self._cache_timestamp else None
            }
        }


# Global enhanced memory instance
enhanced_letta_memory: Optional[EnhancedLettaMemory] = None

def get_enhanced_letta_memory() -> EnhancedLettaMemory:
    """Get or create the global enhanced Letta memory instance"""
    global enhanced_letta_memory
    if enhanced_letta_memory is None:
        enhanced_letta_memory = EnhancedLettaMemory()
    return enhanced_letta_memory

def initialize_enhanced_letta_memory() -> EnhancedLettaMemory:
    """Initialize enhanced Letta memory system"""
    try:
        memory = get_enhanced_letta_memory()
        logger.info("✅ Enhanced Letta memory system initialized")
        return memory
    except Exception as e:
        logger.error(f"❌ Failed to initialize enhanced Letta memory: {e}")
        raise