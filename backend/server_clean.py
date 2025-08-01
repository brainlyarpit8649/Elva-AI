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
            result = response.json()
            
        logger.info(f"✅ N8N Gmail summarization response: {result}")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"❌ N8N Gmail summarization error: {e}")
        return {"success": False, "error": str(e)}

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
            "email summary", "summarize my gmail", "summarize my inbox"
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
                            "intent": "gmail_summarize_and_send_email",
                            "limit": limit,
                            "toEmail": to_email,
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
                        "intent": "gmail_summarize_to_chat",
                        "limit": limit,
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
        
        # STEP 3: Check for DeBERTa Gmail queries (existing logic)
        elif any(phrase in user_msg_lower for phrase in [
            "check my gmail", "check my inbox", "show me my emails", 
            "any unread emails", "new emails", "gmail inbox"
        ]):
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
                request.session_id,
                previous_context=previous_context  # Pass context to AI
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

# Continue with rest of the endpoints...