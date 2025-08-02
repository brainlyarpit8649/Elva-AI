from fastapi import FastAPI, APIRouter, HTTPException, Header
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
import httpx

# Import our enhanced hybrid AI system
from advanced_hybrid_ai import detect_intent, generate_friendly_draft, handle_general_chat, advanced_hybrid_ai
from webhook_handler import send_approved_action, send_to_n8n
from playwright_service import playwright_service, AutomationResult
from direct_automation_handler import direct_automation_handler
from gmail_oauth_service import GmailOAuthService
from conversation_memory import initialize_conversation_memory
from superagi_client import superagi_client
from mcp_integration import get_mcp_service, initialize_mcp_service

# Import enhanced Gmail components
from enhanced_gmail_intent_detector import enhanced_gmail_detector
from enhanced_gmail_service import EnhancedGmailService
from enhanced_chat_models import EnhancedChatMessage, UserMessage, AIMessage

# Import new DeBERTa-based Gmail system
from deberta_gmail_intent_detector import deberta_gmail_detector
from realtime_gmail_service import RealTimeGmailService

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

class SuperAGITaskRequest(BaseModel):
    session_id: str
    goal: str
    agent_type: str = "auto"  # auto, email_agent, linkedin_agent, research_agent

class MCPContextRequest(BaseModel):
    session_id: str
    user_id: str = "default_user"
    intent: str
    data: dict

# Gmail Summarization Request Models
class GmailSummarizeRequest(BaseModel):
    intent: str  # "summarize_to_chat" or "summarize_and_send_email"
    limit: int = 4
    toEmail: Optional[str] = None  # Required for summarize_and_send_email

# Helper functions
def convert_objectid_to_str(doc):
    """Convert MongoDB ObjectId to string for JSON serialization"""
    if isinstance(doc, dict):
        return {key: convert_objectid_to_str(value) for key, value in doc.items()}
    elif isinstance(doc, list):
        return [convert_objectid_to_str(item) for item in doc]
    elif hasattr(doc, '__dict__'):
        return str(doc)
    else:
        return doc

async def send_to_n8n_gmail_summarization(payload: dict):
    """Send Gmail summarization request to n8n webhook"""
    try:
        webhook_url = os.environ.get('N8N_WEBHOOK_URL')
        if not webhook_url:
            raise ValueError("N8N_WEBHOOK_URL not configured")
        
        logger.info(f"📧 Sending Gmail summarization request to n8n: {payload}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            result = response.json() if response.text else {}
            
        logger.info(f"✅ N8N Gmail summarization response: {result}")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"❌ N8N Gmail summarization error: {e}")
        return {"success": False, "error": str(e)}

async def _handle_post_package_confirmation(request: ChatRequest) -> tuple:
    """Handle confirmation of pending post prompt package"""
    try:
        pending_data = pending_post_packages[request.session_id]
        
        # Send to N8N webhook
        webhook_result = await send_to_n8n({
            "intent": "generate_post_prompt_package",
            "session_id": request.session_id,
            "post_description": pending_data.get("post_description", ""),
            "ai_instructions": pending_data.get("ai_instructions", ""),
            "topic": pending_data.get("topic", ""),
            "project_name": pending_data.get("project_name", ""),
            "project_type": pending_data.get("project_type", ""),
            "tech_stack": pending_data.get("tech_stack", ""),
            "status": "pending"
        })
        
        # Clear the pending data
        del pending_post_packages[request.session_id]
        
        response_text = "✅ **Post Prompt Package Sent Successfully!**\n\nYour LinkedIn post preparation package has been sent to the automation system. You can now use the Post Description and AI Instructions to generate your LinkedIn post with any AI tool of your choice."
        intent_data = {"intent": "post_package_sent", "webhook_result": webhook_result}
        
        return response_text, intent_data
        
    except Exception as e:
        logger.error(f"Error sending post package to webhook: {e}")
        response_text = "❌ **Error sending post package.** Please try again or contact support if the issue persists."
        intent_data = {"intent": "post_package_error", "error": str(e)}
        return response_text, intent_data

def format_admin_debug_context(context_data: dict, session_id: str) -> str:
    """Format MCP context data for admin debug display"""
    try:
        formatted_output = f"🧠 **Stored Context for Session: {session_id}**\n\n"
        
        if not context_data:
            return formatted_output + "❌ No context data found for this session."
        
        # Group by intent type
        intents = {}
        for entry in context_data:
            intent = entry.get('intent', 'unknown')
            if intent not in intents:
                intents[intent] = []
            intents[intent].append(entry)
        
        for intent, entries in intents.items():
            formatted_output += f"### 🎯 Intent: {intent.upper()}\n"
            
            for i, entry in enumerate(entries, 1):
                timestamp = entry.get('timestamp', 'Unknown')
                formatted_output += f"\n**Entry {i}** (⏰ {timestamp})\n"
                
                if 'user_message' in entry:
                    formatted_output += f"👤 **User:** {entry['user_message']}\n"
                
                if 'ai_response' in entry:
                    response_preview = entry['ai_response'][:150] + "..." if len(entry['ai_response']) > 150 else entry['ai_response']
                    formatted_output += f"🤖 **AI:** {response_preview}\n"
                
                if 'routing_info' in entry and entry['routing_info']:
                    routing = entry['routing_info']
                    formatted_output += f"🧭 **Routing:** {routing.get('model', 'Unknown')} (confidence: {routing.get('confidence', 0):.2f})\n"
                
                if 'agent_results' in entry and entry['agent_results']:
                    results = entry['agent_results']
                    formatted_output += f"🎯 **Agent Results:** {len(results)} entries\n"
                    for j, result in enumerate(results[:3], 1):  # Show first 3 results
                        result_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                        formatted_output += f"   {j}. {result_preview}\n"
                
                formatted_output += "---\n"
        
        return formatted_output
        
    except Exception as e:
        logger.error(f"Context formatting error: {e}")
        return f"🧠 **Stored Context for Session: {session_id}**\n\n❌ Error formatting context: {str(e)}"

# Routes
@api_router.post("/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest):
    """Enhanced chat endpoint with MCP context awareness and Gmail summarization support"""
    try:
        logger.info(f"🚀 Enhanced Chat Processing: {request.message}")
        
        # STEP 1: Save user message immediately for proper conversation history
        user_msg = UserMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            message=request.message
        )
        await db.chat_messages.insert_one(user_msg.dict())
        logger.info(f"💾 Saved user message: {user_msg.id}")
        
        # STEP 2: Check for Gmail summarization intents first
        user_msg_lower = request.message.lower().strip()
        
        # Gmail summarization intent detection
        if any(phrase in user_msg_lower for phrase in [
            "summarize my emails", "summarize my last", "summarize emails", 
            "summarise my emails", "summarise my last", "summarise emails",
            "email summary", "summarize my gmail", "summarize my inbox",
            "summarise my gmail", "summarise my inbox"
        ]):
            # Extract number of emails to summarize (default to 4)
            import re
            numbers = re.findall(r'\d+', request.message)
            limit = int(numbers[0]) if numbers else 4
            
            # Check if they want to send to email
            send_to_email = any(phrase in user_msg_lower for phrase in [
                "send to", "email to", "send summary to", "email summary to"
            ])
            
            if send_to_email:
                # Extract email address if present
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, request.message)
                to_email = emails[0] if emails else None
                
                if not to_email:
                    response_text = "📧 Please specify the email address where you want to send the summary. For example: 'Summarize my last 4 emails and send to john@example.com'"
                    intent_data = {"intent": "gmail_summarize_email_missing", "limit": limit}
                    needs_approval = False
                else:
                    # Send summarize_and_send_email request to n8n
                    payload = {
                        "intent": "summarize_and_send_email",
                        "limit": limit,
                        "toEmail": to_email
                    }
                    
                    n8n_result = await send_to_n8n_gmail_summarization(payload)
                    
                    if n8n_result.get("success"):
                        response_text = f"✅ Gmail summary of your last {limit} emails has been sent to {to_email}!"
                        intent_data = {
                            "intent": "summarize_and_send_email",
                            "count": limit,
                            "time_filter": "latest",
                            "include_unread_only": False,
                            "user_email": to_email,
                            "n8n_response": n8n_result.get("data")
                        }
                    else:
                        response_text = f"❌ Failed to send email summary: {n8n_result.get('error', 'Unknown error')}"
                        intent_data = {
                            "intent": "gmail_summarize_error",
                            "error": n8n_result.get("error"),
                            "limit": limit,
                            "toEmail": to_email
                        }
                    needs_approval = False
            else:
                # Send summarize_to_chat request to n8n
                payload = {
                    "intent": "summarize_to_chat",
                    "limit": limit
                }
                
                n8n_result = await send_to_n8n_gmail_summarization(payload)
                
                if n8n_result.get("success"):
                    # Get the summary from n8n response
                    n8n_data = n8n_result.get("data", {})
                    summary = n8n_data.get("summary", "Email summary received from n8n workflow")
                    response_text = f"📧 **Gmail Summary (Last {limit} emails):**\n\n{summary}"
                    intent_data = {
                        "intent": "summarize_to_chat",
                        "count": limit,
                        "time_filter": "latest", 
                        "include_unread_only": False,
                        "summary": summary,
                        "n8n_response": n8n_data
                    }
                else:
                    response_text = f"❌ Failed to get email summary: {n8n_result.get('error', 'Unknown error')}"
                    intent_data = {
                        "intent": "gmail_summarize_error",
                        "error": n8n_result.get("error"),
                        "limit": limit
                    }
                needs_approval = False
        
        # STEP 3: Check for DeBERTa Gmail queries (existing logic) - but exclude summarization
        elif any(phrase in user_msg_lower for phrase in [
            "check my gmail", "check my inbox", "show me my emails", 
            "any unread emails", "new emails", "gmail inbox"
        ]) and not any(phrase in user_msg_lower for phrase in ["summarize", "summary"]):
            gmail_result = await realtime_gmail_service.process_gmail_query(
                request.message, 
                request.session_id
            )
            
            if gmail_result.get('success') and gmail_result.get('is_gmail_query'):
                if gmail_result.get('requires_auth'):
                    response_text = gmail_result.get('message', '🔐 Please connect Gmail to access your emails.')
                    intent_data = {
                        'intent': gmail_result.get('intent', 'gmail_auth_required'),
                        'requires_auth': True,
                        'auth_url': '/api/gmail/auth'
                    }
                    needs_approval = False
                else:
                    # Gmail query with authentication - fetch data
                    gmail_data_result = await realtime_gmail_service._fetch_gmail_data(
                        gmail_result.get('intent', 'gmail_summary'), 
                        request.message, 
                        request.session_id
                    )
                    
                    if gmail_data_result.get('success') and gmail_data_result.get('data'):
                        gmail_data = gmail_data_result.get('data', {})
                        emails = gmail_data.get('emails', [])
                        email_count = gmail_data.get('count', 0)
                        
                        # Write Gmail data to MCP context
                        await mcp_service.write_context(
                            session_id=request.session_id,
                            intent=gmail_result.get('intent', 'gmail_summary'),
                            data={
                                'user_query': request.message,
                                'gmail_intent': gmail_result.get('intent'),
                                'confidence': gmail_result.get('confidence', 0.8),
                                'user_email': 'brainlyarpit8649@gmail.com',
                                'emails': emails,
                                'email_count': email_count
                            },
                            user_id='brainlyarpit8649@gmail.com'
                        )
                        
                        # Always provide structured Gmail response
                        response_text = f"📧 **Here are your emails ({email_count} found):**\n\n"
                        
                        for i, email in enumerate(emails[:10], 1):
                            from_name = email.get('from', 'Unknown')
                            subject = email.get('subject', 'No Subject')
                            snippet = email.get('snippet', 'No preview available')[:100]
                            response_text += f"**{i}. {from_name}** – {subject}\n{snippet}...\n\n"
                        
                        intent_data = {
                            'intent': gmail_result.get('intent'),
                            'emails': emails,
                            'email_count': email_count,
                            'method': 'enhanced_gmail',
                            'confidence': gmail_result.get('confidence', 0.8)
                        }
                    else:
                        response_text = gmail_data_result.get('message', '❌ Failed to access Gmail data')
                        intent_data = {
                            'intent': gmail_result.get('intent'),
                            'error': gmail_data_result.get('error', 'Gmail data fetch failed'),
                            'method': 'gmail_data_fetch_failed'
                        }
                    needs_approval = False
            else:
                # Not a Gmail query, proceed with normal processing
                response_text, intent_data, needs_approval = await process_regular_chat(request)
        else:
            # STEP 4: Regular chat processing with MCP context awareness
            response_text, intent_data, needs_approval = await process_regular_chat(request)
        
        # STEP 5: Save AI response message for proper conversation history
        ai_msg = AIMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            response=response_text,
            intent_data=intent_data,
            is_system=intent_data.get('intent') in ['gmail_auth_required', 'error', 'no_pending_package']
        )
        await db.chat_messages.insert_one(ai_msg.dict())
        logger.info(f"💾 Saved AI response message: {ai_msg.id}")
        
        final_response = ChatResponse(
            id=ai_msg.id,
            message=request.message,
            response=response_text,
            intent_data=intent_data,
            needs_approval=needs_approval,
            timestamp=ai_msg.timestamp
        )
        
        return final_response
        
    except Exception as e:
        logger.error(f"💥 Enhanced Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_regular_chat(request: ChatRequest):
    """Process regular chat with MCP context awareness"""
    try:
        # Read existing context from MCP for better AI responses
        previous_context = ""
        try:
            context_result = await mcp_service.read_context(request.session_id)
            if context_result.get("success") and context_result.get("context"):
                previous_context = await mcp_service.get_context_for_prompt(request.session_id)
                logger.info(f"📖 Retrieved context from MCP for session: {request.session_id}")
            else:
                logger.info(f"📭 No previous context found in MCP for session: {request.session_id}")
        except Exception as context_error:
            logger.warning(f"⚠️ Error reading context from MCP: {context_error}")
            previous_context = ""
        
        # Check if this is a send confirmation for a pending post prompt package
        user_msg_lower = request.message.lower().strip()
        send_commands = ["send", "yes, go ahead", "submit", "send it", "yes go ahead", "go ahead"]
        
        email_keywords = ["email", "mail", "@", "message to", "write to"]
        is_likely_email = any(keyword in user_msg_lower for keyword in email_keywords)
        is_short_message = len(request.message.split()) <= 5
        
        is_send_command = (
            any(cmd in user_msg_lower for cmd in send_commands) and 
            is_short_message and 
            not is_likely_email
        )
        
        if is_send_command and request.session_id in pending_post_packages:
            # Handle pending post package confirmation
            response_text, intent_data = await _handle_post_package_confirmation(request)
            needs_approval = False
            
        elif is_send_command and request.session_id not in pending_post_packages:
            # User said send but no pending post package
            response_text = "🤔 I don't see any pending LinkedIn post prompt package to send. Please first ask me to help you prepare a LinkedIn post about your project or topic."
            intent_data = {"intent": "no_pending_package"}
            needs_approval = False
            
        else:
            # Regular hybrid AI processing with context
            intent_data, response_text, routing_decision = await advanced_hybrid_ai.process_message(
                request.message, 
                request.session_id
            )
            
            logger.info(f"🧠 Advanced Routing: {routing_decision.primary_model.value} (confidence: {routing_decision.confidence:.2f})")
            logger.info(f"💡 Routing Logic: {routing_decision.reasoning}")
            
            # Write context to MCP for memory management
            try:
                context_data = mcp_service.prepare_context_data(
                    user_message=request.message,
                    ai_response=response_text,
                    intent_data=intent_data,
                    routing_info={
                        "model": routing_decision.primary_model.value,
                        "confidence": routing_decision.confidence,
                        "reasoning": routing_decision.reasoning
                    }
                )
                
                await mcp_service.write_context(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    intent=intent_data.get("intent", "general_chat"),
                    data=context_data
                )
                
                logger.info(f"💾 Wrote enhanced context to MCP for session: {request.session_id}")
            except Exception as context_error:
                logger.warning(f"⚠️ Error writing context to MCP: {context_error}")
            
            # Determine if approval is needed - ONLY for send_email intent
            needs_approval = intent_data.get("intent") == "send_email"
            
            # Handle generate_post_prompt_package intent
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

@api_router.get("/admin/debug/context")
async def admin_debug_context_get(session_id: str = None, command: str = None, token: str = Header(None, alias="x-debug-token")):
    """Admin Debug Toggle: View MCP-stored messages for debugging (GET endpoint)"""
    try:
        # Verify admin token
        if token != os.getenv("DEBUG_ADMIN_TOKEN", "elva-admin-debug-2024-secure"):
            raise HTTPException(status_code=403, detail="Invalid debug token")
        
        if not command:
            return {"error": "Missing command parameter"}
        
        if not session_id:
            return {"error": "Missing session_id parameter"}
        
        # Read context from MCP
        mcp_context = await mcp_service.read_context(session_id)
        
        if not mcp_context.get('success'):
            return {
                "success": False,
                "session_id": session_id,
                "error": "Failed to read MCP context",
                "details": mcp_context.get('error', 'Unknown error')
            }
        
        # Format the response for clean display in chat
        context_data = mcp_context.get('data', {})
        appends = mcp_context.get('appends', [])
        
        formatted_context = format_admin_debug_context(appends, session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "formatted_context": formatted_context,
            "raw_data": {
                "context_summary": {
                    "initial_context": context_data.get('context', {}),
                    "total_appends": len(appends),
                    "last_updated": context_data.get('updated_at', 'Unknown')
                },
                "message_history": appends
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Admin debug context error: {e}")
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
        frontend_url = os.getenv("REACT_APP_FRONTEND_URL", "https://c20efb94-1a9f-42d9-a126-b5157ee976a4.preview.emergentagent.com")
        return RedirectResponse(url=f"{frontend_url}?gmail_auth=success")
        
    except Exception as e:
        logger.error(f"Gmail callback error: {e}")
        frontend_url = os.getenv("REACT_APP_FRONTEND_URL", "https://c20efb94-1a9f-42d9-a126-b5157ee976a4.preview.emergentagent.com")
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

@api_router.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        try:
            await client.admin.command('ping')
            mongodb_status = "connected"
        except Exception:
            mongodb_status = "disconnected"
        
        # Check MCP service
        try:
            mcp_health = await mcp_service.health_check()
            mcp_status = "connected" if mcp_health.get("success") else "disconnected"
        except Exception:
            mcp_status = "disconnected"
        
        # Check DeBERTa Gmail system stats
        try:
            deberta_stats = await deberta_gmail_detector.get_classification_stats()
        except Exception:
            deberta_stats = {"error": "Statistics unavailable"}
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": mongodb_status,
                "mcp_service": mcp_status,
                "groq_api": "configured" if os.getenv("GROQ_API_KEY") else "missing",
                "claude_api": "configured" if os.getenv("CLAUDE_API_KEY") else "missing"
            },
            "gmail_api_integration": {
                "status": "ready",
                "oauth2_flow": "implemented",
                "credentials_configured": True,
                "scopes": ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"],
                "endpoints": [
                    "/api/gmail/auth", "/api/gmail/callback", "/api/gmail/status",
                    "/api/gmail/inbox", "/api/gmail/send", "/api/gmail/email/{id}"
                ]
            },
            "deberta_gmail_integration": {
                "version": "2.0", 
                "model": "microsoft/deberta-v3-base",
                "status": "ready",
                "features": [
                    "high_accuracy_intent_classification",
                    "real_gmail_data_only",
                    "no_placeholder_responses", 
                    "instant_oauth_refresh",
                    "formatted_chat_responses",
                    "inbox_summary", "email_search", "unread_count", "email_summarization"
                ],
                "classification_stats": deberta_stats
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
                    "sequential_tasks": ["professional_emails", "complex_creative"],
                    "web_automation_tasks": ["web_scraping", "data_extraction"]
                }
            },
            "n8n_webhook": "configured" if os.getenv("N8N_WEBHOOK_URL") else "missing",
            "gmail_summarization": {
                "status": "ready",
                "intents": ["summarize_to_chat", "summarize_and_send_email"],
                "webhook_url": os.getenv("N8N_WEBHOOK_URL"),
                "features": ["context_aware_summarization", "email_count_extraction", "targeted_email_sending"]
            },
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