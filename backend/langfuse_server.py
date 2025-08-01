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

# Import Langfuse for observability
from langfuse import Langfuse

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

# Initialize Langfuse for observability
langfuse = Langfuse(
    public_key=os.environ.get('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.environ.get('LANGFUSE_SECRET_KEY'),
    host=os.environ.get('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')
)

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

def format_admin_context_display(session_id: str, context_data: dict) -> str:
    """Format MCP context data for admin debugging display"""
    try:
        formatted = f"🧠 **Stored Context for Session: {session_id}**\n\n"
        
        if not context_data:
            return formatted + "No context data available."
        
        # Extract main context and appends
        main_context = context_data.get('context', {})
        appends = context_data.get('appends', [])
        
        # Display session info
        formatted += f"**📋 Session Info:**\n"
        formatted += f"• Session ID: {context_data.get('session_id', 'N/A')}\n"
        formatted += f"• Last Updated: {context_data.get('last_updated', 'N/A')}\n"
        formatted += f"• Total Appends: {context_data.get('total_appends', 0)}\n\n"
        
        # Display main conversation context
        if main_context and 'data' in main_context:
            context_info = main_context['data']
            
            # Show chat history
            chat_history = context_info.get('chat_history', [])
            if chat_history:
                formatted += f"**💬 Chat Messages ({len(chat_history)}):**\n"
                for i, msg in enumerate(chat_history[-5:], 1):  # Last 5 messages
                    role = msg.get('role', 'unknown').title()
                    content = msg.get('content', '')[:80] + ('...' if len(msg.get('content', '')) > 80 else '')
                    timestamp = msg.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime('%I:%M %p')
                        except:
                            time_str = timestamp[:8]  # Fallback
                    else:
                        time_str = 'N/A'
                    formatted += f"{i}️⃣ [{role}] \"{content}\" ({time_str})\n"
                formatted += "\n"
            
            # Show intent information
            if 'intent_data' in context_info:
                intent_data = context_info['intent_data']
                formatted += f"**🎯 Current Intent:**\n"
                formatted += f"• Intent: {intent_data.get('intent', 'N/A')}\n"
                formatted += f"• Confidence: {intent_data.get('confidence', 'N/A')}\n\n"
        
        # Display agent results (appends)
        if appends:
            formatted += f"**🤖 Agent Results ({len(appends)}):**\n"
            for i, append in enumerate(appends[-3:], 1):  # Last 3 agent results
                source = append.get('source', 'unknown').title()
                output = append.get('output', {})
                timestamp = append.get('timestamp', '')
                
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%I:%M %p')
                    except:
                        time_str = timestamp[:8]
                else:
                    time_str = 'N/A'
                
                # Summarize output
                output_summary = "No output"
                if output:
                    if isinstance(output, dict):
                        keys = list(output.keys())[:3]
                        output_summary = f"Data with keys: {', '.join(keys)}"
                    else:
                        output_summary = str(output)[:60] + ('...' if len(str(output)) > 60 else '')
                
                formatted += f"{i}️⃣ [Agent:{source}] \"{output_summary}\" ({time_str})\n"
            formatted += "\n"
        
        # Display summary
        formatted += f"**📊 Summary:**\n"
        formatted += f"• Total Messages: {len(chat_history) if 'chat_history' in locals() else 'N/A'}\n"
        formatted += f"• Agent Interactions: {len(appends)}\n"
        formatted += f"• Context Size: ~{len(str(context_data))} characters"
        
        return formatted
        
    except Exception as e:
        return f"🧠 **Stored Context for Session: {session_id}**\n\n❌ Error formatting context: {str(e)}"

# Routes with Langfuse observability
@api_router.post("/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest):
    """Enhanced chat endpoint with comprehensive Langfuse observability"""
    
    # Initialize Langfuse trace for the entire chat pipeline
    trace = langfuse.trace(
        name="elva_chat_pipeline",
        input={
            "user_message": request.message,
            "session_id": request.session_id,
            "user_id": request.user_id
        },
        metadata={
            "endpoint": "/api/chat",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    try:
        logger.info(f"🚀 Enhanced Chat Processing: {request.message}")
        
        # SPAN 1: User Message Processing
        user_message_span = trace.span(
            name="user_message_processing",
            input={"message": request.message, "session_id": request.session_id}
        )
        
        # STEP 1: Save user message immediately for proper conversation history
        user_msg = UserMessage(
            session_id=request.session_id,
            user_id=request.user_id,
            message=request.message
        )
        await db.chat_messages.insert_one(user_msg.dict())
        logger.info(f"💾 Saved user message: {user_msg.id}")
        
        user_message_span.end(output={"user_message_id": user_msg.id, "saved": True})
        
        # SPAN 2: DeBERTa Gmail Intent Detection
        gmail_detection_span = trace.span(
            name="deberta_gmail_intent_detection",
            input={"query": request.message}
        )
        
        # STEP 2: Check for Gmail-specific queries first using DeBERTa-based detection
        gmail_result = await realtime_gmail_service.process_gmail_query(
            request.message, 
            request.session_id
        )
        
        gmail_detection_span.end(output={
            "is_gmail_query": gmail_result.get('is_gmail_query'),
            "intent": gmail_result.get('intent'),
            "confidence": gmail_result.get('confidence'),
            "requires_auth": gmail_result.get('requires_auth')
        })
        
        if gmail_result.get('success') and gmail_result.get('is_gmail_query'):
            if gmail_result.get('requires_auth'):
                # SPAN 3A: Gmail Authentication Required
                auth_span = trace.span(
                    name="gmail_auth_required",
                    input={"intent": gmail_result.get('intent')}
                )
                
                # Gmail query but not authenticated
                response_text = gmail_result.get('message', '🔐 Please connect Gmail to access your emails.')
                intent_data = {
                    'intent': gmail_result.get('intent', 'gmail_auth_required'),
                    'requires_auth': True,
                    'auth_url': '/api/gmail/auth'
                }
                needs_approval = False
                logger.info(f"🔐 Gmail authentication required for: {gmail_result.get('intent')}")
                
                auth_span.end(output={
                    "auth_required": True,
                    "auth_url": "/api/gmail/auth",
                    "message": response_text
                })
                
            else:
                # SPAN 3B: Gmail API Processing  
                gmail_api_span = trace.span(
                    name="gmail_api_processing",
                    input={
                        "intent": gmail_result.get('intent'),
                        "authenticated": True
                    }
                )
                
                # Gmail query with authentication - First fetch Gmail data, then route through SuperAGI
                logger.info(f"📧 Gmail query detected: {gmail_result.get('intent')} - Fetching Gmail data first")
                
                # First get Gmail data directly
                gmail_data_result = await realtime_gmail_service._fetch_gmail_data(
                    gmail_result.get('intent', 'gmail_summary'), 
                    request.message, 
                    request.session_id
                )
                
                if gmail_data_result.get('success') and gmail_data_result.get('data'):
                    # Get Gmail data for structured response
                    gmail_data = gmail_data_result.get('data', {})
                    emails = gmail_data.get('emails', [])
                    email_count = gmail_data.get('count', 0)
                    
                    gmail_api_span.update(output={
                        "gmail_data_fetched": True,
                        "email_count": email_count,
                        "emails_preview": [{"from": email.get("from"), "subject": email.get("subject")} 
                                         for email in emails[:3]]  # Preview first 3
                    })
                    
                    # Write Gmail data to MCP context for SuperAGI
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
                    
                    # Try SuperAGI first, but always fallback to structured Gmail display
                    try:
                        superagi_result = await superagi_client.run_task(
                            goal=request.message,
                            agent_type="email_agent",  
                            session_id=request.session_id
                        )
                        
                        if superagi_result.get('success') and superagi_result.get('email_summary'):
                            response_text = superagi_result.get('email_summary', '')
                            # Add structured email data display
                            if email_count > 0:
                                response_text += f"\n\n📧 **Analyzed {email_count} emails**"
                                if superagi_result.get('key_insights'):
                                    response_text += f"\n\n🔍 **Key Insights:**\n" + '\n'.join([f"• {insight}" for insight in superagi_result.get('key_insights', [])])
                                if superagi_result.get('suggested_actions'):
                                    response_text += f"\n\n✅ **Suggested Actions:**\n" + '\n'.join([f"• {action}" for action in superagi_result.get('suggested_actions', [])])
                        else:
                            raise Exception("SuperAGI did not provide valid response")
                            
                    except Exception as superagi_error:
                        logger.warning(f"SuperAGI failed: {superagi_error}, using Gmail data directly")
                        # ALWAYS provide structured Gmail response as fallback
                        response_text = f"📧 **Here are your emails ({email_count} found):**\n\n"
                        
                        # Add formatted email previews
                        for i, email in enumerate(emails[:10], 1):  # Show max 10 emails
                            from_name = email.get('from', 'Unknown')
                            subject = email.get('subject', 'No Subject')
                            snippet = email.get('snippet', 'No preview available')[:100]
                            response_text += f"**{i}. {from_name}** – {subject}\n{snippet}...\n\n"
                    
                    # CRITICAL: Always include structured intent_data for frontend
                    intent_data = {
                        'intent': gmail_result.get('intent'),
                        'emails': emails,  # Frontend needs this for card display
                        'email_count': email_count,  # Frontend needs this for count display
                        'method': 'enhanced_gmail_with_fallback',
                        'confidence': gmail_result.get('confidence', 0.8)
                    }
                    
                    gmail_api_span.end()
                else:
                    # Gmail data fetch failed - show authentication or error message
                    response_text = gmail_data_result.get('message', '❌ Failed to access Gmail data')
                    intent_data = {
                        'intent': gmail_result.get('intent'),
                        'error': gmail_data_result.get('error', 'Gmail data fetch failed'),
                        'method': 'gmail_data_fetch_failed'
                    }
                    
                    gmail_api_span.end(output={
                        "gmail_data_fetched": False,
                        "error": gmail_data_result.get('error', 'Gmail data fetch failed')
                    })
                
                needs_approval = False
            
        else:
            # SPAN 4: Hybrid AI Processing (Non-Gmail)
            hybrid_ai_span = trace.span(
                name="hybrid_ai_processing",
                input={"message": request.message, "is_gmail": False}
            )
            
            # STEP 3: Not a Gmail query - use existing hybrid AI system
            # Check if this is a send confirmation for a pending post prompt package
            user_msg_lower = request.message.lower().strip()
            send_commands = ["send", "yes, go ahead", "submit", "send it", "yes go ahead", "go ahead"]
            
            # Only consider it a send command if it's a short message (likely confirmation)
            # and doesn't contain email-related keywords
            email_keywords = ["email", "mail", "@", "message to", "write to"]
            is_likely_email = any(keyword in user_msg_lower for keyword in email_keywords)
            is_short_message = len(request.message.split()) <= 5  # Short confirmation messages
            
            is_send_command = (
                any(cmd in user_msg_lower for cmd in send_commands) and 
                is_short_message and 
                not is_likely_email
            )
            
            if is_send_command and request.session_id in pending_post_packages:
                # Handle pending post package confirmation
                response_text, intent_data = await _handle_post_package_confirmation(request)
                needs_approval = False
                hybrid_ai_span.update(output={"post_package_sent": True})
                
            elif is_send_command and request.session_id not in pending_post_packages:
                # User said send but no pending post package
                response_text = "🤔 I don't see any pending LinkedIn post prompt package to send. Please first ask me to help you prepare a LinkedIn post about your project or topic."
                intent_data = {"intent": "no_pending_package"}
                needs_approval = False
                hybrid_ai_span.update(output={"no_pending_package": True})
                
            else:
                # Regular hybrid AI processing
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
                    
                    # Process message with hybrid AI
                    intent_data, response_text, routing_decision = await advanced_hybrid_ai.process_message(
                        request.message, 
                        request.session_id
                    )
                    
                    logger.info(f"🧠 Advanced Routing: {routing_decision.primary_model.value} (confidence: {routing_decision.confidence:.2f})")
                    logger.info(f"💡 Routing Logic: {routing_decision.reasoning}")
                    
                    hybrid_ai_span.update(output={
                        "routing_model": routing_decision.primary_model.value,
                        "routing_confidence": routing_decision.confidence,
                        "routing_reasoning": routing_decision.reasoning,
                        "intent": intent_data.get("intent"),
                        "response_length": len(response_text)
                    })
                    
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
                        
                except Exception as e:
                    logger.error(f"❌ Hybrid AI processing error: {e}")
                    response_text = "Sorry, I encountered an error processing your request. Please try again! 🤖"
                    intent_data = {"intent": "error", "error": str(e)}
                    needs_approval = False
                    hybrid_ai_span.update(output={"error": str(e)})
            
            hybrid_ai_span.end()
        
        # SPAN 5: Response Generation and Storage
        response_span = trace.span(
            name="response_generation",
            input={
                "response_text": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                "needs_approval": needs_approval,
                "intent": intent_data.get("intent") if intent_data else None
            }
        )
        
        # STEP 4: Save AI response message for proper conversation history
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
        
        response_span.end(output={
            "ai_message_id": ai_msg.id,
            "final_response_saved": True,
            "response_length": len(response_text)
        })
        
        # Complete the trace with final output
        trace.update(
            output={
                "response": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                "intent": intent_data.get("intent") if intent_data else None,
                "needs_approval": needs_approval,
                "message_id": ai_msg.id
            }
        )
        
        return final_response
        
    except Exception as e:
        logger.error(f"💥 Enhanced Chat Error: {e}")
        
        # Update trace with error
        trace.update(
            output={"error": str(e)},
            metadata={"error_type": "chat_pipeline_error"}
        )
        
        raise HTTPException(status_code=500, detail=str(e))

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

# Keep all existing endpoints from original server.py here...
# This is a simplified version focusing on the chat endpoint with Langfuse integration
# The full implementation would include all other endpoints from the original file

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)