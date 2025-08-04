"""
Semantic Letta Memory System for Elva AI
Enhanced memory with semantic fact extraction, natural responses, and automatic deduplication.
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
import uuid
from dataclasses import dataclass
from enum import Enum

# Import existing AI models for semantic processing
from advanced_hybrid_ai import generate_friendly_draft, handle_general_chat

logger = logging.getLogger(__name__)

class ResponseStyle(Enum):
    NATURAL_BRIEF = "natural_brief"  # "Got it 👍", "Sure"
    CONVERSATIONAL = "conversational"  # Continue conversation naturally
    SILENT = "silent"  # No confirmation, just store

@dataclass
class SemanticFact:
    """Represents a semantically extracted fact"""
    id: str
    content: str  # The actual meaningful fact
    category: str
    confidence: float
    source_message: str  # Original message for reference
    session_id: str
    created_at: str
    updated_at: str
    related_facts: List[str] = None  # IDs of related facts
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.related_facts is None:
            self.related_facts = []
        if self.metadata is None:
            self.metadata = {}

class SemanticLettaMemory:
    def __init__(self, memory_dir: str = "/app/backend/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / "semantic_memory.json"
        
        # Enhanced semantic memory structure
        self.memory = {
            "user_identity": {},  # Name, nickname, personal info
            "preferences": {},  # Likes, dislikes, preferences
            "relationships": {},  # People, work, family
            "facts": {},  # General facts about user
            "skills_abilities": {},  # What user can do/knows
            "goals_tasks": {},  # User's objectives and tasks
            "communication_style": {},  # How user prefers to communicate
            "contexts": {},  # Contextual information
            "fact_relationships": {},  # Connections between facts
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "total_facts": 0,
                "deduplication_count": 0,
                "semantic_extractions": 0
            }
        }
        
        # Natural response templates
        self.natural_confirmations = [
            "Got it 👍",
            "Sure, noted",
            "Alright",
            "Perfect",
            "Understood",
            "Cool",
            "Nice to know",
            "Thanks for letting me know"
        ]
        
        # Load existing memory
        self._load_memory()
        
    def _load_memory(self):
        """Load memory from file with migration support"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r') as f:
                    loaded_memory = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.memory.update(loaded_memory)
                logger.info("✅ Loaded semantic memory from file")
            else:
                self._save_memory()
                logger.info("✅ Created new semantic memory file")
        except Exception as e:
            logger.error(f"❌ Error loading semantic memory: {e}")

    def _save_memory(self):
        """Save memory to file with metadata updates"""
        try:
            self.memory["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            self.memory["metadata"]["total_facts"] = sum(
                len(category) for key, category in self.memory.items() 
                if key not in ["metadata", "fact_relationships"]
            )
            
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
            logger.info("✅ Semantic memory saved successfully")
        except Exception as e:
            logger.error(f"❌ Error saving semantic memory: {e}")

    async def process_message_for_memory(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Main entry point for processing messages with semantic understanding
        Returns: {
            "is_memory_operation": bool,
            "facts_extracted": List[SemanticFact],
            "response": str,
            "response_style": ResponseStyle,
            "needs_natural_continuation": bool
        }
        """
        try:
            message_lower = message.lower().strip()
            
            # Check if this is a memory-related command
            memory_command_type = self._detect_memory_command_type(message_lower)
            
            if memory_command_type == "store":
                return await self._handle_store_command(message, session_id)
            elif memory_command_type == "forget":
                return await self._handle_forget_command(message, session_id)
            elif memory_command_type == "recall":
                return await self._handle_recall_command(message, session_id)
            else:
                # Not a direct memory command, but check for implicit facts
                implicit_facts = await self._extract_implicit_facts(message, session_id)
                if implicit_facts:
                    await self._store_facts_silently(implicit_facts, session_id)
                    return {
                        "is_memory_operation": False,
                        "facts_extracted": implicit_facts,
                        "response": "",
                        "response_style": ResponseStyle.SILENT,
                        "needs_natural_continuation": True,
                        "implicit_learning": True
                    }
                
                # No memory operation detected
                return {
                    "is_memory_operation": False,
                    "facts_extracted": [],
                    "response": "",
                    "response_style": ResponseStyle.SILENT,
                    "needs_natural_continuation": False
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing message for memory: {e}")
            return {
                "is_memory_operation": False,
                "facts_extracted": [],
                "response": "",
                "response_style": ResponseStyle.SILENT,
                "needs_natural_continuation": False,
                "error": str(e)
            }

    def _detect_memory_command_type(self, message_lower: str) -> Optional[str]:
        """Detect the type of memory command"""
        # Store commands
        store_patterns = [
            "remember that", "remember this", "store this", "note that",
            "my name is", "call me", "i am", "i like", "i prefer",
            "my favorite", "i love", "i hate", "i dislike", "keep in mind"
        ]
        
        # Forget commands  
        forget_patterns = [
            "forget that", "forget about", "don't remember", "remove from memory",
            "stop remembering", "delete that fact", "clear that information"
        ]
        
        # Recall commands
        recall_patterns = [
            "what do you remember", "what do you know about me", "tell me about",
            "what's my", "who am i", "what are my", "do you remember", 
            "remind me", "what did i tell you", "what do i like"
        ]
        
        for pattern in store_patterns:
            if pattern in message_lower:
                return "store"
                
        for pattern in forget_patterns:
            if pattern in message_lower:
                return "forget"
                
        for pattern in recall_patterns:
            if pattern in message_lower:
                return "recall"
                
        return None

    async def _handle_store_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Handle explicit memory storage commands with semantic extraction"""
        try:
            # Extract semantic facts using AI
            facts = await self._extract_semantic_facts(message, session_id)
            
            if not facts:
                return {
                    "is_memory_operation": True,
                    "facts_extracted": [],
                    "response": "I didn't catch anything specific to remember from that.",
                    "response_style": ResponseStyle.NATURAL_BRIEF,
                    "needs_natural_continuation": False
                }
            
            # Store facts with deduplication
            stored_facts = []
            for fact in facts:
                stored_fact = await self._store_fact_with_deduplication(fact, session_id)
                if stored_fact:
                    stored_facts.append(stored_fact)
            
            # Generate natural confirmation response
            response = self._generate_natural_confirmation(stored_facts)
            
            return {
                "is_memory_operation": True,
                "facts_extracted": stored_facts,
                "response": response,
                "response_style": ResponseStyle.NATURAL_BRIEF,
                "needs_natural_continuation": False
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling store command: {e}")
            return {
                "is_memory_operation": True,
                "facts_extracted": [],
                "response": "Got it",  # Simple fallback
                "response_style": ResponseStyle.NATURAL_BRIEF,
                "needs_natural_continuation": False,
                "error": str(e)
            }

    async def _handle_forget_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Handle memory deletion commands"""
        try:
            # Extract what to forget using semantic understanding
            forget_target = await self._extract_forget_target(message)
            
            # Find and remove matching facts
            removed_facts = self._remove_matching_facts(forget_target)
            
            if removed_facts:
                response = f"Okay, I've forgotten about that."
            else:
                response = "I don't think I had that information anyway."
            
            self._save_memory()
            
            return {
                "is_memory_operation": True,
                "facts_removed": len(removed_facts),
                "response": response,
                "response_style": ResponseStyle.NATURAL_BRIEF,
                "needs_natural_continuation": False
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling forget command: {e}")
            return {
                "is_memory_operation": True,
                "facts_removed": 0,
                "response": "Alright",
                "response_style": ResponseStyle.NATURAL_BRIEF,
                "needs_natural_continuation": False,
                "error": str(e)
            }

    async def _handle_recall_command(self, message: str, session_id: str) -> Dict[str, Any]:
        """Handle memory recall commands with natural responses"""
        try:
            # Extract what user is asking about
            recall_query = await self._extract_recall_query(message)
            
            # Find relevant facts
            relevant_facts = self._find_relevant_facts(recall_query)
            
            # Generate natural response
            response = self._generate_natural_recall_response(recall_query, relevant_facts)
            
            return {
                "is_memory_operation": True,
                "facts_retrieved": len(relevant_facts),
                "response": response,
                "response_style": ResponseStyle.CONVERSATIONAL,
                "needs_natural_continuation": False,
                "relevant_facts": relevant_facts
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling recall command: {e}")
            return {
                "is_memory_operation": True,
                "facts_retrieved": 0,
                "response": "I don't have specific information about that.",
                "response_style": ResponseStyle.CONVERSATIONAL,
                "needs_natural_continuation": False,
                "error": str(e)
            }

    async def _extract_semantic_facts(self, message: str, session_id: str) -> List[SemanticFact]:
        """Extract meaningful facts from user message using AI"""
        try:
            # Use the existing AI system for semantic extraction
            extraction_prompt = f"""
Extract meaningful facts from this user message. Focus on personal information, preferences, and important details.

User message: "{message}"

Extract only the core facts, not the command itself. Here are examples:
- "remember that I like samosas and murmura" → "likes samosas and murmura"  
- "my name is John" → "name is John"  
- "call me Mike" → "nickname is Mike"
- "I prefer working in the morning" → "prefers working in the morning"

Return only the meaningful facts, not the instruction text. If there are multiple facts, separate them with |

Facts:"""
            
            # Use Claude for semantic extraction
            response = await handle_general_chat(extraction_prompt, session_id, "")
            
            if not response or len(response.strip()) < 2:
                return []
            
            # Parse extracted facts
            facts = []
            fact_texts = [f.strip() for f in response.split('|') if f.strip()]
            
            for fact_text in fact_texts:
                # Clean up the fact text
                fact_text = fact_text.strip().strip('"').strip("'")
                
                # Skip if too short or if it looks like a question
                if len(fact_text) < 5 or fact_text.endswith('?'):
                    continue
                    
                # Make sure it starts with a proper fact format
                if not any(word in fact_text.lower() for word in ['like', 'name', 'prefer', 'love', 'hate', 'is', 'work', 'live']):
                    continue
                
                fact = SemanticFact(
                    id=str(uuid.uuid4()),
                    content=fact_text.lower(),  # Normalize to lowercase
                    category=self._categorize_semantic_fact(fact_text),
                    confidence=0.8,  # Default confidence
                    source_message=message,
                    session_id=session_id,
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat()
                )
                facts.append(fact)
            
            self.memory["metadata"]["semantic_extractions"] += len(facts)
            return facts
            
        except Exception as e:
            logger.error(f"❌ Error extracting semantic facts: {e}")
            # Fallback to simple extraction
            return self._simple_fact_extraction(message, session_id)

    def _simple_fact_extraction(self, message: str, session_id: str) -> List[SemanticFact]:
        """Fallback simple fact extraction if AI fails"""
        try:
            message_lower = message.lower().strip()
            
            # Remove command prefixes
            prefixes = ["remember that", "remember this", "note that", "keep in mind that", "store"]
            extracted_content = message_lower
            
            for prefix in prefixes:
                if message_lower.startswith(prefix):
                    extracted_content = message_lower[len(prefix):].strip()
                    break
            
            # Skip if it's a question (recall attempt)
            if extracted_content.endswith('?') or any(word in extracted_content for word in ['what', 'who', 'when', 'where', 'how']):
                return []
            
            # Only extract if it contains meaningful personal info
            if len(extracted_content) > 5 and any(word in extracted_content for word in 
                ['like', 'love', 'prefer', 'name is', 'am', 'work', 'live', 'hate', 'dislike']):
                
                fact = SemanticFact(
                    id=str(uuid.uuid4()),
                    content=extracted_content,
                    category=self._categorize_semantic_fact(extracted_content),
                    confidence=0.6,  # Lower confidence for simple extraction
                    source_message=message,
                    session_id=session_id,
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat()
                )
                return [fact]
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Error in simple fact extraction: {e}")
            return []

    def _categorize_semantic_fact(self, fact_text: str) -> str:
        """Categorize facts semantically"""
        fact_lower = fact_text.lower()
        
        # Identity patterns
        if any(word in fact_lower for word in ["name is", "called", "nickname", "i am"]):
            return "user_identity"
        
        # Preference patterns
        elif any(word in fact_lower for word in ["like", "love", "prefer", "favorite", "enjoy", "hate", "dislike"]):
            return "preferences"
        
        # Relationship patterns
        elif any(word in fact_lower for word in ["work", "job", "manager", "boss", "colleague", "friend", "family"]):
            return "relationships"
        
        # Skills/abilities patterns
        elif any(word in fact_lower for word in ["can", "know how", "experience", "skill", "good at", "expert"]):
            return "skills_abilities"
        
        # Goals/tasks patterns
        elif any(word in fact_lower for word in ["want to", "goal", "plan to", "working on", "project", "task"]):
            return "goals_tasks"
        
        # Communication style patterns
        elif any(word in fact_lower for word in ["call me", "address me", "speak to me", "communicate"]):
            return "communication_style"
        
        else:
            return "facts"

    async def _store_fact_with_deduplication(self, fact: SemanticFact, session_id: str) -> Optional[SemanticFact]:
        """Store fact with automatic deduplication and merging"""
        try:
            category_facts = self.memory.get(fact.category, {})
            
            # Check for similar existing facts
            similar_fact_id = self._find_similar_fact(fact, category_facts)
            
            if similar_fact_id:
                # Update existing fact instead of creating duplicate
                existing_fact = category_facts[similar_fact_id]
                updated_fact = self._merge_facts(existing_fact, fact)
                category_facts[similar_fact_id] = updated_fact.__dict__
                self.memory["metadata"]["deduplication_count"] += 1
                logger.info(f"🔄 Merged similar fact: {fact.content[:50]}...")
                fact_to_return = updated_fact
            else:
                # Store new fact
                category_facts[fact.id] = fact.__dict__
                fact_to_return = fact
            
            # Ensure category exists in memory
            self.memory[fact.category] = category_facts
            self._save_memory()
            
            return fact_to_return
            
        except Exception as e:
            logger.error(f"❌ Error storing fact with deduplication: {e}")
            return fact

    def _find_similar_fact(self, new_fact: SemanticFact, existing_facts: Dict[str, Any]) -> Optional[str]:
        """Find similar existing fact for deduplication"""
        new_content_lower = new_fact.content.lower()
        new_words = set(new_content_lower.split())
        
        for fact_id, fact_data in existing_facts.items():
            existing_content_lower = fact_data["content"].lower()
            existing_words = set(existing_content_lower.split())
            
            # Calculate word overlap
            overlap = len(new_words.intersection(existing_words))
            total_words = len(new_words.union(existing_words))
            
            if total_words > 0:
                similarity = overlap / total_words
                
                # If very similar (70%+ word overlap), consider it duplicate
                if similarity >= 0.7:
                    return fact_id
                    
                # Special cases for identity facts
                if new_fact.category == "user_identity":
                    if any(word in both for both in [new_content_lower, existing_content_lower] 
                           for word in ["name", "called", "nickname"]):
                        return fact_id
        
        return None

    def _merge_facts(self, existing_fact_data: Dict[str, Any], new_fact: SemanticFact) -> SemanticFact:
        """Merge new fact with existing fact intelligently"""
        try:
            # Create SemanticFact from existing data
            existing_fact = SemanticFact(
                id=existing_fact_data["id"],
                content=existing_fact_data["content"],
                category=existing_fact_data["category"],
                confidence=existing_fact_data.get("confidence", 0.5),
                source_message=existing_fact_data["source_message"],
                session_id=existing_fact_data["session_id"],
                created_at=existing_fact_data["created_at"],
                updated_at=datetime.utcnow().isoformat(),
                related_facts=existing_fact_data.get("related_facts", []),
                metadata=existing_fact_data.get("metadata", {})
            )
            
            # Merge logic based on category
            if new_fact.category == "preferences":
                # For preferences, update with newest information
                merged_content = new_fact.content
            elif new_fact.category == "user_identity":
                # For identity, prefer more recent/specific info
                merged_content = new_fact.content if len(new_fact.content) > len(existing_fact.content) else existing_fact.content
            else:
                # For general facts, combine if different enough
                if new_fact.content.lower() not in existing_fact.content.lower():
                    merged_content = f"{existing_fact.content}; {new_fact.content}"
                else:
                    merged_content = new_fact.content
            
            # Update the existing fact
            existing_fact.content = merged_content
            existing_fact.updated_at = datetime.utcnow().isoformat()
            existing_fact.confidence = max(existing_fact.confidence, new_fact.confidence)
            
            # Add source message to metadata
            if "source_messages" not in existing_fact.metadata:
                existing_fact.metadata["source_messages"] = []
            existing_fact.metadata["source_messages"].append(new_fact.source_message)
            
            return existing_fact
            
        except Exception as e:
            logger.error(f"❌ Error merging facts: {e}")
            return new_fact

    def _generate_natural_confirmation(self, facts: List[SemanticFact]) -> str:
        """Generate natural, human-like confirmation responses"""
        if not facts:
            return "Got it 👍"
        
        # For single facts, use brief confirmations
        if len(facts) == 1:
            import random
            confirmations = [
                "Got it 👍",
                "Sure, noted",
                "Perfect",
                "Cool",
                "Alright",
                "Nice to know"
            ]
            return random.choice(confirmations)
        
        # For multiple facts, acknowledge plurality but stay natural
        return "Got all that 👍"

    async def _extract_recall_query(self, message: str) -> str:
        """Extract what the user is asking to recall"""
        message_lower = message.lower()
        
        # Remove question prefixes
        prefixes = [
            "what do you remember about", "what do you know about", 
            "tell me about", "what's my", "what are my", "do you remember"
        ]
        
        query = message_lower
        for prefix in prefixes:
            if message_lower.startswith(prefix):
                query = message_lower[len(prefix):].strip()
                break
        
        # Clean up common question words
        query = re.sub(r'^(me|my|i|about|what|who|when|where|how)', '', query).strip()
        
        return query if query else message_lower

    def _find_relevant_facts(self, query: str) -> List[Dict[str, Any]]:
        """Find facts relevant to the query"""
        query_words = set(query.lower().split())
        relevant_facts = []
        
        # Search through all categories
        for category_name, category_facts in self.memory.items():
            if category_name in ["metadata", "fact_relationships"]:
                continue
                
            for fact_id, fact_data in category_facts.items():
                if isinstance(fact_data, dict) and "content" in fact_data:
                    fact_words = set(fact_data["content"].lower().split())
                    
                    # Calculate relevance score
                    overlap = len(query_words.intersection(fact_words))
                    if overlap > 0 or any(word in fact_data["content"].lower() for word in query_words):
                        relevant_facts.append({
                            "fact": fact_data,
                            "category": category_name,
                            "relevance": overlap
                        })
        
        # Sort by relevance
        relevant_facts.sort(key=lambda x: x["relevance"], reverse=True)
        
        return relevant_facts[:5]  # Return top 5 most relevant

    def _generate_natural_recall_response(self, query: str, relevant_facts: List[Dict[str, Any]]) -> str:
        """Generate natural, conversational recall responses"""
        if not relevant_facts:
            return "I don't have specific information about that."
        
        # Generate response based on query type and facts
        response_parts = []
        
        for fact_info in relevant_facts:
            fact = fact_info["fact"]
            category = fact_info["category"]
            
            # Format fact naturally based on category
            if category == "user_identity":
                if "name" in fact["content"].lower():
                    response_parts.append(f"Your {fact['content']}")
                else:
                    response_parts.append(fact["content"])
            elif category == "preferences":
                response_parts.append(f"You {fact['content']}")
            else:
                response_parts.append(fact["content"])
        
        # Combine response parts naturally
        if len(response_parts) == 1:
            return response_parts[0].capitalize() + "."
        elif len(response_parts) == 2:
            return f"{response_parts[0].capitalize()}, and {response_parts[1]}."
        else:
            return f"{response_parts[0].capitalize()}. Also, " + ", ".join(response_parts[1:]) + "."

    async def _extract_implicit_facts(self, message: str, session_id: str) -> List[SemanticFact]:
        """Extract implicit facts from casual conversation"""
        # This could be enhanced to detect implicit facts in casual conversation
        # For now, return empty list to avoid over-extraction
        return []

    async def _store_facts_silently(self, facts: List[SemanticFact], session_id: str) -> None:
        """Store facts silently without confirmation"""
        for fact in facts:
            await self._store_fact_with_deduplication(fact, session_id)

    async def _extract_forget_target(self, message: str) -> str:
        """Extract what to forget from message"""
        message_lower = message.lower()
        
        prefixes = ["forget that", "forget about", "don't remember", "remove"]
        for prefix in prefixes:
            if message_lower.startswith(prefix):
                return message[len(prefix):].strip()
        
        return message

    def _remove_matching_facts(self, forget_target: str) -> List[str]:
        """Remove facts matching the forget target"""
        removed_facts = []
        target_lower = forget_target.lower()
        
        for category_name, category_facts in self.memory.items():
            if category_name in ["metadata", "fact_relationships"]:
                continue
                
            facts_to_remove = []
            for fact_id, fact_data in category_facts.items():
                if isinstance(fact_data, dict) and "content" in fact_data:
                    if target_lower in fact_data["content"].lower():
                        facts_to_remove.append(fact_id)
                        removed_facts.append(fact_data["content"])
            
            # Remove identified facts
            for fact_id in facts_to_remove:
                del category_facts[fact_id]
        
        if removed_facts:
            self._save_memory()
            
        return removed_facts

    def get_memory_context_for_ai(self, session_id: str) -> str:
        """Get relevant memory context for AI responses"""
        try:
            context_parts = []
            
            # Add key user information
            for category_name, category_facts in self.memory.items():
                if category_name in ["metadata", "fact_relationships"] or not category_facts:
                    continue
                    
                category_context = []
                for fact_data in category_facts.values():
                    if isinstance(fact_data, dict) and "content" in fact_data:
                        category_context.append(fact_data["content"])
                
                if category_context:
                    context_parts.append(f"{category_name.replace('_', ' ').title()}: {'; '.join(category_context[:3])}")  # Limit per category
            
            if context_parts:
                return "Personal Context: " + " | ".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"❌ Error getting memory context for AI: {e}")
            return ""

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        try:
            total_facts = 0
            category_counts = {}
            
            for category_name, category_facts in self.memory.items():
                if category_name not in ["metadata", "fact_relationships"]:
                    count = len(category_facts)
                    category_counts[category_name] = count
                    total_facts += count
            
            return {
                "total_facts": total_facts,
                "category_counts": category_counts,
                "metadata": self.memory.get("metadata", {}),
                "memory_file_exists": self.memory_file.exists()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting memory stats: {e}")
            return {"error": str(e)}


# Global instance
semantic_letta_memory: Optional[SemanticLettaMemory] = None

def get_semantic_letta_memory() -> SemanticLettaMemory:
    """Get or create the global semantic Letta memory instance"""
    global semantic_letta_memory
    if semantic_letta_memory is None:
        semantic_letta_memory = SemanticLettaMemory()
    return semantic_letta_memory

def initialize_semantic_letta_memory() -> SemanticLettaMemory:
    """Initialize semantic Letta memory system"""
    try:
        memory = get_semantic_letta_memory()
        logger.info("✅ Semantic Letta memory system initialized")
        return memory
    except Exception as e:
        logger.error(f"❌ Failed to initialize semantic Letta memory: {e}")
        raise