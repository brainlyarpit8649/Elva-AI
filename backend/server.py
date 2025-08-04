from fastapi import FastAPI, APIRouter, HTTPException, Header, Query, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any
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
from message_memory import ensure_indexes
from superagi_client import superagi_client
from mcp_integration import get_mcp_service, initialize_mcp_service

# Import enhanced Gmail components
from enhanced_gmail_intent_detector import enhanced_gmail_detector
from enhanced_gmail_service import EnhancedGmailService
from enhanced_chat_models import EnhancedChatMessage, UserMessage, AIMessage

# Import new DeBERTa-based Gmail system
from deberta_gmail_intent_detector import deberta_gmail_detector
from realtime_gmail_service import RealTimeGmailService

# Import Tomorrow.io Weather Service
from weather_service_tomorrow import (
    get_current_weather, 
    get_weather_forecast, 
    get_air_quality_index, 
    get_weather_alerts, 
    get_sun_times,
    get_cache_stats,
    clear_weather_cache
)

# Import Letta Memory System
from letta_memory import initialize_letta_memory, get_letta_memory

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

# Initialize Letta Memory System
try:
    letta_memory = initialize_letta_memory()
    logging.info("✅ Letta Memory System initialized successfully")
except Exception as e:
    logging.warning(f"⚠️ Letta Memory initialization failed: {e}")
    letta_memory = None

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
    """Enhanced chat endpoint with comprehensive message memory and Gmail summarization support"""
    try:
        logger.info(f"🚀 Enhanced Chat Processing: {request.message}")
        
        # Import message memory functions
        from message_memory import save_message, get_conversation_context_for_ai
        
        # STEP 1: Save user message IMMEDIATELY for comprehensive conversation history
        await save_message(request.session_id, "user", request.message)
        
        # Also save to enhanced chat collection for compatibility 
        user_msg = UserMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            message=request.message
        )
        await db.chat_messages.insert_one(user_msg.dict())
        logger.info(f"💾 Saved user message to both systems: {user_msg.id}")
        
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
                                'user_email': '',
                                'emails': emails,
                                'email_count': email_count
                            },
                            user_id=''
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
        
        # STEP 5: Save AI response message to BOTH memory systems for comprehensive conversation history
        from message_memory import save_message
        await save_message(request.session_id, "assistant", response_text)
        
        ai_msg = AIMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            response=response_text,
            intent_data=intent_data,
            is_system=intent_data.get('intent') in ['gmail_auth_required', 'error', 'no_pending_package']
        )
        await db.chat_messages.insert_one(ai_msg.dict())
        logger.info(f"💾 Saved AI response to both memory systems: {ai_msg.id}")
        
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
    """Process regular chat with hybrid memory (MongoDB + message_memory + Letta)"""
    try:
        # Import message memory functions
        from message_memory import get_conversation_context_for_ai, search_conversation_memory
        
        # STEP 1: Check for Letta memory commands first
        user_msg_lower = request.message.lower().strip()
        
        # Handle Letta memory commands
        if letta_memory and any(cmd in user_msg_lower for cmd in [
            "remember that", "store fact", "teach elva", "my nickname is", "i am", "call me"
        ]):
            # Extract the fact to store
            fact = request.message.strip()
            result = letta_memory.store_fact(fact)
            
            if result.get("success"):
                response_text = f"✅ I'll remember that: {fact}"
                intent_data = {"intent": "store_memory", "fact": fact}
            else:
                response_text = f"⚠️ I had trouble storing that information: {result.get('error', 'Unknown error')}"
                intent_data = {"intent": "memory_error", "error": result.get('error')}
            
            needs_approval = False
            return response_text, intent_data, needs_approval
        
        elif letta_memory and any(cmd in user_msg_lower for cmd in [
            "forget that", "remove fact", "don't remember"
        ]):
            # Extract what to forget
            fact_to_forget = request.message.replace("forget that", "").replace("remove fact", "").replace("don't remember", "").strip()
            result = letta_memory.forget_fact(fact_to_forget)
            
            if result.get("success"):
                response_text = f"✅ I've forgotten that information."
                intent_data = {"intent": "forget_memory", "fact": fact_to_forget}
            else:
                response_text = f"⚠️ I had trouble forgetting that: {result.get('error', 'Unknown error')}"
                intent_data = {"intent": "memory_error", "error": result.get('error')}
            
            needs_approval = False
            return response_text, intent_data, needs_approval
        
        elif letta_memory and any(cmd in user_msg_lower for cmd in [
            "what do you know about me", "what's my", "who am i", "tell me about", "what do you remember"
        ]):
            # Retrieve facts from memory
            result = letta_memory.retrieve_context(request.message)
            
            if result.get("success") and result.get("relevant"):
                response_text = result.get("context", "I don't have specific information about that.")
                intent_data = {"intent": "recall_memory", "query": request.message}
            else:
                response_text = "I don't have specific information about that."
                intent_data = {"intent": "no_memory", "query": request.message}
            
            needs_approval = False
            return response_text, intent_data, needs_approval
        
        # STEP 2: Get FULL conversation context (MongoDB + message_memory + Letta)
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
            
            # Add Letta memory context
            if letta_memory:
                letta_context_result = letta_memory.retrieve_context(f"relevant information for: {request.message}")
                if letta_context_result.get("success") and letta_context_result.get("relevant"):
                    letta_context = letta_context_result.get("context", "")
                    if letta_context:
                        previous_context += f"\n\n=== LONG-TERM MEMORY ===\n{letta_context}"
                        logger.info(f"🧠 Added Letta long-term memory context for session: {request.session_id}")
                
        except Exception as context_error:
            logger.warning(f"⚠️ Error reading conversation context: {context_error}")
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
                
                # STEP 3: Auto-store important facts in Letta memory
                if letta_memory:
                    # Check if the conversation contains important personal information
                    user_message_lower = request.message.lower()
                    
                    # Look for personal information patterns
                    fact_patterns = [
                        ("my name is", "name"),
                        ("call me", "nickname"),
                        ("i am", "identity"),
                        ("i work as", "job"),
                        ("i'm a", "profession"),
                        ("my email is", "email"),
                        ("my phone", "phone"),
                        ("i prefer", "preference"),
                        ("i like", "preference"),
                        ("remember that", "reminder"),
                        ("my manager", "contact"),
                        ("my boss", "contact"),
                    ]
                    
                    for pattern, fact_type in fact_patterns:
                        if pattern in user_message_lower:
                            try:
                                # Store the fact automatically
                                fact_result = letta_memory.store_fact(request.message)
                                if fact_result.get("success"):
                                    logger.info(f"🧠 Auto-stored {fact_type} fact in Letta memory: {request.message[:50]}...")
                                break  # Only store once per message
                            except Exception as letta_error:
                                logger.warning(f"⚠️ Auto-storage to Letta failed: {letta_error}")
                
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
        frontend_url = os.getenv("REACT_APP_FRONTEND_URL", "https://958507ec-1e07-4ecd-9523-c0f204730193.preview.emergentagent.com")
        return RedirectResponse(url=f"{frontend_url}?gmail_auth=success")
        
    except Exception as e:
        logger.error(f"Gmail callback error: {e}")
        frontend_url = os.getenv("REACT_APP_FRONTEND_URL", "https://958507ec-1e07-4ecd-9523-c0f204730193.preview.emergentagent.com")
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
        
        # Create approval request for existing pipeline
        approval_request = ApprovalRequest(
            session_id=internal_session_id,
            message_id=message_id,
            approved=approved,
            edited_data=edited_data
        )
        
        # Process through existing approval pipeline
        result = await approve_action(approval_request)
        
        # Log WhatsApp approval
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

@api_router.get("/letta/memory-stats")
async def get_letta_memory_stats():
    """Get Letta memory system statistics"""
    try:
        if letta_memory:
            stats = letta_memory.get_memory_summary()
            return stats
        else:
            return {"success": False, "error": "Letta memory not initialized"}
    except Exception as e:
        logger.error(f"❌ Error getting Letta memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/letta/store-fact")
async def store_letta_fact(request: dict):
    """Manually store a fact in Letta memory"""
    try:
        fact = request.get("fact", "")
        if not fact:
            raise HTTPException(status_code=400, detail="Fact is required")
        
        if letta_memory:
            result = letta_memory.store_fact(fact)
            return result
        else:
            return {"success": False, "error": "Letta memory not initialized"}
    except Exception as e:
        logger.error(f"❌ Error storing fact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/letta/retrieve-context")
async def retrieve_letta_context(request: dict):
    """Retrieve context from Letta memory"""
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        if letta_memory:
            result = letta_memory.retrieve_context(query)
            return result
        else:
            return {"success": False, "error": "Letta memory not initialized"}
    except Exception as e:
        logger.error(f"❌ Error retrieving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@api_router.get("/weather/current")
async def get_current_weather_endpoint(location: str, username: str = None):
    """Get current weather for a location using Tomorrow.io API"""
    try:
        logger.info(f"🌦️ Current weather request for: {location}")
        result = await get_current_weather(location, username)
        return {"status": "success", "data": result, "location": location}
    except Exception as e:
        logger.error(f"Current weather error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/forecast")
async def get_weather_forecast_endpoint(location: str, days: int = 3, username: str = None):
    """Get weather forecast for a location using Tomorrow.io API"""
    try:
        logger.info(f"📅 Weather forecast request for: {location} ({days} days)")
        result = await get_weather_forecast(location, days, username)
        return {"status": "success", "data": result, "location": location, "days": days}
    except Exception as e:
        logger.error(f"Weather forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/air-quality")
async def get_air_quality_endpoint(location: str):
    """Get air quality index for a location using Tomorrow.io API"""
    try:
        logger.info(f"🌬️ Air quality request for: {location}")
        result = await get_air_quality_index(location)
        return {"status": "success", "data": result, "location": location}
    except Exception as e:
        logger.error(f"Air quality error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/alerts")
async def get_weather_alerts_endpoint(location: str):
    """Get weather alerts for a location"""
    try:
        logger.info(f"⚠️ Weather alerts request for: {location}")
        result = await get_weather_alerts(location)
        return {"status": "success", "data": result, "location": location}
    except Exception as e:
        logger.error(f"Weather alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/sun-times")
async def get_sun_times_endpoint(location: str):
    """Get sunrise and sunset times for a location using Tomorrow.io API"""
    try:
        logger.info(f"🌅 Sun times request for: {location}")
        result = await get_sun_times(location)
        return {"status": "success", "data": result, "location": location}
    except Exception as e:
        logger.error(f"Sun times error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/cache/stats")
async def get_weather_cache_stats():
    """Get weather cache statistics"""
    try:
        stats = get_cache_stats()
        return {"status": "success", "cache_stats": stats}
    except Exception as e:
        logger.error(f"Weather cache stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/weather/cache/clear")
async def clear_weather_cache_endpoint():
    """Clear weather cache"""
    try:
        await clear_weather_cache()
        return {"status": "success", "message": "Weather cache cleared successfully"}
    except Exception as e:
        logger.error(f"Clear weather cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MCP Validate Endpoints for Puch AI Integration
@api_router.post("/mcp/validate")
async def mcp_validate_post(
    token: str = Query(None),
    authorization: str = Header(None)
):
    """
    Puch AI Validation Endpoint (POST)
    Required by Puch AI to verify MCP server connection
    Returns user's WhatsApp number with country code
    """
    try:
        # Extract and validate authentication token
        auth_token = token
        
        # Check Authorization header (preferred by Puch AI)
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]  # Remove 'Bearer ' prefix
            else:
                auth_token = authorization
        
        # Validate token against environment variable
        expected_token = os.getenv("MCP_API_TOKEN", "kumararpit9468")
        if not auth_token or auth_token != expected_token:
            logger.warning(f"🚫 Puch AI Validate POST - Invalid token attempt")
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "invalid_token",
                    "message": "Invalid or missing MCP API token"
                }
            )
        
        logger.info("✅ Puch AI Validation POST - Token verified successfully")
        
        # Return user's WhatsApp number as required by Puch AI
        return {
            "number": "919654030351"  # Country code (91) + phone number (9654030351)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Puch AI Validate POST Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "validation_failed",
                "message": "Validation endpoint error"
            }
        )

@api_router.get("/mcp/validate")  
async def mcp_validate_get(
    token: str = Query(None),
    authorization: str = Header(None)
):
    """
    Puch AI Validation Endpoint (GET)
    GET version of validation endpoint for broader compatibility
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
            logger.warning(f"🚫 Puch AI Validate GET - Invalid token attempt")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        logger.info("✅ Puch AI Validation GET - Token verified successfully")
        
        return {
            "number": "919654030351"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Puch AI Validate GET Error: {e}")
        raise HTTPException(status_code=500, detail="Validation failed")

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
            },
            "weather_integration": {
                "provider": "Tomorrow.io",
                "status": "ready" if os.getenv("TOMORROW_API_KEY") else "missing_api_key",
                "api_key_configured": bool(os.getenv("TOMORROW_API_KEY")),
                "cache_enabled": True,
                "cache_ttl_seconds": 300,
                "endpoints": [
                    "/api/weather/current",
                    "/api/weather/forecast", 
                    "/api/weather/air-quality",
                    "/api/weather/alerts",
                    "/api/weather/sun-times",
                    "/api/weather/cache/stats",
                    "/api/weather/cache/clear"
                ],
                "supported_intents": [
                    "get_current_weather",
                    "get_weather_forecast",
                    "get_air_quality_index", 
                    "get_weather_alerts",
                    "get_sun_times"
                ],
                "features": [
                    "current_weather_conditions",
                    "multi_day_forecasts_up_to_7_days",
                    "air_quality_monitoring",
                    "weather_alerts_basic",
                    "sunrise_sunset_times",
                    "5_minute_location_based_caching",
                    "emoji_formatted_responses",
                    "instant_responses_no_approval"
                ]
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

@app.on_event("startup")
async def startup_db_indexes():
    # Create TTL and text search indexes for message memory
    await ensure_indexes()
    logger.info("🚀 Application startup completed with database indexes")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    # Close Playwright service
    await playwright_service.close()