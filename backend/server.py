import os
import logging
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, HTTPException, Request, Query, Header, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
import json
import httpx

# Import our enhanced hybrid AI system
from advanced_hybrid_ai import detect_intent, generate_friendly_draft, handle_general_chat, advanced_hybrid_ai
from webhook_handler import send_approved_action, send_to_n8n
from playwright_service import playwright_service, AutomationResult
from direct_automation_handler import direct_automation_handler
from gmail_oauth_service import GmailOAuthService
from conversation_memory import initialize_conversation_memory
from message_memory import ensure_indexes
from superagi_client import superagi_client
from mcp_integration import get_mcp_service, initialize_mcp_service

# Import enhanced Gmail components
from enhanced_gmail_intent_detector import enhanced_gmail_detector
from enhanced_gmail_service import EnhancedGmailService
from enhanced_chat_models import EnhancedChatMessage, UserMessage, AIMessage

# Import new DeBERTa-based Gmail system
from realtime_gmail_service import RealTimeGmailService
from deberta_gmail_intent_detector import deberta_gmail_detector

# Import weather service
from weather_service_tomorrow import (
    get_current_weather, 
    get_weather_forecast, 
    get_air_quality_index, 
    get_weather_alerts, 
    get_sun_times,
    get_cache_stats,
    clear_weather_cache
)

# Import simplified Letta Memory System 
from letta_memory import initialize_letta_memory, get_letta_memory

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Setup comprehensive logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection with optimized settings
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=20,  # Connection pooling
    minPoolSize=5,
    maxIdleTimeMS=30000,
    connectTimeoutMS=5000,
    serverSelectionTimeoutMS=5000
)
db = client[os.environ['DB_NAME']]

# Initialize services
gmail_oauth_service = GmailOAuthService(db=db)
enhanced_gmail_service = EnhancedGmailService(gmail_oauth_service)
realtime_gmail_service = RealTimeGmailService(gmail_oauth_service)
conversation_memory = initialize_conversation_memory(db)
mcp_service = initialize_mcp_service()

# Re-enable Letta Memory System with safe initialization
try:
    semantic_memory = initialize_letta_memory()
    logging.info("✅ Letta Memory System initialized successfully")
    MEMORY_ENABLED = True
except Exception as e:
    logging.warning(f"⚠️ Letta Memory initialization failed: {e}")
    semantic_memory = None
    MEMORY_ENABLED = False

# Global timeout configuration
GLOBAL_CHAT_TIMEOUT = 50.0  # 50 seconds max
MEMORY_OPERATION_TIMEOUT = 15.0  # 15 seconds for memory operations
DATABASE_OPERATION_TIMEOUT = 10.0  # 10 seconds for DB operations
AI_RESPONSE_TIMEOUT = 30.0  # 30 seconds for AI response generation

# Create indexes for message memory (will be done on first request)
startup_tasks = {
    "indexes_created": False
}

# Global variables for tracking
pending_post_packages = {}
degraded_mode_messages = [
    "Got it! Let's keep chatting while I catch up on memory…",
    "I'm with you! Processing your request now…",
    "On it! Give me just a moment…",
    "Got it! Working on your request…"
]

# FastAPI app setup
app = FastAPI(title="Elva AI Backend", version="2.0.0")
api_router = APIRouter(prefix="/api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    id: str
    message: str
    response: str
    intent_data: Optional[dict] = None
    needs_approval: bool = False
    timestamp: datetime
    session_id: str
    user_id: str

class ApprovalRequest(BaseModel):
    message_id: str
    approved: bool
    edited_data: Optional[dict] = None

# Utility functions
def convert_objectid_to_str(document):
    """Convert MongoDB ObjectId to string for JSON serialization"""
    if isinstance(document, list):
        return [convert_objectid_to_str(item) for item in document]
    elif isinstance(document, dict):
        for key, value in document.items():
            if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                document[key] = convert_objectid_to_str(value)
            elif hasattr(value, '__dict__'):
                document[key] = str(value)
            elif isinstance(value, (dict, list)):
                document[key] = convert_objectid_to_str(value)
    return document

def get_session_welcome_message(session_id: str) -> str:
    """Generate session welcome message"""
    return f"👋 Hello! I'm Elva AI, your intelligent assistant. I can help with emails, scheduling, research, and much more! How can I help you today?"

async def safe_memory_operation(operation_func, *args, timeout: float = MEMORY_OPERATION_TIMEOUT, **kwargs) -> Optional[Any]:
    """
    Safely execute memory operations with timeout and error handling.
    Returns None if operation fails or times out.
    """
    try:
        return await asyncio.wait_for(operation_func(*args, **kwargs), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ Memory operation timed out after {timeout}s")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Memory operation failed: {e}")
        return None

async def safe_database_operation(operation_func, *args, timeout: float = DATABASE_OPERATION_TIMEOUT, **kwargs) -> Optional[Any]:
    """
    Safely execute database operations with timeout and error handling.
    Returns None if operation fails or times out.
    """
    try:
        return await asyncio.wait_for(operation_func(*args, **kwargs), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ Database operation timed out after {timeout}s")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Database operation failed: {e}")
        return None

def get_degraded_mode_message() -> str:
    """Get a random natural degraded mode message"""
    import random
    return random.choice(degraded_mode_messages)

# Main chat endpoint with comprehensive timeout protection
@api_router.post("/chat", response_model=ChatResponse)
async def enhanced_chat_with_timeout(request: ChatRequest):
    """
    Enhanced chat endpoint with comprehensive timeout protection and fallback system.
    
    Fallback order:
    1. Groq + Letta context (ideal)
    2. Groq only (if Letta fails/times out)
    3. Simple response (if Groq fails)
    """
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Wrap entire chat processing in global timeout
        return await asyncio.wait_for(
            _process_chat_with_fallbacks(request, start_time),
            timeout=GLOBAL_CHAT_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.error(f"🚨 Global chat timeout exceeded {GLOBAL_CHAT_TIMEOUT}s for session {request.session_id}")
        
        # Ultimate fallback - immediate response
        return await _create_emergency_response(request, "I'm here to help! What would you like to know?")
    except Exception as e:
        logger.error(f"🚨 Critical chat error: {e}")
        
        # Emergency fallback
        return await _create_emergency_response(request, "I'm ready to assist you! How can I help?")

async def _process_chat_with_fallbacks(request: ChatRequest, start_time: float):
    """Process chat with comprehensive fallback system"""
    
    # Lazy initialization of startup tasks
    global startup_tasks
    
    if not startup_tasks["indexes_created"]:
        # Safe database index creation
        index_result = await safe_database_operation(ensure_indexes)
        if index_result is not None:
            startup_tasks["indexes_created"] = True
            logger.info("✅ Message memory indexes created successfully")
        else:
            logger.warning("⚠️ Message memory index creation failed - continuing without indexes")

    logger.info(f"💬 Enhanced chat request - Session: {request.session_id}, Message: {request.message[:100]}...")

    # STEP 1: Save user message safely
    user_msg = UserMessage(
        user_id=request.user_id,
        session_id=request.session_id,
        message=request.message
    )
    
    # Safe user message save
    save_result = await safe_database_operation(db.chat_messages.insert_one, user_msg.dict())
    if save_result:
        logger.info(f"💾 Saved user message: {user_msg.id}")
    else:
        logger.warning("⚠️ Failed to save user message - continuing")

    # STEP 2: Process through fallback system
    response_text, intent_data, needs_approval = await _process_with_cascading_fallbacks(request)
    
    # STEP 3: Create and save AI response
    ai_msg = AIMessage(
        session_id=request.session_id,
        user_id=request.user_id,
        response=response_text,
        intent_data=intent_data,
        is_system=intent_data.get('intent') in ['gmail_auth_required', 'error', 'no_pending_package']
    )
    
    # Safe AI message save
    await safe_database_operation(db.chat_messages.insert_one, ai_msg.dict())
    
    # STEP 4: Safe conversation context storage
    await _safe_context_storage(request, response_text, intent_data, ai_msg)
    
    execution_time = asyncio.get_event_loop().time() - start_time
    logger.info(f"✅ Chat processed successfully in {execution_time:.2f}s")
    
    return ChatResponse(
        id=ai_msg.id,
        message=request.message,
        response=response_text,
        intent_data=intent_data,
        needs_approval=needs_approval,
        timestamp=ai_msg.timestamp,
        session_id=request.session_id,
        user_id=request.user_id
    )

async def _process_with_cascading_fallbacks(request: ChatRequest) -> tuple[str, dict, bool]:
    """
    Cascading fallback system:
    1. Quick memory check first (if memory command detected)
    2. Full processing with Letta memory + Groq
    3. Groq only (if memory fails)
    4. Simple response (if Groq fails)
    """
    
    # PRIORITY: Quick memory command check first (before any complex processing)
    if MEMORY_ENABLED and semantic_memory:
        message_lower = request.message.lower().strip()
        
        memory_triggers = [
            "remember that", "store this", "what do you remember", 
            "what's my", "what is my", "forget that", "my name is", "call me",
            "what do i", "who am i", "tell me about", "do you remember",
            "i like", "i love", "my favorite"
        ]
        
        is_memory_command = any(trigger in message_lower for trigger in memory_triggers)
        
        if is_memory_command:
            logger.info(f"🧠 Quick memory command detected: {request.message[:50]}...")
            
            try:
                memory_result = await semantic_memory.chat_with_memory(request.message, request.session_id)
                
                if memory_result and memory_result.get("success"):
                    response_text = memory_result.get("response", "Got it!")
                    intent_data = {"intent": "memory_operation", "operation_type": "letta_memory"}
                    logger.info(f"✅ Quick memory operation successful: {response_text[:50]}...")
                    return response_text, intent_data, False
                else:
                    logger.warning("⚠️ Quick memory operation had no success flag, continuing")
            except Exception as memory_error:
                logger.error(f"❌ Quick memory processing error: {memory_error}")
                # Continue with normal processing if memory fails
    
    # Try full processing with memory context
    try:
        return await _process_with_memory_context(request)
    except Exception as e:
        logger.warning(f"⚠️ Full processing failed, trying Groq-only: {e}")
        
        # Fallback to Groq only
        try:
            return await _process_groq_only(request)
        except Exception as e2:
            logger.warning(f"⚠️ Groq processing failed, using simple fallback: {e2}")
            
            # Ultimate fallback
            return await _process_simple_fallback(request)

async def _process_with_memory_context(request: ChatRequest) -> tuple[str, dict, bool]:
    """Process chat with Letta memory context - simplified approach"""
    
    # Import message memory functions safely
    try:
        from message_memory import get_conversation_context_for_ai, search_conversation_memory
    except ImportError as e:
        logger.warning(f"⚠️ Could not import message memory functions: {e}")
        return await _process_groq_only(request)
    
    # STEP 1: Handle Letta memory commands directly first (before any AI processing)
    if MEMORY_ENABLED and semantic_memory:
        message_lower = request.message.lower().strip()
        
        # Expand memory trigger patterns
        memory_triggers = [
            "remember that", "store this", "what do you remember", 
            "what's my", "what is my", "forget that", "my name is", "call me",
            "what do i", "who am i", "tell me about", "do you remember",
            "i like", "i love", "my favorite"
        ]
        
        is_memory_command = any(trigger in message_lower for trigger in memory_triggers)
        
        if is_memory_command:
            logger.info(f"🧠 Processing Letta memory command directly: {request.message[:50]}...")
            
            try:
                memory_result = await semantic_memory.chat_with_memory(request.message, request.session_id)
                
                if memory_result and memory_result.get("success"):
                    response_text = memory_result.get("response", "Got it!")
                    intent_data = {"intent": "memory_operation", "operation_type": "letta_memory"}
                    logger.info(f"✅ Letta memory operation completed: {response_text[:50]}...")
                    return response_text, intent_data, False
                else:
                    logger.warning("⚠️ Letta memory operation failed, continuing with normal processing")
            except Exception as memory_error:
                logger.error(f"❌ Memory processing error: {memory_error}")
                # Continue with normal processing
    
    # Initialize memory context for later use
    memory_context = ""
    
    # STEP 2: Get conversation context for AI responses
    previous_context = ""
    try:
        # Get full conversation history for context
        context_result = await safe_database_operation(
            get_conversation_context_for_ai, 
            request.session_id
        )
        if context_result:
            previous_context = context_result
            logger.info(f"📖 Retrieved conversation context ({len(previous_context)} chars)")
            
        # Add Letta Memory context for natural responses
        if MEMORY_ENABLED and semantic_memory:
            try:
                memory_summary = await safe_memory_operation(
                    semantic_memory.get_memory_summary
                )
                if memory_summary and memory_summary.get("success"):
                    memory_info = memory_summary.get("memory_info", {})
                    total_facts = memory_info.get("total_facts", 0)
                    if total_facts > 0:
                        # Get relevant facts for this message
                        context_result = await safe_memory_operation(
                            semantic_memory.retrieve_context,
                            request.message
                        )
                        if context_result and context_result.get("success"):
                            memory_context = context_result.get("context", "")
                            if memory_context:
                                previous_context += f"\n\n=== USER MEMORY ===\n{memory_context}"
                                logger.info(f"🧠 Added Letta memory context ({len(memory_context)} chars)")
            except Exception as memory_context_error:
                logger.warning(f"⚠️ Error retrieving memory context: {memory_context_error}")
        
        # Add MCP context
        mcp_context_result = await safe_memory_operation(
            mcp_service.read_context, 
            request.session_id
        )
        if mcp_context_result and mcp_context_result.get("success"):
            mcp_context = await safe_memory_operation(
                mcp_service.get_context_for_prompt, 
                request.session_id
            )
            if mcp_context:
                previous_context += f"\n\n=== MCP CONTEXT ===\n{mcp_context}"
                logger.info(f"📖 Added MCP context")
                
    except Exception as context_error:
        logger.warning(f"⚠️ Error reading conversation context: {context_error}")
        previous_context = ""

    # STEP 3: Handle Post Prompt Package confirmation
    if request.session_id in pending_post_packages:
        if any(confirmation in request.message.lower() for confirmation in ["send", "yes", "go ahead", "submit", "confirm", "ok"]):
            logger.info(f"📤 Confirmed post package send for session {request.session_id}")
            
            package_data = pending_post_packages[request.session_id]
            intent_data = {
                "intent": "generate_post_prompt_package_confirmed",
                **package_data
            }
            
            del pending_post_packages[request.session_id]
            
            response_text = "✅ **Package sent to your automation workflow!** I've forwarded your post description and AI instructions for processing."
            return response_text, intent_data, True

    # STEP 4: Process through advanced hybrid AI with context
    try:
        intent_data, response_text, routing_decision = await asyncio.wait_for(
            advanced_hybrid_ai.process_message(
                user_input=request.message,
                session_id=request.session_id,
                memory_context=previous_context  # Pass full context including Letta memory
            ),
            timeout=AI_RESPONSE_TIMEOUT
        )
        
        logger.info(f"🚀 AI processing completed: {intent_data.get('intent', 'unknown')} -> {len(response_text)} chars")
        
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ AI response generation timed out, using fallback")
        return await _process_groq_only(request)
    
    # Check if this is an action that needs approval
    needs_approval = intent_data.get("needs_approval", False)
    if intent_data.get("intent") in ["send_email", "create_event", "add_todo", "set_reminder"]:
        needs_approval = True

    # STEP 5: Auto-store important information in Letta memory
    if MEMORY_ENABLED and semantic_memory and intent_data.get("intent") != "memory_operation":
        await _auto_store_facts(request, semantic_memory)

    # STEP 6: Handle generate_post_prompt_package intent
    if intent_data.get("intent") == "generate_post_prompt_package":
        pending_post_packages[request.session_id] = {
            "post_description": intent_data.get("post_description", ""),
            "ai_instructions": intent_data.get("ai_instructions", ""),
            "topic": intent_data.get("topic", ""),
            "project_name": intent_data.get("project_name", ""),
            "project_type": intent_data.get("project_type", ""),
            "tech_stack": intent_data.get("tech_stack", ""),
            "timestamp": datetime.utcnow().isoformat()
        }
        response_text += "\n\n💬 **Ready to send?** Just say **'send'**, **'yes, go ahead'**, or **'submit'** to send this package to your automation workflow!"
        logger.info(f"📝 Stored pending post package for session {request.session_id}")
    
    return response_text, intent_data, needs_approval

async def _process_groq_only(request: ChatRequest) -> tuple[str, dict, bool]:
    """Fallback processing using only Groq (no memory context)"""
    
    logger.info(f"🤖 Processing with Groq-only fallback for session: {request.session_id}")
    
    # Add a subtle degraded mode message occasionally
    import random
    add_degraded_message = random.random() < 0.3  # 30% chance
    
    try:
        # Simple Groq processing
        intent_data, response_text, _ = await asyncio.wait_for(
            advanced_hybrid_ai.process_message(
                user_input=request.message,
                session_id=request.session_id,
                memory_context=""  # No memory context
            ),
            timeout=25.0
        )
        
        # Add degraded mode message naturally
        if add_degraded_message and intent_data.get("intent") == "general_chat":
            degraded_msg = get_degraded_mode_message()
            response_text = f"{degraded_msg}\n\n{response_text}"
        
        needs_approval = intent_data.get("needs_approval", False)
        if intent_data.get("intent") in ["send_email", "create_event", "add_todo", "set_reminder"]:
            needs_approval = True
            
        return response_text, intent_data, needs_approval
        
    except Exception as e:
        logger.warning(f"⚠️ Groq-only processing failed: {e}")
        return await _process_simple_fallback(request)

async def _process_simple_fallback(request: ChatRequest) -> tuple[str, dict, bool]:
    """Ultimate fallback - simple response without AI processing"""
    
    logger.info(f"🛡️ Using simple fallback for session: {request.session_id}")
    
    # Analyze message for simple patterns
    message_lower = request.message.lower().strip()
    
    # Simple greeting detection
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    if any(greeting in message_lower for greeting in greetings):
        response_text = "Hello! I'm Elva AI, your helpful assistant. How can I help you today? 😊"
    
    # Simple question detection
    elif "?" in request.message:
        response_text = "That's a great question! I'm here to help you find the answer. Let me know what specific information you're looking for! 🤔"
    
    # Simple task detection
    elif any(word in message_lower for word in ["help", "assist", "need", "want", "can you"]):
        response_text = "I'm here to help! I can assist with emails, scheduling, research, and much more. What would you like me to help you with? ✨"
    
    # Default response
    else:
        responses = [
            "I'm ready to help! What would you like to know? 🚀",
            "Thanks for reaching out! How can I assist you today? 💫",
            "I'm here and ready to help! What can I do for you? ⭐",
            "Great to hear from you! What would you like help with? 🌟"
        ]
        import random
        response_text = random.choice(responses)
    
    intent_data = {"intent": "general_chat", "fallback_mode": "simple"}
    return response_text, intent_data, False

async def _auto_store_facts(request: ChatRequest, semantic_memory):
    """Auto-store important facts from conversation"""
    
    try:
        user_message_lower = request.message.lower()
        
        # Patterns that suggest personal information
        info_patterns = {
            "identity": ["my name is", "i am", "call me", "i'm"],
            "preferences": ["i like", "i love", "i prefer", "i hate", "i dislike", "my favorite"],
            "contacts": ["my manager", "my boss", "my colleague", "my friend", "my family"],
            "work": ["i work", "my job", "my company", "my role", "my position"],
            "location": ["i live", "i'm from", "my address", "my location"],
            "skills": ["i can", "i know how to", "i'm good at", "i have experience"]
        }
        
        for fact_type, patterns in info_patterns.items():
            if any(pattern in user_message_lower for pattern in patterns):
                # Auto-store facts silently
                auto_memory_result = await safe_memory_operation(
                    semantic_memory.process_message_for_memory,
                    request.message,
                    request.session_id
                )
                if auto_memory_result and auto_memory_result.get("facts_extracted"):
                    logger.info(f"🧠 Auto-stored {fact_type} facts: {len(auto_memory_result['facts_extracted'])} facts")
                break
                
    except Exception as auto_store_error:
        logger.warning(f"⚠️ Auto-store failed: {auto_store_error}")

async def _safe_context_storage(request: ChatRequest, response_text: str, intent_data: dict, ai_msg):
    """Safely store conversation context in multiple systems"""
    
    # Store in conversation memory system
    conversation_store_result = await safe_memory_operation(
        conversation_memory.add_message_to_memory,
        session_id=request.session_id,
        user_message=request.message,
        ai_response=response_text,
        intent_data=intent_data or {}
    )
    
    # Store in MCP service
    mcp_store_result = await safe_memory_operation(
        _store_mcp_context,
        request,
        response_text,
        intent_data,
        ai_msg
    )
    
    if conversation_store_result or mcp_store_result:
        logger.info(f"✅ Context stored successfully: {request.session_id}")
    else:
        logger.warning(f"⚠️ Context storage failed for session: {request.session_id}")

async def _store_mcp_context(request: ChatRequest, response_text: str, intent_data: dict, ai_msg):
    """Store context in MCP service"""
    
    mcp_context_data = mcp_service.prepare_context_data(
        user_message=request.message,
        ai_response=response_text,
        intent_data=intent_data or {},
        routing_info={
            "hybrid_ai_routing": intent_data.get("routing_info") if intent_data else None,
            "session_id": request.session_id,
            "user_id": request.user_id
        }
    )
    
    await mcp_service.write_context(
        session_id=request.session_id,
        user_id=request.user_id,
        intent=intent_data.get("intent", "general_chat") if intent_data else "general_chat",
        data=mcp_context_data
    )

async def _create_emergency_response(request: ChatRequest, response_text: str) -> ChatResponse:
    """Create emergency response when everything fails"""
    
    emergency_msg = AIMessage(
        session_id=request.session_id,
        user_id=request.user_id,
        response=response_text,
        intent_data={"intent": "emergency_fallback"},
        is_system=False
    )
    
    # Try to save emergency message (but don't fail if it doesn't work)
    await safe_database_operation(db.chat_messages.insert_one, emergency_msg.dict())
    
    return ChatResponse(
        id=emergency_msg.id,
        message=request.message,
        response=response_text,
        intent_data={"intent": "emergency_fallback"},
        needs_approval=False,
        timestamp=emergency_msg.timestamp,
        session_id=request.session_id,
        user_id=request.user_id
    )

# Keep the rest of the endpoints unchanged for now...
# (approve, history, health, etc.)

@api_router.post("/approve")
async def approve_action(request: ApprovalRequest):
    try:
        logger.info(f"Received approval request: {request}")
        
        # Get the message from database with timeout protection
        message = await safe_database_operation(
            db.chat_messages.find_one,
            {"id": request.message_id}
        )
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        if not request.approved:
            # Update message in database with rejection
            await safe_database_operation(
                db.chat_messages.update_one,
                {"id": request.message_id},
                {"$set": {"approved": False}}
            )
            return {"success": True, "message": "Action cancelled"}
        
        # Use edited data if provided, otherwise use original intent data
        final_data = request.edited_data if request.edited_data else message["intent_data"]
        logger.info(f"Sending to n8n with data: {final_data}")
        
        # Send to n8n webhook with timeout protection
        n8n_response = await asyncio.wait_for(
            send_to_n8n(final_data),
            timeout=30.0
        )
        
        # Update message in database
        await safe_database_operation(
            db.chat_messages.update_one,
            {"id": request.message_id},
            {"$set": {"approved": True, "final_data": final_data}}
        )
        
        # Store approval in MCP context
        try:
            mcp_context_data = {
                "action": "approval",
                "message_id": request.message_id,
                "approved": True,
                "final_data": final_data,
                "n8n_response": n8n_response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await safe_memory_operation(
                mcp_service.append_context,
                session_id=message.get("session_id", "unknown"),
                intent="approval_action",
                data=mcp_context_data
            )
        except Exception as mcp_error:
            logger.warning(f"⚠️ Error appending to MCP context: {mcp_error}")
        
        return {"success": True, "message": "Action approved and sent to n8n", "n8n_response": n8n_response}
        
    except asyncio.TimeoutError:
        logger.error("⚠️ Approval request timed out")
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        logger.error(f"Approval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        messages = []
        cursor = db.chat_messages.find({"session_id": session_id}).sort([("timestamp", 1)])
        
        # Use safe database operation for history retrieval
        history_result = await safe_database_operation(cursor.to_list, 1000)
        
        if history_result:
            for message in history_result:
                messages.append(convert_objectid_to_str(message))
        
        return {"history": messages}
    except Exception as e:
        logger.error(f"Chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    try:
        result = await safe_database_operation(
            db.chat_messages.delete_many,
            {"session_id": session_id}
        )
        
        deleted_count = result.deleted_count if result else 0
        return {"success": True, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Clear chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/health")
async def health_check():
    try:
        # Test database connection with timeout
        db_status = "connected"
        try:
            await asyncio.wait_for(db.admin.command('ping'), timeout=5.0)
        except:
            db_status = "disconnected"
        
        # Test memory system
        memory_status = "enabled" if MEMORY_ENABLED and semantic_memory else "disabled"
        
        # Test MCP service
        mcp_status = "connected"
        try:
            await asyncio.wait_for(mcp_service.health_check(), timeout=5.0)
        except:
            mcp_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_status,
                "semantic_memory": memory_status,
                "mcp_service": mcp_status
            },
            "timeout_config": {
                "global_chat_timeout": GLOBAL_CHAT_TIMEOUT,
                "memory_operation_timeout": MEMORY_OPERATION_TIMEOUT,
                "database_operation_timeout": DATABASE_OPERATION_TIMEOUT,
                "ai_response_timeout": AI_RESPONSE_TIMEOUT
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add router to app
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)