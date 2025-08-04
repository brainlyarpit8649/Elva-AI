import os
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, HTTPException, Request, Query, Header
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

# Import Semantic Letta Memory System (New Enhanced Version)
from semantic_letta_memory import initialize_semantic_letta_memory, get_semantic_letta_memory
from performance_optimizer import initialize_performance_optimizer, get_performance_optimizer

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize Gmail OAuth service with database connection
gmail_oauth_service = GmailOAuthService(db=db)

# Initialize enhanced Gmail service (legacy)
enhanced_gmail_service = EnhancedGmailService(gmail_oauth_service)

# Initialize new real-time Gmail service with DeBERTa
realtime_gmail_service = RealTimeGmailService(gmail_oauth_service)

# Initialize conversation memory system
conversation_memory = initialize_conversation_memory(db)

# Initialize MCP (Model Context Protocol) integration service
mcp_service = initialize_mcp_service()

# Initialize Semantic Letta Memory System
try:
    semantic_memory = initialize_semantic_letta_memory()
    logging.info("✅ Semantic Letta Memory System initialized successfully")
except Exception as e:
    logging.warning(f"⚠️ Semantic Letta Memory initialization failed: {e}")
    semantic_memory = None

# Initialize Performance Optimizer
try:
    performance_optimizer = None  # Will be initialized on first use
    logging.info("✅ Performance Optimizer marked for lazy initialization")
except Exception as e:
    logging.warning(f"⚠️ Performance Optimizer setup failed: {e}")
    performance_optimizer = None

# Create indexes for message memory (will be done on first request)
startup_tasks = {
    "indexes_created": False,
    "performance_optimizer_initialized": False
}

# Global variables for tracking
pending_post_packages = {}

# Create FastAPI app
app = FastAPI(title="Elva AI Backend", description="Enhanced AI Assistant Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup API router
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: str = "anonymous"

class ChatResponse(BaseModel):
    id: str
    message: str
    response: str
    intent_data: Optional[Dict[str, Any]] = None
    needs_approval: bool = False
    timestamp: datetime
    session_id: str
    user_id: str

class ApprovalRequest(BaseModel):
    message_id: str
    approved: bool
    edited_data: Optional[Dict[str, Any]] = None

class SuperAGITaskRequest(BaseModel):
    goal: str
    agent_type: str
    session_id: str

class MCPContextRequest(BaseModel):
    session_id: str
    user_id: str = "anonymous"
    intent: str
    data: Dict[str, Any]

class DebugToggleRequest(BaseModel):
    session_id: str
    
# Helper functions
def convert_objectid_to_str(document):
    """Convert MongoDB ObjectId to string for JSON serialization"""
    if isinstance(document, list):
        return [convert_objectid_to_str(doc) for doc in document]
    if isinstance(document, dict):
        for key, value in document.items():
            if hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                document[key] = str(value)
            elif isinstance(value, (dict, list)):
                document[key] = convert_objectid_to_str(value)
    return document

def get_session_welcome_message(session_id: str) -> str:
    """Generate session welcome message"""
    return f"👋 Hello! I'm Elva AI, your intelligent assistant. I can help with emails, scheduling, research, and much more! How can I help you today?"

# Main chat endpoint
@api_router.post("/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest):
    try:
        logger.info(f"💬 Enhanced chat request - Session: {request.session_id}, Message: {request.message[:100]}...")

        # STEP 0: Save user message to database first (with proper EnhancedChatMessage structure)
        user_msg = UserMessage(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message
        )
        await db.chat_messages.insert_one(user_msg.dict())
        logger.info(f"💾 Saved user message: {user_msg.id}")

        # STEP 1: Process the message through the main processing pipeline
        response_text, intent_data, needs_approval = await process_regular_chat(request)
        
        # STEP 2: Create response message with proper structure
        ai_msg = AIMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            response=response_text,
            intent_data=intent_data,
            is_system=intent_data.get('intent') in ['gmail_auth_required', 'error', 'no_pending_package']
        )
        await db.chat_messages.insert_one(ai_msg.dict())
        logger.info(f"💾 Saved AI response to both memory systems: {ai_msg.id}")
        
        # STEP 3: Enhanced Conversation Context Storage for both systems
        try:
            # Store in conversation memory system
            await conversation_memory.store_conversation_turn(
                session_id=request.session_id,
                user_message=request.message,
                ai_response=response_text,
                intent_data=intent_data or {},
                additional_context={
                    "needs_approval": needs_approval,
                    "user_id": request.user_id,
                    "message_id": ai_msg.id
                }
            )
            
            # Store in MCP service
            try:
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
                logger.info(f"✅ Context stored in both conversation memory and MCP: {request.session_id}")
            except Exception as mcp_error:
                logger.warning(f"⚠️ MCP context storage failed: {mcp_error}")
            
        except Exception as memory_error:
            logger.warning(f"⚠️ Enhanced conversation context storage failed: {memory_error}")

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

    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_regular_chat(request: ChatRequest):
    try:
        logger.info(f"🤖 Processing regular chat for session: {request.session_id}")

        # Performance optimization check
        if performance_optimizer:
            is_cached, cached_result = await performance_optimizer.optimize_chat_processing({
                "message": request.message,
                "session_id": request.session_id
            })
            if is_cached and cached_result:
                return cached_result["response"], cached_result["intent_data"], cached_result.get("needs_approval", False)

        # Import message memory functions
        from message_memory import get_conversation_context_for_ai, search_conversation_memory
        
        # STEP 1: Semantic Letta memory processing with new system
        if semantic_memory:
            memory_result = await semantic_memory.process_message_for_memory(request.message, request.session_id)
            
            if memory_result.get("is_memory_operation"):
                response_text = memory_result.get("response", "Got it 👍")
                intent_data = {"intent": "memory_operation", "operation_type": "semantic_memory"}
                needs_approval = False
                
                # Cache successful memory operations for performance
                if performance_optimizer and memory_result.get("facts_extracted"):
                    performance_optimizer.cache_response(request.message, {
                        "response": response_text,
                        "intent_data": intent_data,
                        "needs_approval": needs_approval
                    })
                
                return response_text, intent_data, needs_approval
        
        # STEP 2: Get FULL conversation context (MongoDB + message_memory + Semantic Memory)
        previous_context = ""
        try:
            # Get complete conversation history for context
            previous_context = await get_conversation_context_for_ai(request.session_id)
            logger.info(f"📖 Retrieved full conversation context for session: {request.session_id}")
            
            # Add MCP context for additional context
            context_result = await mcp_service.read_context(request.session_id)
            if context_result.get("success") and context_result.get("context"):
                mcp_context = await mcp_service.get_context_for_prompt(request.session_id)
                if mcp_context:
                    previous_context += f"\n\n=== ADDITIONAL CONTEXT ===\n{mcp_context}"
                logger.info(f"📖 Added MCP context for session: {request.session_id}")
            
            # Add Semantic Memory context for better responses
            if semantic_memory:
                memory_context = semantic_memory.get_memory_context_for_ai(request.session_id)
                if memory_context:
                    previous_context += f"\n\n=== PERSONALIZED MEMORY ===\n{memory_context}"
                    logger.info(f"🧠 Added Semantic Memory context for session: {request.session_id}")
                
        except Exception as context_error:
            logger.warning(f"⚠️ Error reading conversation context: {context_error}")
            previous_context = ""

        # STEP 3: Handle Post Prompt Package confirmation check
        if request.session_id in pending_post_packages:
            if any(confirmation in request.message.lower() for confirmation in ["send", "yes", "go ahead", "submit", "confirm", "ok"]):
                logger.info(f"📤 Confirmed post package send for session {request.session_id}")
                
                package_data = pending_post_packages[request.session_id]
                intent_data = {
                    "intent": "generate_post_prompt_package_confirmed",
                    **package_data
                }
                
                # Remove from pending
                del pending_post_packages[request.session_id]
                
                response_text = "✅ **Package sent to your automation workflow!** I've forwarded your post description and AI instructions for processing."
                needs_approval = True  # This will trigger the automation workflow
                return response_text, intent_data, needs_approval

        # STEP 4: Run through advanced hybrid AI system
        result = await advanced_hybrid_ai(
            message=request.message,
            session_id=request.session_id,
            conversation_context=previous_context,
            user_id=request.user_id
        )

        response_text = result.get("response", "I understand.")
        intent_data = result.get("intent_data", {})
        needs_approval = result.get("needs_approval", False)

        # STEP 5: Store important information in semantic memory automatically
        if semantic_memory and not memory_result.get("is_memory_operation", False):
            # Check if the conversation contains important personal information to auto-store
            user_message_lower = request.message.lower()
            
            # Patterns that suggest personal information that should be stored
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
                    try:
                        # Auto-store facts silently (no confirmation message)
                        auto_memory_result = await semantic_memory.process_message_for_memory(request.message, request.session_id)
                        if auto_memory_result.get("facts_extracted"):
                            logger.info(f"🧠 Auto-stored {fact_type} facts from conversation: {len(auto_memory_result['facts_extracted'])} facts")
                    except Exception as auto_store_error:
                        logger.warning(f"⚠️ Auto-store failed: {auto_store_error}")
                    break

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
        
    except Exception as e:
        logger.error(f"❌ Regular chat processing error: {e}")
        response_text = "Sorry, I encountered an error processing your request. Please try again! 🤖"
        intent_data = {"intent": "error", "error": str(e)}
        needs_approval = False
        return response_text, intent_data, needs_approval

@api_router.post("/approve")
async def approve_action(request: ApprovalRequest):
    try:
        logger.info(f"Received approval request: {request}")
        
        # Get the message from database
        message = await db.chat_messages.find_one({"id": request.message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        if not request.approved:
            # Update message in database with rejection
            await db.chat_messages.update_one(
                {"id": request.message_id},
                {"$set": {"approved": False}}
            )
            return {"success": True, "message": "Action cancelled"}
        
        # Use edited data if provided, otherwise use original intent data
        final_data = request.edited_data if request.edited_data else message["intent_data"]
        logger.info(f"Sending to n8n with data: {final_data}")
        
        # Send to n8n using our webhook handler
        n8n_response = await send_approved_action(
            final_data, 
            message["user_id"], 
            message["session_id"]
        )
        
        # Update message in database with approval status and n8n response
        await db.chat_messages.update_one(
            {"id": request.message_id},
            {"$set": {
                "approved": request.approved, 
                "n8n_response": n8n_response,
                "edited_data": request.edited_data
            }}
        )
        
        # Append results to MCP context when action is approved
        try:
            append_result = await mcp_service.append_context(
                session_id=request.session_id,
                output={
                    "action": "approved_action_result",
                    "intent": final_data.get("intent"),
                    "n8n_response": n8n_response,
                    "edited_data": request.edited_data,
                    "execution_status": "success" if n8n_response.get("success") else "partial",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"📝 Appended approval result to MCP context: {append_result}")
        except Exception as mcp_error:
            logger.warning(f"⚠️ Error appending to MCP context: {mcp_error}")
        
        return {"success": True, "message": "Action approved and sent to n8n", "n8n_response": n8n_response}
        
    except Exception as e:
        logger.error(f"Approval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        messages = []
        cursor = db.chat_messages.find({"session_id": session_id}).sort([("timestamp", 1)])
        async for message in cursor:
            messages.append(convert_objectid_to_str(message))
        return {"history": messages}
    except Exception as e:
        logger.error(f"Chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    try:
        result = await db.chat_messages.delete_many({"session_id": session_id})
        return {"success": True, "deleted_count": result.deleted_count}
    except Exception as e:
        logger.error(f"Clear chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/superagi/run-task")
async def run_superagi_task(request: SuperAGITaskRequest):
    """Execute task with SuperAGI autonomous agents"""
    try:
        logger.info(f"🚀 SuperAGI Task Request: {request.goal} (Agent: {request.agent_type})")
        
        # Execute with SuperAGI client
        result = await superagi_client.run_task(
            goal=request.goal,
            agent_type=request.agent_type,
            session_id=request.session_id
        )
        
        # Store result in MCP context for conversation awareness
        try:
            await mcp_service.append_context(
                session_id=request.session_id,
                output={
                    "superagi_task": request.goal,
                    "agent_type": request.agent_type,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as mcp_error:
            logger.warning(f"⚠️ Error storing SuperAGI result in MCP: {mcp_error}")
        
        return {
            "success": result.get("success", False),
            "result": result,
            "session_id": request.session_id,
            "agent_type": request.agent_type
        }
        
    except Exception as e:
        logger.error(f"❌ SuperAGI task execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mcp/write-context")
async def write_mcp_context(request: MCPContextRequest):
    """Write context data to MCP service"""
    try:
        result = await mcp_service.write_context(
            session_id=request.session_id,
            user_id=request.user_id,
            intent=request.intent,
            data=request.data
        )
        return result
    except Exception as e:
        logger.error(f"❌ MCP context write error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/mcp/read-context/{session_id}")
async def read_mcp_context(session_id: str):
    """Read context data from MCP service"""
    try:
        result = await mcp_service.read_context(session_id)
        return result
    except Exception as e:
        logger.error(f"❌ MCP context read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mcp/append-context")
async def append_mcp_context(request: dict):
    """Append agent results to existing context in MCP service"""
    try:
        session_id = request.get("session_id")
        output = request.get("output", {})
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        result = await mcp_service.append_context(
            session_id=session_id,
            output=output
        )
        return result
    except Exception as e:
        logger.error(f"❌ MCP context append error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/web-automation")
async def execute_web_automation(request: MCPContextRequest):
    """Execute web automation tasks using Playwright"""
    try:
        automation_type = request.data.get('automation_type', 'web_scraping')
        url = request.data.get('url', '')
        
        if not url:
            raise HTTPException(status_code=400, detail="URL is required for web automation")
        
        logger.info(f"🤖 Executing web automation: {automation_type} on {url}")
        
        # Execute automation with Playwright service
        result = await playwright_service.execute_automation(
            automation_type=automation_type,
            url=url,
            session_id=request.session_id,
            **request.data
        )
        
        # Store automation result in database for history
        automation_record = {
            "id": str(uuid.uuid4()),
            "session_id": request.session_id,
            "automation_type": automation_type,
            "url": url,
            "parameters": request.data,
            "result": result.data if hasattr(result, 'data') else result,
            "success": result.success if hasattr(result, 'success') else True,
            "message": result.message if hasattr(result, 'message') else "Automation completed",
            "execution_time": result.execution_time if hasattr(result, 'execution_time') else 0,
            "timestamp": datetime.utcnow()
        }
        
        await db.web_automation_history.insert_one(automation_record)
        logger.info(f"📝 Stored automation record: {automation_record['id']}")
        
        # Also store in MCP context for conversation awareness
        try:
            await mcp_service.append_context(
                session_id=request.session_id,
                output={
                    "web_automation_result": automation_record,
                    "automation_type": automation_type,
                    "url": url,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as mcp_error:
            logger.warning(f"⚠️ Error storing automation result in MCP: {mcp_error}")
        
        return {
            "success": automation_record["success"],
            "automation_id": automation_record["id"],
            "message": automation_record["message"],
            "result": automation_record["result"],
            "execution_time": automation_record["execution_time"]
        }
        
    except Exception as e:
        logger.error(f"❌ Web automation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/automation-history/{session_id}")
async def get_automation_history(session_id: str):
    """Get web automation history for a session"""
    try:
        history = []
        cursor = db.web_automation_history.find({"session_id": session_id}).sort([("timestamp", -1)]).limit(10)
        async for record in cursor:
            history.append(convert_objectid_to_str(record))
        
        return {"history": history, "count": len(history)}
        
    except Exception as e:
        logger.error(f"Automation history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/automation-status/{automation_id}")
async def get_automation_status(automation_id: str):
    """Get status of a specific automation task"""
    try:
        record = await db.web_automation_history.find_one({"id": automation_id})
        if not record:
            raise HTTPException(status_code=404, detail="Automation record not found")
        
        return convert_objectid_to_str(record)
        
    except Exception as e:
        logger.error(f"Automation status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Gmail OAuth endpoints
@api_router.get("/gmail/auth")
async def gmail_auth():
    """Initiate Gmail OAuth2 authentication"""
    try:
        auth_result = gmail_oauth_service.get_auth_url()
        if not auth_result.get('success'):
            logger.error(f"Gmail auth failed: {auth_result.get('message')}")
            raise HTTPException(status_code=500, detail=auth_result.get('message'))
        
        auth_url = auth_result.get('auth_url')
        logger.info(f"✅ Gmail auth URL generated: {auth_url}")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Gmail auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/callback")
async def gmail_callback(code: str = None, error: str = None):
    """Handle Gmail OAuth2 callback"""
    try:
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        
        # Exchange code for tokens
        await gmail_oauth_service.exchange_code_for_tokens(code)
        
        # Redirect to frontend with success message
        frontend_url = os.getenv("REACT_APP_FRONTEND_URL", "https://329904b0-2cf4-48ba-8d24-e322e324860a.preview.emergentagent.com")
        return RedirectResponse(url=f"{frontend_url}?gmail_auth=success")
        
    except Exception as e:
        logger.error(f"Gmail callback error: {e}")
        frontend_url = os.getenv("REACT_APP_FRONTEND_URL", "https://329904b0-2cf4-48ba-8d24-e322e324860a.preview.emergentagent.com")
        return RedirectResponse(url=f"{frontend_url}?gmail_auth=error&message={str(e)}")

@api_router.get("/gmail/status")
async def gmail_status():
    """Get Gmail authentication status"""
    try:
        status = await gmail_oauth_service.get_auth_status()
        return status
    except Exception as e:
        logger.error(f"Gmail status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/inbox")
async def gmail_inbox():
    """Get Gmail inbox messages"""
    try:
        messages = await gmail_oauth_service.get_inbox_messages()
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Gmail inbox error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/gmail/send")
async def gmail_send_email(request: dict):
    """Send email using Gmail API with OAuth2"""
    try:
        result = await gmail_oauth_service.send_email(
            to=request.get("to"),
            subject=request.get("subject"),
            body=request.get("body")
        )
        return result
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/email/{email_id}")
async def gmail_get_email(email_id: str):
    """Get specific email by ID"""
    try:
        email = await gmail_oauth_service.get_email_by_id(email_id)
        return email
    except Exception as e:
        logger.error(f"Gmail get email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Message Memory Management endpoints
@api_router.get("/message-memory/stats/{session_id}")
async def get_message_memory_stats(session_id: str):
    """Get comprehensive message memory statistics for a session"""
    try:
        from message_memory import get_memory_stats, get_conversation_history
        stats = await get_memory_stats(session_id)
        
        # Also get recent conversation preview
        recent_messages = await get_conversation_history(session_id, limit=5)
        stats["recent_messages_preview"] = recent_messages
        
        return stats
    except Exception as e:
        logger.error(f"Message memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/message-memory/full-context/{session_id}")
async def get_full_conversation_context(session_id: str):
    """Get full conversation context for debugging conversation memory"""
    try:
        from message_memory import get_conversation_context_for_ai, get_conversation_history
        
        full_context = await get_conversation_context_for_ai(session_id)
        all_messages = await get_conversation_history(session_id)
        
        return {
            "session_id": session_id,
            "total_messages": len(all_messages),
            "full_context": full_context,
            "all_messages": all_messages
        }
    except Exception as e:
        logger.error(f"Full context retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/message-memory/search/{session_id}")
async def search_message_memory(session_id: str, request: dict):
    """Search through message memory for specific content"""
    try:
        from message_memory import search_conversation_memory
        
        search_query = request.get("query", "")
        if not search_query:
            raise HTTPException(status_code=400, detail="Search query is required")
        
        results = await search_conversation_memory(session_id, search_query)
        
        return {
            "session_id": session_id,
            "search_query": search_query,
            "results_found": len(results),
            "matching_messages": results
        }
    except Exception as e:
        logger.error(f"Message memory search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Memory management endpoints
@api_router.post("/conversation-memory/cleanup")
async def cleanup_old_conversation_memories():
    """Cleanup old conversation memories to prevent memory leaks"""
    try:
        cleanup_result = await conversation_memory.cleanup_old_memories()
        return {
            "success": True,
            "message": "Old conversation memories cleaned up successfully",
            "cleanup_details": cleanup_result
        }
    except Exception as e:
        logger.error(f"Conversation memory cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversation-memory/stats/{session_id}")
async def get_conversation_memory_stats(session_id: str):
    """Get conversation memory statistics for a session"""
    try:
        stats = await conversation_memory.get_memory_stats(session_id)
        return stats
    except Exception as e:
        logger.error(f"Conversation memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/conversation-memory/{session_id}")
async def clear_conversation_memory(session_id: str):
    """Clear conversation memory for a specific session"""
    try:
        result = await conversation_memory.clear_memory(session_id)
        return {
            "success": True,
            "message": f"Conversation memory cleared for session {session_id}",
            "details": result
        }
    except Exception as e:
        logger.error(f"Clear conversation memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WhatsApp MCP Integration Endpoint
@api_router.post("/mcp")
async def whatsapp_mcp_handler(
    raw_request: Request,
    token: str = Query(None),
    authorization: str = Header(None)
):
    """
    WhatsApp MCP Integration Handler
    Processes WhatsApp messages through existing Elva AI chat pipeline
    
    Supports token authentication via:
    - Query parameter: ?token=<TOKEN>
    - Authorization header: Bearer <TOKEN>
    
    Expected payload: {"session_id": "...", "message": "..."}
    """
    try:
        # Extract JSON body from raw request
        try:
            request = await raw_request.json()
        except Exception:
            request = {}
        
        # Extract and validate authentication token
        auth_token = None
        
        # Check query parameter first
        if hasattr(raw_request, 'query_params') and 'token' in raw_request.query_params:
            auth_token = raw_request.query_params.get('token')
        elif token:
            auth_token = token
        
        # Check Authorization header
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]  # Remove 'Bearer ' prefix
            else:
                auth_token = authorization
        
        # Validate token
        expected_token = os.getenv("MCP_API_TOKEN", "kumararpit9468")
        if not auth_token or auth_token != expected_token:
            logger.warning(f"🚫 WhatsApp MCP - Invalid token: {auth_token}")
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "invalid_token",
                    "message": "Invalid or missing MCP API token",
                    "expected_format": "Bearer <token> in header or ?token=<token> in query"
                }
            )
        
        # Handle empty or test connection requests
        if not request or request == {}:
            logger.info("🔄 WhatsApp MCP - Connection test request")
            return {
                "status": "ok",
                "message": "MCP connection successful",
                "service": "WhatsApp MCP Integration",
                "platform": "whatsapp",
                "endpoints": ["POST /api/mcp", "GET /api/mcp/health"],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Flexible payload validation - accept different formats
        if not isinstance(request, dict):
            # Try to handle string payloads (some clients send plain text)
            if isinstance(request, str):
                request = {
                    "session_id": "connection_test",
                    "message": request,
                    "user_id": "test_user"
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_payload",
                        "message": "Request must be JSON object or string",
                        "expected_formats": [
                            '{"session_id": "...", "message": "..."}',
                            '{"session_id": "...", "text": "..."}',
                            '{"session_id": "...", "query": "..."}'
                        ]
                    }
                )
        
        # Validate request payload
        if not isinstance(request, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_payload",
                    "message": "Request must be a JSON object",
                    "expected_format": '{"session_id": "...", "message": "..."}'
                }
            )
        
        # Extract message with flexible field names (like mcp_service.py)
        session_id = request.get('session_id')
        message = (
            request.get('message') or 
            request.get('text') or 
            request.get('query') or 
            request.get('content') or
            ""
        )
        user_id = request.get('user_id', 'whatsapp_user')
        
        # Handle connection test cases - more flexible for Puch AI
        if not session_id and not message:
            logger.info("🔄 WhatsApp MCP - Empty payload connection test")
            return {
                "status": "ok", 
                "message": "MCP connection successful - ready for messages",
                "service": "WhatsApp MCP Integration",
                "platform": "whatsapp",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Set defaults for missing fields (more lenient)
        if not session_id:
            session_id = f"test_session_{int(datetime.utcnow().timestamp())}"
        
        if not message:
            message = "Hello! Connection test successful."
        
        # Handle simple connection test messages (expanded list)
        test_messages = ["test", "hello", "ping", "connection test", "", "hi", "check"]
        if message.lower() in test_messages:
            logger.info(f"🔄 WhatsApp MCP - Simple connection test: {message}")
            return {
                "status": "ok",
                "message": "MCP connection successful! WhatsApp integration is ready.",
                "session_id": session_id,
                "platform": "whatsapp",
                "integrations": ["gmail", "weather", "general_chat"],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        logger.info(f"📱 WhatsApp MCP Message - Session: {session_id}, Message: {message[:100]}...")
        
        # Create ChatRequest object for existing pipeline
        chat_request = ChatRequest(
            message=message,
            session_id=f"whatsapp_{session_id}",  # Prefix to distinguish WhatsApp sessions
            user_id=user_id
        )
        
        # Process through existing enhanced chat pipeline
        chat_response = await enhanced_chat(chat_request)
        
        # Log WhatsApp conversation in MongoDB
        whatsapp_log = {
            "id": str(uuid.uuid4()),
            "platform": "whatsapp",
            "session_id": session_id,
            "whatsapp_session_id": f"whatsapp_{session_id}",
            "user_id": user_id,
            "user_message": message,
            "ai_response": chat_response.response,
            "intent_data": chat_response.intent_data,
            "needs_approval": chat_response.needs_approval,
            "timestamp": datetime.utcnow(),
            "processing_time": None
        }
        
        # Store WhatsApp conversation log
        await db.whatsapp_conversations.insert_one(whatsapp_log)
        logger.info(f"📝 Logged WhatsApp conversation: {whatsapp_log['id']}")
        
        # Write to MCP context for session memory
        try:
            mcp_context_data = mcp_service.prepare_context_data(
                user_message=message,
                ai_response=chat_response.response,
                intent_data=chat_response.intent_data or {},
                routing_info={
                    "platform": "whatsapp",
                    "session_id": session_id,
                    "user_id": user_id
                }
            )
            
            await mcp_service.write_context(
                session_id=f"whatsapp_{session_id}",
                user_id=user_id,
                intent=chat_response.intent_data.get("intent", "general_chat") if chat_response.intent_data else "general_chat",
                data=mcp_context_data
            )
            
            logger.info(f"💾 WhatsApp context written to MCP: whatsapp_{session_id}")
        except Exception as mcp_error:
            logger.warning(f"⚠️ MCP context write failed for WhatsApp: {mcp_error}")
        
        # Format response for WhatsApp/Puch AI
        whatsapp_response = {
            "success": True,
            "session_id": session_id,
            "message": chat_response.response,
            "intent": chat_response.intent_data.get("intent", "general_chat") if chat_response.intent_data else "general_chat",
            "needs_approval": chat_response.needs_approval,
            "platform": "whatsapp",
            "timestamp": chat_response.timestamp.isoformat(),
            "conversation_id": whatsapp_log['id']
        }
        
        # Add special handling for Gmail and Weather intents
        if chat_response.intent_data and chat_response.intent_data.get("intent") in ["check_gmail_inbox", "gmail_summary", "get_weather_forecast"]:
            whatsapp_response["intent_data"] = {
                "type": chat_response.intent_data.get("intent"),
                "confidence": chat_response.intent_data.get("confidence", 0.8),
                "data": chat_response.intent_data
            }
        
        # Add approval workflow info if needed
        if chat_response.needs_approval:
            whatsapp_response["approval_info"] = {
                "required": True,
                "intent": chat_response.intent_data.get("intent"),
                "message_id": chat_response.id,
                "approval_endpoint": "/api/approve"
            }
        
        logger.info(f"✅ WhatsApp MCP Response - Session: {session_id}, Intent: {whatsapp_response['intent']}")
        return whatsapp_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 WhatsApp MCP Handler Error: {e}")
        
        # Log error for debugging
        error_log = {
            "id": str(uuid.uuid4()),
            "platform": "whatsapp",
            "session_id": request.get('session_id', 'unknown') if isinstance(request, dict) else 'unknown',
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow()
        }
        
        try:
            await db.whatsapp_errors.insert_one(error_log)
        except:
            pass  # Don't fail if error logging fails
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "processing_failed",
                "message": "Failed to process WhatsApp message",
                "details": str(e),
                "session_id": request.get('session_id') if isinstance(request, dict) else None
            }
        )

@api_router.get("/mcp")
async def whatsapp_mcp_connection_test(
    token: str = None,
    authorization: str = Header(None)
):
    """
    WhatsApp MCP Connection Test (GET)
    Handles GET requests from Puch AI for connection verification
    """
    try:
        # Extract and validate authentication token
        auth_token = token
        
        # Check Authorization header
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]
            else:
                auth_token = authorization
        
        # Validate token
        expected_token = os.getenv("MCP_API_TOKEN", "kumararpit9468")
        if not auth_token or auth_token != expected_token:
            logger.warning(f"🚫 WhatsApp MCP GET - Invalid token attempt")
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "invalid_token",
                    "message": "Invalid or missing MCP API token"
                }
            )
        
        logger.info("🔄 WhatsApp MCP - GET connection test successful")
        
        return {
            "status": "ok",
            "message": "MCP connection successful - WhatsApp integration ready",
            "service": "WhatsApp MCP Integration",
            "platform": "whatsapp",
            "methods": ["GET", "POST"],
            "integrations": {
                "gmail": "ready",
                "weather": "ready",
                "general_chat": "ready"
            },
            "supported_formats": [
                '{"session_id": "...", "message": "..."}',
                '{"session_id": "...", "text": "..."}',
                '{"session_id": "...", "query": "..."}'
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ WhatsApp MCP GET Error: {e}")
        return {
            "status": "error",
            "message": "Connection test failed",
            "error": str(e)
        }

@api_router.get("/mcp/health")
async def whatsapp_mcp_health():
    """WhatsApp MCP Health Check Endpoint"""
    try:
        # Check MCP service health
        mcp_health = await mcp_service.health_check()
        
        # Check database connections
        await client.admin.command('ping')
        
        return {
            "status": "healthy",
            "service": "WhatsApp MCP Integration",
            "version": "1.0.0",
            "platform": "whatsapp",
            "mcp_service": mcp_health.get("success", False),
            "database": "connected",
            "integrations": {
                "gmail": "ready",
                "weather": "ready", 
                "hybrid_ai": "ready"
            },
            "endpoints": [
                "POST /api/mcp",
                "GET /api/mcp/health",
                "GET /api/mcp/sessions",
                "POST /api/mcp/approve"
            ],
            "authentication": {
                "methods": ["query_parameter", "authorization_header"],
                "token_configured": bool(os.getenv("MCP_API_TOKEN")),
                "example_usage": [
                    "POST /api/mcp?token=<TOKEN>",
                    "POST /api/mcp (with Authorization: Bearer <TOKEN>)"
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ WhatsApp MCP Health Check Error: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@api_router.get("/mcp/sessions")
async def get_whatsapp_sessions(
    token: str = None,
    authorization: str = Header(None),
    limit: int = 20
):
    """Get WhatsApp conversation sessions"""
    try:
        # Validate token (same logic as main endpoint)
        auth_token = token
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]
            else:
                auth_token = authorization
        
        expected_token = os.getenv("MCP_API_TOKEN", "kumararpit9468")
        if not auth_token or auth_token != expected_token:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get recent WhatsApp sessions
        sessions = []
        cursor = db.whatsapp_conversations.find().sort([("timestamp", -1)]).limit(limit)
        async for session in cursor:
            sessions.append(convert_objectid_to_str(session))
        
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions),
            "platform": "whatsapp"
        }
        
    except Exception as e:
        logger.error(f"❌ WhatsApp sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mcp/approve")
async def whatsapp_approve_action(
    request: dict,
    token: str = None,
    authorization: str = Header(None)
):
    """Handle approval actions from WhatsApp"""
    try:
        # Validate token
        auth_token = token
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]
            else:
                auth_token = authorization
        
        expected_token = os.getenv("MCP_API_TOKEN", "kumararpit9468")
        if not auth_token or auth_token != expected_token:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Extract approval data
        session_id = request.get('session_id')
        message_id = request.get('message_id')
        approved = request.get('approved', False)
        edited_data = request.get('edited_data')
        
        if not session_id or not message_id:
            raise HTTPException(
                status_code=400,
                detail="session_id and message_id are required"
            )
        
        # Convert to internal session format
        internal_session_id = f"whatsapp_{session_id}"
        
        # Call internal approval endpoint
        approval_request = ApprovalRequest(
            message_id=message_id,
            approved=approved,
            edited_data=edited_data
        )
        
        result = await approve_action(approval_request)
        
        # Store WhatsApp approval log
        approval_log = {
            "id": str(uuid.uuid4()),
            "platform": "whatsapp",
            "session_id": session_id,
            "message_id": message_id,
            "approved": approved,
            "edited_data": edited_data,
            "result": result,
            "timestamp": datetime.utcnow()
        }
        
        await db.whatsapp_approvals.insert_one(approval_log)
        logger.info(f"📝 Logged WhatsApp approval: {approval_log['id']}")
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Action processed"),
            "session_id": session_id,
            "platform": "whatsapp",
            "approval_id": approval_log['id']
        }
        
    except Exception as e:
        logger.error(f"❌ WhatsApp approval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New Semantic Memory endpoints (replacing old Letta endpoints)
@api_router.get("/memory/stats")
async def get_semantic_memory_stats():
    """Get semantic memory system statistics"""
    try:
        if semantic_memory:
            stats = semantic_memory.get_memory_stats()
            return stats
        else:
            return {"success": False, "error": "Semantic memory not initialized"}
    except Exception as e:
        logger.error(f"❌ Error getting semantic memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/memory/process")
async def process_memory_message(request: dict):
    """Process a message through semantic memory"""
    try:
        message = request.get("message", "")
        session_id = request.get("session_id", "")
        
        if not message or not session_id:
            raise HTTPException(status_code=400, detail="Message and session_id are required")
        
        if semantic_memory:
            result = await semantic_memory.process_message_for_memory(message, session_id)
            return result
        else:
            return {"success": False, "error": "Semantic memory not initialized"}
    except Exception as e:
        logger.error(f"❌ Error processing memory message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/context/{session_id}")
async def get_memory_context(session_id: str):
    """Get memory context for a session"""
    try:
        if semantic_memory:
            context = semantic_memory.get_memory_context_for_ai(session_id)
            return {"session_id": session_id, "context": context}
        else:
            return {"success": False, "error": "Semantic memory not initialized"}
    except Exception as e:
        logger.error(f"❌ Error getting memory context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@api_router.get("/health")
async def health_check():
    try:
        # Check database connection
        await client.admin.command('ping')
        
        # Check service health
        gmail_status = await gmail_oauth_service.get_auth_status()
        mcp_health = await mcp_service.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": "connected",
                "gmail_api_integration": {
                    "status": "ready",
                    "oauth2_flow": "implemented",
                    "credentials_configured": gmail_status.get("credentials_configured", False),
                    "scopes": gmail_status.get("scopes", []),
                    "endpoints": [
                        "/api/gmail/auth",
                        "/api/gmail/callback", 
                        "/api/gmail/status",
                        "/api/gmail/inbox",
                        "/api/gmail/send",
                        "/api/gmail/email/{id}"
                    ]
                },
                "groq_api": {
                    "configured": bool(os.getenv("GROQ_API_KEY")),
                    "model": "llama3-8b-8192"
                },
                "claude_api": {
                    "configured": bool(os.getenv("ANTHROPIC_API_KEY")), 
                    "model": "claude-3-5-sonnet-20241022"
                },
                "n8n_webhook": {
                    "configured": bool(os.getenv("N8N_WEBHOOK_URL"))
                },
                "mcp_service": {
                    "status": "connected" if mcp_health.get("success") else "disconnected"
                },
                "semantic_memory": {
                    "status": "initialized" if semantic_memory else "not_initialized"
                },
                "performance_optimizer": {
                    "status": "initialized" if performance_optimizer else "not_initialized"
                }
            },
            "version": "2.0.0-semantic-memory"
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail=str(e))

# Add the API router to the main app
app.include_router(api_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Elva AI Backend is running with Semantic Memory!", "version": "2.0.0-semantic-memory"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)