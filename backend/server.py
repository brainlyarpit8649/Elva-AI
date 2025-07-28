from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import json

# Import our enhanced hybrid AI system
from advanced_hybrid_ai import detect_intent, generate_friendly_draft, handle_general_chat, advanced_hybrid_ai
from webhook_handler import send_approved_action, send_to_n8n
from playwright_service import playwright_service, AutomationResult
from direct_automation_handler import direct_automation_handler
from gmail_oauth_service import GmailOAuthService
from conversation_memory import initialize_conversation_memory

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize Gmail OAuth service with database connection
gmail_oauth_service = GmailOAuthService(db=db)

# Initialize conversation memory system
conversation_memory = initialize_conversation_memory(db)

# In-memory store for pending post prompt packages
pending_post_packages = {}

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str = "default_user"
    message: str
    response: str
    intent_data: Optional[dict] = None
    approved: Optional[bool] = None
    n8n_response: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

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

class ApprovalRequest(BaseModel):
    session_id: str
    message_id: str
    approved: bool
    edited_data: Optional[dict] = None

class WebAutomationRequest(BaseModel):
    session_id: str
    automation_type: str  # "web_scraping", "linkedin_insights", "email_automation", "data_extraction"
    parameters: dict

# Helper functions
def convert_objectid_to_str(doc):
    """Convert MongoDB ObjectId to string for JSON serialization"""
    if isinstance(doc, dict):
        new_doc = {}
        for key, value in doc.items():
            if key == '_id':
                # Skip MongoDB's _id field
                continue
            elif hasattr(value, 'binary') or str(type(value)) == "<class 'bson.objectid.ObjectId'>":
                # This is likely an ObjectId
                new_doc[key] = str(value)
            elif isinstance(value, dict):
                new_doc[key] = convert_objectid_to_str(value)
            elif isinstance(value, list):
                new_doc[key] = [convert_objectid_to_str(item) if isinstance(item, dict) else str(item) if hasattr(item, 'binary') else item for item in value]
            else:
                new_doc[key] = value
        return new_doc
    elif hasattr(doc, 'binary') or str(type(doc)) == "<class 'bson.objectid.ObjectId'>":
        return str(doc)
    else:
        return doc

# Routes
@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"🚀 Advanced Hybrid AI Chat: {request.message}")
        
        # Check if this is a send confirmation for a pending post prompt package
        user_msg_lower = request.message.lower().strip()
        send_commands = ["send", "yes, go ahead", "submit", "send it", "yes go ahead", "go ahead"]
        is_send_command = any(cmd in user_msg_lower for cmd in send_commands)
        
        if is_send_command and request.session_id in pending_post_packages:
            # User wants to send the pending post prompt package to n8n
            pending_data = pending_post_packages[request.session_id]
            
            # Send to N8N webhook
            try:
                webhook_result = await send_to_n8n({
                    "intent": "generate_post_prompt_package",
                    "session_id": request.session_id,
                    "post_description": pending_data.get("post_description", ""),
                    "ai_instructions": pending_data.get("ai_instructions", ""),
                    "topic": pending_data.get("topic", ""),
                    "project_name": pending_data.get("project_name", ""),
                    "project_type": pending_data.get("project_type", ""),
                    "tech_stack": pending_data.get("tech_stack", "")
                })
                
                # Clear the pending data
                del pending_post_packages[request.session_id]
                
                # Create success response
                response_text = "✅ **Post Prompt Package Sent Successfully!**\n\nYour LinkedIn post preparation package has been sent to the automation system. You can now use the Post Description and AI Instructions to generate your LinkedIn post with any AI tool of your choice."
                
                # Save to database
                chat_msg = ChatMessage(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    message=request.message,
                    response=response_text,
                    intent_data={"intent": "post_package_sent", "webhook_result": webhook_result}
                )
                await db.chat_messages.insert_one(chat_msg.dict())
                
                return ChatResponse(
                    id=chat_msg.id,
                    message=request.message,
                    response=response_text,
                    intent_data={"intent": "post_package_sent"},
                    needs_approval=False,
                    timestamp=chat_msg.timestamp
                )
                
            except Exception as e:
                logger.error(f"Error sending post package to webhook: {e}")
                response_text = "❌ **Error sending post package.** Please try again or contact support if the issue persists."
                
                chat_msg = ChatMessage(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    message=request.message,
                    response=response_text,
                    intent_data={"intent": "post_package_error", "error": str(e)}
                )
                await db.chat_messages.insert_one(chat_msg.dict())
                
                return ChatResponse(
                    id=chat_msg.id,
                    message=request.message,
                    response=response_text,
                    intent_data={"intent": "post_package_error"},
                    needs_approval=False,
                    timestamp=chat_msg.timestamp
                )
        
        elif is_send_command and request.session_id not in pending_post_packages:
            # User said send but no pending post package
            response_text = "🤔 I don't see any pending LinkedIn post prompt package to send. Please first ask me to help you prepare a LinkedIn post about your project or topic."
            
            chat_msg = ChatMessage(
                session_id=request.session_id,
                user_id=request.user_id,
                message=request.message,
                response=response_text,
                intent_data={"intent": "no_pending_package"}
            )
            await db.chat_messages.insert_one(chat_msg.dict())
            
            return ChatResponse(
                id=chat_msg.id,
                message=request.message,
                response=response_text,
                intent_data={"intent": "no_pending_package"},
                needs_approval=False,
                timestamp=chat_msg.timestamp
            )
        
        # Use advanced hybrid processing with sophisticated routing
        intent_data, response_text, routing_decision = await advanced_hybrid_ai.process_message(
            request.message, 
            request.session_id
        )
        
        logger.info(f"🧠 Advanced Routing: {routing_decision.primary_model.value} (confidence: {routing_decision.confidence:.2f})")
        logger.info(f"💡 Routing Logic: {routing_decision.reasoning}")
        
        # Check if this is a direct automation intent
        intent = intent_data.get("intent", "general_chat")
        is_direct_automation = advanced_hybrid_ai.is_direct_automation_intent(intent)
        
        if is_direct_automation:
            # Handle direct automation - bypass AI response generation and approval modal
            logger.info(f"🔄 Direct automation detected: {intent}")
            
            # Process the automation directly
            automation_result = await direct_automation_handler.process_direct_automation(intent_data, request.session_id)
            
            # Set response text to the automation result
            response_text = automation_result["message"]
            
            # Update intent data with automation results
            intent_data.update({
                "automation_result": automation_result["data"],
                "automation_success": automation_result["success"],
                "execution_time": automation_result["execution_time"],
                "direct_automation": True
            })
            
            # No approval needed for direct automation
            needs_approval = False
            
            logger.info(f"✅ Direct automation completed: {intent} - Success: {automation_result['success']}")
            
        else:
            # Traditional flow for non-direct automation intents
            web_automation_intents = ["web_scraping", "linkedin_insights", "email_automation", "data_extraction"]
            # generate_post_prompt_package doesn't need approval - it just shows blocks for user review
            needs_approval = intent_data.get("intent") not in ["general_chat", "generate_post_prompt_package"]
            
            # For web automation intents, check if we have required credentials
            if intent_data.get("intent") in web_automation_intents:
                # Check if this is a web scraping request that can be executed directly
                if intent_data.get("intent") == "web_scraping" and intent_data.get("url"):
                    # Execute web scraping directly if we have URL and selectors
                    try:
                        automation_result = await playwright_service.extract_dynamic_data(
                            intent_data.get("url"),
                            intent_data.get("selectors", {}),
                            intent_data.get("wait_for_element")
                        )
                        
                        # Update response with automation results
                        if automation_result.success:
                            response_text += f"\n\n🔍 **Web Scraping Results:**\n{json.dumps(automation_result.data, indent=2)}"
                            intent_data["automation_result"] = automation_result.data
                            intent_data["automation_success"] = True
                            needs_approval = False  # No approval needed for successful scraping
                        else:
                            response_text += f"\n\n⚠️ **Scraping Error:** {automation_result.message}"
                            intent_data["automation_error"] = automation_result.message
                            
                    except Exception as e:
                        logger.error(f"Direct web scraping error: {e}")
                        response_text += f"\n\n❌ **Automation Error:** {str(e)}"
        
        # Handle generate_post_prompt_package intent - store pending data
        if intent_data.get("intent") == "generate_post_prompt_package":
            # Store the post description and AI instructions for later confirmation
            pending_post_packages[request.session_id] = {
                "post_description": intent_data.get("post_description", ""),
                "ai_instructions": intent_data.get("ai_instructions", ""),
                "topic": intent_data.get("topic", ""),
                "project_name": intent_data.get("project_name", ""),
                "project_type": intent_data.get("project_type", ""),
                "tech_stack": intent_data.get("tech_stack", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add confirmation instruction to the response
            response_text += "\n\n💬 **Ready to send?** Just say **'send'**, **'yes, go ahead'**, or **'submit'** to send this package to your automation workflow!"
            
            logger.info(f"📝 Stored pending post package for session {request.session_id}")
        
        # Save to database
        chat_msg = ChatMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            message=request.message,
            response=response_text,
            intent_data=intent_data
        )
        await db.chat_messages.insert_one(chat_msg.dict())
        
        return ChatResponse(
            id=chat_msg.id,
            message=request.message,
            response=response_text,
            intent_data=intent_data,
            needs_approval=needs_approval,
            timestamp=chat_msg.timestamp
        )
        
    except Exception as e:
        logger.error(f"💥 Advanced Hybrid Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        return {
            "success": True,
            "message": "Action executed successfully!" if n8n_response.get("success") else "Action sent but n8n had issues",
            "n8n_response": n8n_response
        }
        
    except HTTPException:
        # Re-raise HTTPException to preserve status code
        raise
    except Exception as e:
        logger.error(f"Approval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        logger.info(f"Getting chat history for session: {session_id}")
        
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(1000)
        
        # Convert ObjectIds to strings for JSON serialization
        serializable_messages = [convert_objectid_to_str(msg) for msg in messages]
        
        return {"messages": serializable_messages}
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    try:
        logger.info(f"Clearing chat history for session: {session_id}")
        
        result = await db.chat_messages.delete_many({"session_id": session_id})
        return {
            "success": True, 
            "message": f"Cleared {result.deleted_count} messages from chat history"
        }
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/routing-stats/{session_id}")
async def get_routing_stats(session_id: str):
    try:
        stats = advanced_hybrid_ai.get_routing_stats(session_id)
        return {
            "session_id": session_id,
            "routing_statistics": stats,
            "advanced_features": {
                "task_classification": "multi-dimensional analysis",
                "routing_logic": "context-aware with fallback",
                "conversation_history": "last 10 messages tracked",
                "supported_routing": ["sequential", "claude_primary", "groq_primary", "context_enhanced"]
            }
        }
    except Exception as e:
        logger.error(f"Routing stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/automation-status/{intent}")
async def get_automation_status(intent: str):
    """Get automation status message for a specific intent"""
    try:
        status_message = advanced_hybrid_ai.get_automation_status_message(intent)
        is_direct = advanced_hybrid_ai.is_direct_automation_intent(intent)
        
        return {
            "intent": intent,
            "status_message": status_message,
            "is_direct_automation": is_direct,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Automation status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/web-automation")
async def execute_web_automation(request: WebAutomationRequest):
    """
    Execute web automation tasks using Playwright
    """
    try:
        logger.info(f"🌐 Web Automation Request: {request.automation_type}")
        
        result = None
        
        if request.automation_type == "web_scraping" or request.automation_type == "data_extraction":
            # Extract dynamic data from websites
            url = request.parameters.get("url")
            selectors = request.parameters.get("selectors", {})
            wait_for_element = request.parameters.get("wait_for_element")
            
            if not url or not selectors:
                raise HTTPException(status_code=400, detail="URL and selectors are required for web scraping")
            
            result = await playwright_service.extract_dynamic_data(url, selectors, wait_for_element)
            
        elif request.automation_type == "linkedin_insights":
            # LinkedIn insights will be handled via Gmail API integration in the future
            raise HTTPException(status_code=501, detail="LinkedIn insights temporarily disabled - Gmail API integration coming soon")
            
        elif request.automation_type == "email_automation":
            # Email automation will be handled via Gmail API
            raise HTTPException(status_code=501, detail="Email automation temporarily disabled - Gmail API integration coming soon")
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported automation type: {request.automation_type}")
        
        # Save automation result to database
        automation_record = {
            "id": str(uuid.uuid4()),
            "session_id": request.session_id,
            "automation_type": request.automation_type,
            "parameters": request.parameters,
            "result": result.data if result else {},
            "success": result.success if result else False,
            "message": result.message if result else "Unknown error",
            "execution_time": result.execution_time if result else 0,
            "timestamp": datetime.utcnow()
        }
        
        await db.automation_logs.insert_one(automation_record)
        
        return {
            "success": result.success if result else False,
            "data": result.data if result else {},
            "message": result.message if result else "Automation failed",
            "execution_time": result.execution_time if result else 0,
            "automation_id": automation_record["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web automation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/automation-history/{session_id}")
async def get_automation_history(session_id: str):
    """Get automation history for a session"""
    try:
        logger.info(f"Getting automation history for session: {session_id}")
        
        automation_logs = await db.automation_logs.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).to_list(50)  # Get latest 50 records
        
        # Convert ObjectIds to strings for JSON serialization
        serializable_logs = [convert_objectid_to_str(log) for log in automation_logs]
        
        return {"automation_history": serializable_logs}
    except Exception as e:
        logger.error(f"Automation history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/stats")
async def get_memory_system_stats():
    """Get comprehensive memory system statistics and health information"""
    try:
        system_stats = await conversation_memory.get_memory_stats()
        
        return {
            "success": True,
            "message": "Memory system statistics retrieved successfully",
            "stats": system_stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Memory system stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/stats/{session_id}")
async def get_session_memory_stats(session_id: str):
    """Get memory statistics for a specific session"""
    try:
        session_stats = await conversation_memory.get_memory_stats(session_id)
        
        return {
            "success": True,
            "message": f"Memory statistics retrieved for session: {session_id}",
            "stats": session_stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Session memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversation-memory/{session_id}")
async def get_conversation_memory_info(session_id: str):
    """Get conversation memory information and statistics for a session"""
    try:
        memory_stats = await conversation_memory.get_memory_stats(session_id)
        conversation_context = await conversation_memory.get_conversation_context(session_id)
        session_summary = await conversation_memory.get_session_summary(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "memory_stats": memory_stats,
            "conversation_context": conversation_context,
            "session_summary": session_summary,
            "context_length": len(conversation_context),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Conversation memory info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/conversation-memory/{session_id}")
async def clear_conversation_memory(session_id: str):
    """Clear conversation memory for a specific session"""
    try:
        await conversation_memory.clear_session_memory(session_id)
        return {
            "success": True,
            "message": f"Conversation memory cleared for session {session_id}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Clear conversation memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/conversation-memory/cleanup")
async def cleanup_old_conversation_memories():
    """Cleanup old conversation memories to prevent memory leaks"""
    try:
        await conversation_memory.cleanup_old_memories()
        return {
            "success": True,
            "message": "Old conversation memories cleaned up successfully",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Memory cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# OAuth2 endpoints for Gmail API
@api_router.get("/gmail/auth")
async def gmail_auth_init(session_id: str = None):
    """Initialize Gmail OAuth2 authentication flow with session support"""
    try:
        if not session_id:
            session_id = 'default_session'
            
        result = gmail_oauth_service.get_auth_url()
        
        if result.get('success') and result.get('auth_url'):
            # Add session ID to the state parameter
            auth_url = result['auth_url']
            if 'state=' in auth_url:
                auth_url = auth_url.replace('state=', f'state={session_id}_')
            result['auth_url'] = auth_url
            
        return result
    except Exception as e:
        logger.error(f"Gmail auth init error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/callback")
async def gmail_auth_callback(code: str = None, state: str = None, error: str = None, session_id: str = None):
    """Handle Gmail OAuth2 callback from Google redirect"""
    try:
        logger.info(f"🔗 Gmail OAuth callback received - code: {bool(code)}, state: {state}, error: {error}")
        
        # Extract session_id from state if not provided separately
        if not session_id and state:
            try:
                # State can contain session information
                if '_' in state:
                    session_id = state.split('_')[0]
                    logger.info(f"📋 Extracted session_id from state: {session_id}")
                else:
                    session_id = 'default_session'
            except:
                session_id = 'default_session'
        
        if not session_id:
            session_id = 'default_session'
            
        logger.info(f"🎯 Using session_id: {session_id}")
            
        # Handle OAuth error responses
        if error:
            logger.warning(f"❌ OAuth callback received error: {error}")
            # Redirect to frontend with error parameter
            return RedirectResponse(
                url=f'https://aac17c76-bf24-4440-9340-97ce1bd35c08.preview.emergentagent.com/?auth=error&message={error}&session_id={session_id}',
                status_code=302
            )
        
        # Check for authorization code
        if not code:
            logger.error("❌ No authorization code received in OAuth callback")
            return RedirectResponse(
                url=f'https://aac17c76-bf24-4440-9340-97ce1bd35c08.preview.emergentagent.com/?auth=error&message=no_code&session_id={session_id}',
                status_code=302
            )
        
        logger.info(f"✅ Processing OAuth callback with authorization code for session: {session_id}")
        
        # Handle OAuth callback with authorization code
        result = await gmail_oauth_service.handle_oauth_callback(code, session_id)
        
        logger.info(f"📊 OAuth callback result: success={result.get('success')}, authenticated={result.get('authenticated')}")
        
        if result.get("authenticated", False):
            logger.info(f"🎉 Gmail authentication successful for session {session_id} - redirecting to frontend")
            # Redirect to frontend with success parameter
            return RedirectResponse(
                url=f'https://aac17c76-bf24-4440-9340-97ce1bd35c08.preview.emergentagent.com/?auth=success&service=gmail&session_id={session_id}',
                status_code=302
            )
        else:
            error_msg = result.get('message', 'Authentication failed')
            logger.error(f"❌ Gmail authentication failed for session {session_id}: {error_msg}")
            return RedirectResponse(
                url=f'https://aac17c76-bf24-4440-9340-97ce1bd35c08.preview.emergentagent.com/?auth=error&message=auth_failed&details={error_msg}&session_id={session_id}',
                status_code=302
            )
        
    except Exception as e:
        logger.error(f"💥 Gmail auth callback exception: {e}")
        # Redirect to frontend with error parameter
        return RedirectResponse(
            url=f'https://aac17c76-bf24-4440-9340-97ce1bd35c08.preview.emergentagent.com/?auth=error&message=server_error&details={str(e)}&session_id={session_id if session_id else "unknown"}',
            status_code=302
        )

@api_router.get("/gmail/debug")
async def gmail_debug_info():
    """Get detailed Gmail integration debug information"""
    try:
        # Get Gmail OAuth status for debugging
        gmail_status = await gmail_oauth_service.get_auth_status('debug_session')
        
        # Check for credentials file
        credentials_file_exists = gmail_oauth_service.credentials_file_path.exists()
        credentials_content = None
        
        if credentials_file_exists:
            try:
                with open(gmail_oauth_service.credentials_file_path, 'r') as f:
                    credentials_data = json.load(f)
                    # Don't expose actual credentials, just structure
                    credentials_content = {
                        "has_web_config": "web" in credentials_data,
                        "has_installed_config": "installed" in credentials_data,
                        "client_id_configured": bool(credentials_data.get('web', {}).get('client_id') or credentials_data.get('installed', {}).get('client_id')),
                        "redirect_uri_configured": bool(credentials_data.get('web', {}).get('redirect_uris') or credentials_data.get('installed', {}).get('redirect_uris'))
                    }
            except Exception as e:
                credentials_content = {"error": f"Failed to parse credentials.json: {str(e)}"}
        
        # Check database connection
        db_status = "unknown"
        token_count = 0
        try:
            await db.command("ping")
            db_status = "connected"
            token_count = await db.oauth_tokens.count_documents({"service": "gmail"})
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        debug_info = {
            "gmail_service_status": {
                "credentials_file_exists": credentials_file_exists,
                "credentials_file_path": str(gmail_oauth_service.credentials_file_path),
                "credentials_content": credentials_content,
                "redirect_uri_env": os.getenv('GMAIL_REDIRECT_URI'),
                "scopes": gmail_oauth_service.scopes
            },
            "database_status": {
                "connection": db_status,
                "gmail_token_count": token_count
            },
            "gmail_auth_status": gmail_status,
            "environment": {
                "GMAIL_REDIRECT_URI": os.getenv('GMAIL_REDIRECT_URI'),
                "has_claude_key": bool(os.getenv('CLAUDE_API_KEY')),
                "has_groq_key": bool(os.getenv('GROQ_API_KEY'))
            }
        }
        
        return {
            "success": True,
            "debug_info": debug_info,
            "message": "Gmail integration debug information retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Gmail debug error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve Gmail debug information"
        }

@api_router.get("/gmail/status")
async def gmail_auth_status(session_id: str = None):
    """Get Gmail authentication status for specific session"""
    try:
        status = await gmail_oauth_service.get_auth_status(session_id)
        return status
    except Exception as e:
        logger.error(f"Gmail status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/inbox")
async def gmail_check_inbox(session_id: str = None, max_results: int = 10, query: str = 'is:unread'):
    """Check Gmail inbox using OAuth2 for specific session"""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
            
        result = await gmail_oauth_service.check_inbox(session_id, max_results=max_results, query=query)
        return result
    except Exception as e:
        logger.error(f"Gmail inbox check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/gmail/send")
async def gmail_send_email(request: dict):
    """Send email using Gmail API with OAuth2"""
    try:
        to = request.get('to')
        subject = request.get('subject')
        body = request.get('body')
        
        if not all([to, subject, body]):
            raise HTTPException(status_code=400, detail="to, subject, and body are required")
        
        result = gmail_oauth_service.send_email(
            to=to,
            subject=subject,
            body=body,
            sender_email=request.get('from'),
            cc=request.get('cc'),
            bcc=request.get('bcc')
        )
        return result
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/email/{message_id}")
async def gmail_get_email(message_id: str):
    """Get specific email content using Gmail API"""
    try:
        result = gmail_oauth_service.get_email_content(message_id)
        return result
    except Exception as e:
        logger.error(f"Gmail get email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def root():
    return {"message": "Elva AI Backend is running! 🤖✨", "version": "1.0"}

@api_router.get("/")
async def root():
    return {"message": "Elva AI Backend with Advanced Hybrid Routing! 🤖✨🧠", "version": "2.0"}

# Health check endpoint - Enhanced for advanced hybrid system
@api_router.get("/health")
async def health_check():
    try:
        # Test MongoDB connection
        await db.command("ping")
        
        # Get Gmail OAuth status (default session for health check)
        gmail_status = await gmail_oauth_service.get_auth_status('health_check')
        
        health_status = {
            "status": "healthy",
            "mongodb": "connected",
            "gmail_api_integration": {
                "status": "ready",
                "oauth2_flow": "implemented", 
                "credentials_configured": gmail_status.get('credentials_configured', False),
                "authenticated": gmail_status.get('authenticated', False),
                "scopes": gmail_oauth_service.scopes,
                "endpoints": [
                    "/api/gmail/auth",
                    "/api/gmail/callback", 
                    "/api/gmail/status",
                    "/api/gmail/inbox",
                    "/api/gmail/send",
                    "/api/gmail/email/{id}"
                ]
            },
            "advanced_hybrid_ai_system": {
                "version": "2.0",
                "groq_api_key": "configured" if os.getenv("GROQ_API_KEY") else "missing",
                "claude_api_key": "configured" if os.getenv("CLAUDE_API_KEY") else "missing",
                "groq_model": "llama3-8b-8192",
                "claude_model": "claude-3-5-sonnet-20241022",
                "sophisticated_features": {
                    "task_classification": [
                        "primary_intent", "emotional_complexity", "professional_tone", 
                        "creative_requirement", "technical_complexity", "response_length",
                        "user_engagement_level", "context_dependency", "reasoning_type"
                    ],
                    "routing_strategies": [
                        "intent_based", "emotional_routing", "professional_routing",
                        "creative_routing", "sequential_execution", "context_enhancement"
                    ],
                    "advanced_capabilities": [
                        "conversation_history_tracking", "context_aware_responses",
                        "fallback_mechanisms", "confidence_scoring", "routing_explanation"
                    ]
                },
                "routing_models": {
                    "claude_tasks": ["high_emotional", "creative_content", "conversational", "professional_warm"],
                    "groq_tasks": ["logical_reasoning", "structured_analysis", "technical_complex", "intent_detection"],
                    "sequential_tasks": ["professional_emails", "linkedin_posts", "complex_creative"],
                    "web_automation_tasks": ["web_scraping", "data_extraction"]
                }
            },
            "n8n_webhook": "configured" if os.getenv("N8N_WEBHOOK_URL") else "missing",
            "playwright_service": {
                "status": "available",
                "browser": "chromium",
                "capabilities": [
                    "dynamic_data_extraction", "web_scraping"
                ]
            },
            "conversation_memory_system": {
                "status": "available",
                "langchain_integration": "enabled", 
                "memory_types": [
                    "ConversationBufferMemory",
                    "ConversationSummaryBufferMemory"
                ],
                "features": [
                    "context_retention",
                    "conversation_summarization", 
                    "intent_context_storage",
                    "memory_cleanup",
                    "mongodb_integration",
                    "redis_caching",
                    "native_mongodb_history",
                    "enhanced_fallback_messaging",
                    "memory_stats_api",
                    "early_api_key_validation"
                ],
                "max_token_limit": conversation_memory.max_token_limit,
                "buffer_window_size": conversation_memory.buffer_window_size,
                "memory_cleanup_interval_hours": conversation_memory.memory_cleanup_hours,
                "redis_integration": {
                    "enabled": conversation_memory.redis is not None,
                    "url": conversation_memory.redis_url if conversation_memory.redis is not None else "not_configured",
                    "ttl_seconds": conversation_memory.redis_ttl
                },
                "api_keys": {
                    "groq_configured": bool(os.getenv("GROQ_API_KEY")),
                    "claude_configured": bool(os.getenv("CLAUDE_API_KEY"))
                }
            }
        }
        
        return health_status
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    # Close Playwright service
    await playwright_service.close()