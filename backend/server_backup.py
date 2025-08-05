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

# Routes
@api_router.post("/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest):
    """Enhanced chat endpoint with improved Gmail integration and Langfuse observability"""
    
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
                },
                source="elva"
            )
            
            if append_result.get("success"):
                logger.info(f"📝 Approval result appended to MCP - Session: {request.session_id}")
            else:
                logger.warning(f"⚠️ MCP append failed: {append_result.get('error')}")
                
        except Exception as mcp_error:
            logger.warning(f"⚠️ MCP append error: {mcp_error}")
            # Continue processing even if MCP append fails
        
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
async def get_enhanced_chat_history(session_id: str):
    """Enhanced chat history endpoint that properly handles user/AI message distinction"""
    try:
        logger.info(f"Getting enhanced chat history for session: {session_id}")
        
        # Get all messages for the session, sorted by timestamp
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(1000)
        
        # Convert ObjectIds to strings and ensure proper message structure
        enhanced_messages = []
        for msg in messages:
            # Convert ObjectId to string
            serialized_msg = convert_objectid_to_str(msg)
            
            # Determine if this is a user message or AI message
            # Check for explicit is_user flag first, then fallback to heuristics
            if 'is_user' in serialized_msg:
                is_user = serialized_msg['is_user']
            else:
                # Legacy messages - determine by presence of message vs response
                is_user = bool(serialized_msg.get('message', '').strip()) and not bool(serialized_msg.get('response', '').strip())
            
            # Create properly structured message for frontend
            if is_user:
                # User message
                enhanced_msg = {
                    'id': serialized_msg.get('id', ''),
                    'message': serialized_msg.get('message', ''),
                    'isUser': True,
                    'timestamp': serialized_msg.get('timestamp', ''),
                    'session_id': session_id
                }
            else:
                # AI message
                enhanced_msg = {
                    'id': serialized_msg.get('id', ''),
                    'response': serialized_msg.get('response', ''),
                    'isUser': False,
                    'intent_data': serialized_msg.get('intent_data', {}),
                    'approved': serialized_msg.get('approved'),
                    'is_system': serialized_msg.get('is_system', False),
                    'is_welcome': serialized_msg.get('is_welcome', False),
                    'is_edit': serialized_msg.get('is_edit', False),
                    'timestamp': serialized_msg.get('timestamp', ''),
                    'session_id': session_id
                }
            
            enhanced_messages.append(enhanced_msg)
        
        logger.info(f"✅ Retrieved {len(enhanced_messages)} messages for session {session_id}")
        return {"messages": enhanced_messages, "total_count": len(enhanced_messages)}
        
    except Exception as e:
        logger.error(f"Enhanced history error: {e}")
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

@api_router.post("/superagi/run-task")
async def run_superagi_task(request: SuperAGITaskRequest):
    """
    Execute task with SuperAGI autonomous agents
    Integrates with MCP for context sharing
    """
    try:
        logger.info(f"🤖 SuperAGI Task Request: {request.goal} (agent: {request.agent_type})")
        
        # Execute task with SuperAGI
        result = await superagi_client.run_task(
            session_id=request.session_id,
            goal=request.goal,
            agent_type=request.agent_type
        )
        
        # Store result in chat history for user review
        if result.get("success"):
            chat_msg = ChatMessage(
                session_id=request.session_id,
                user_id="superagi_system",
                message=f"SuperAGI Task: {request.goal}",
                response=json.dumps(result, indent=2),
                intent_data={"intent": "superagi_task_result", "agent": request.agent_type}
            )
            await db.chat_messages.insert_one(chat_msg.dict())
            
            # Append SuperAGI results to MCP context
            try:
                append_result = await mcp_service.append_context(
                    session_id=request.session_id,
                    output={
                        "agent_type": request.agent_type,
                        "goal": request.goal,
                        "superagi_result": result,
                        "execution_status": "success" if result.get("success") else "failed",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    source="superagi"
                )
                
                if append_result.get("success"):
                    logger.info(f"📝 SuperAGI result appended to MCP - Session: {request.session_id}")
                else:
                    logger.warning(f"⚠️ MCP append failed for SuperAGI result: {append_result.get('error')}")
                    
            except Exception as mcp_error:
                logger.warning(f"⚠️ MCP append error for SuperAGI: {mcp_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ SuperAGI task execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mcp/write-context")
async def write_mcp_context(request: MCPContextRequest):
    """
    Write context data to MCP service
    Used by Elva to store structured context for SuperAGI agents
    """
    try:
        logger.info(f"📝 Writing MCP context for session: {request.session_id}")
        
        # Use the MCP integration service
        result = await mcp_service.write_context(
            session_id=request.session_id,
            intent=request.intent,
            data=request.data,
            user_id=request.user_id
        )
            
        if result.get("success"):
            return {
                "success": True,
                "message": "Context written to MCP successfully",
                "mcp_response": result.get("mcp_response")
            }
        else:
            logger.error(f"MCP write failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=f"MCP write failed: {result.get('error')}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ MCP context write error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/mcp/read-context/{session_id}")
async def read_mcp_context(session_id: str):
    """
    Read context data from MCP service
    Used by SuperAGI agents and n8n workflows
    """
    try:
        logger.info(f"📖 Reading MCP context for session: {session_id}")
        
        # Use the MCP integration service
        result = await mcp_service.read_context(session_id)
        
        if result.get("success"):
            return result.get("context") or {
                "success": False,
                "message": "Context not found",
                "session_id": session_id
            }
        else:
            logger.error(f"MCP read failed: {result.get('error')}")
            return {
                "success": False,
                "message": result.get("error", "MCP read failed"),
                "session_id": session_id
            }
        
    except Exception as e:
        logger.error(f"❌ MCP context read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mcp/append-context")
async def append_mcp_context(request: dict):
    """
    Append agent results to existing context in MCP service
    Used when SuperAGI or n8n agents complete tasks
    """
    try:
        session_id = request.get("session_id")
        output = request.get("output", {})
        source = request.get("source", "elva")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        logger.info(f"➕ Appending to MCP context for session: {session_id} from source: {source}")
        
        # Use the MCP integration service
        result = await mcp_service.append_context(
            session_id=session_id,
            output=output,
            source=source
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Context appended to MCP successfully",
                "mcp_response": result.get("mcp_response")
            }
        else:
            logger.error(f"MCP append failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=f"MCP append failed: {result.get('error')}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ MCP context append error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin Debug Endpoint for MCP Context Viewing
@api_router.get("/admin/debug/context/{session_id}")
async def admin_debug_context(
    session_id: str, 
    x_debug_token: Optional[str] = Header(None, alias="X-Debug-Token")
):
    """
    🔒 ADMIN ONLY: View MCP stored context for debugging
    Requires DEBUG_ADMIN_TOKEN in X-Debug-Token header
    """
    try:
        # Verify admin token
        expected_token = os.getenv("DEBUG_ADMIN_TOKEN")
        if not expected_token or x_debug_token != expected_token:
            logger.warning(f"🚨 Unauthorized admin debug attempt from IP: {session_id}")
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin token")
        
        logger.info(f"🔐 Admin debug context request for session: {session_id}")
        
        # Read context from MCP service
        result = await mcp_service.read_context(session_id)
        
        if not result.get("success"):
            return {
                "success": False,
                "message": f"Failed to read context: {result.get('error', 'Unknown error')}",
                "session_id": session_id
            }
        
        context_data = result.get("context")
        if not context_data:
            return {
                "success": True,
                "message": "No context found for this session",
                "session_id": session_id,
                "formatted_context": f"🧠 No stored context found for session: {session_id}"
            }
        
        # Format the context for readable display
        formatted_context = format_admin_context_display(session_id, context_data)
        
        return {
            "success": True,
            "session_id": session_id,
            "formatted_context": formatted_context,
            "raw_context": context_data,  # For detailed debugging if needed
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Admin debug context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/web-automation")
async def execute_web_automation(request: MCPContextRequest):
    """
    Execute web automation tasks using Playwright
    """
    try:
        automation_type = request.data.get("automation_type", "")
        logger.info(f"🌐 Web Automation Request: {automation_type}")
        
        result = None
        
        if automation_type == "web_scraping" or automation_type == "data_extraction":
            # Extract dynamic data from websites
            url = request.data.get("url")
            selectors = request.data.get("selectors", {})
            wait_for_element = request.data.get("wait_for_element")
            
            if not url or not selectors:
                raise HTTPException(status_code=400, detail="URL and selectors are required for web scraping")
            
            result = await playwright_service.extract_dynamic_data(url, selectors, wait_for_element)
            
        elif automation_type == "linkedin_insights":
            # LinkedIn insights will be handled via Gmail API integration in the future
            raise HTTPException(status_code=501, detail="LinkedIn insights temporarily disabled - Gmail API integration coming soon")
            
        elif automation_type == "email_automation":
            # Email automation will be handled via Gmail API
            raise HTTPException(status_code=501, detail="Email automation temporarily disabled - Gmail API integration coming soon")
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported automation type: {automation_type}")
        
        # Save automation result to database
        automation_record = {
            "id": str(uuid.uuid4()),
            "session_id": request.session_id,
            "automation_type": automation_type,
            "parameters": request.data,
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
                url=f'https://7c274570-5dc9-4f65-b14d-72a40eec87bc.preview.emergentagent.com/?auth=error&message={error}&session_id={session_id}',
                status_code=302
            )
        
        # Check for authorization code
        if not code:
            logger.error("❌ No authorization code received in OAuth callback")
            return RedirectResponse(
                url=f'https://7c274570-5dc9-4f65-b14d-72a40eec87bc.preview.emergentagent.com/?auth=error&message=no_code&session_id={session_id}',
                status_code=302
            )
        
        logger.info(f"✅ Processing OAuth callback with authorization code for session: {session_id}")
        
        # Handle OAuth callback with authorization code
        result = await gmail_oauth_service.handle_oauth_callback(code, session_id)
        
        logger.info(f"📊 OAuth callback result: success={result.get('success')}, authenticated={result.get('authenticated')}")
        
        if result.get("authenticated", False):
            logger.info(f"🎉 Gmail authentication successful for session {session_id} - redirecting to frontend")
            
            # IMMEDIATE STATUS REFRESH: Clear any cached auth status and force refresh
            await gmail_oauth_service.get_auth_status(session_id)  # This updates the cached status
            
            # Redirect to frontend with success parameter
            return RedirectResponse(
                url=f'https://7c274570-5dc9-4f65-b14d-72a40eec87bc.preview.emergentagent.com/?auth=success&service=gmail&session_id={session_id}&timestamp={int(datetime.utcnow().timestamp())}',
                status_code=302
            )
        else:
            error_msg = result.get('message', 'Authentication failed')
            logger.error(f"❌ Gmail authentication failed for session {session_id}: {error_msg}")
            return RedirectResponse(
                url=f'https://7c274570-5dc9-4f65-b14d-72a40eec87bc.preview.emergentagent.com/?auth=error&message=auth_failed&details={error_msg}&session_id={session_id}',
                status_code=302
            )
        
    except Exception as e:
        logger.error(f"💥 Gmail auth callback exception: {e}")
        # Redirect to frontend with error parameter
        return RedirectResponse(
            url=f'https://7c274570-5dc9-4f65-b14d-72a40eec87bc.preview.emergentagent.com/?auth=error&message=server_error&details={str(e)}&session_id={session_id if session_id else "unknown"}',
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

@api_router.get("/gmail/user-info")
async def gmail_user_info(session_id: str = None):
    """Get Gmail user information for admin detection"""
    try:
        if not session_id:
            # Try to extract from headers or use a default
            session_id = "default_session"
        
        # Check if user is authenticated
        status = await gmail_oauth_service.get_auth_status(session_id)
        if not status.get('authenticated'):
            return {
                "success": False,
                "error": "Not authenticated",
                "requires_auth": True
            }
        
        # Get user profile info from Gmail service
        user_info = await gmail_oauth_service.get_user_profile(session_id)
        
        if user_info and user_info.get('success'):
            return {
                "success": True,
                "email": user_info.get('email'),
                "name": user_info.get('name'),
                "session_id": session_id
            }
        else:
            return {
                "success": False,
                "error": "Failed to retrieve user info"
            }
            
    except Exception as e:
        logger.error(f"Gmail user info error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

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

@api_router.get("/gmail/user-info")
async def gmail_get_user_info(session_id: str = None):
    """Get authenticated user's Gmail profile information"""
    try:
        if not session_id:
            # Try to get from query params
            from fastapi import Request
            session_id = "default_session"
        
        # Check if user is authenticated
        auth_status = await gmail_oauth_service.get_auth_status(session_id)
        
        if not auth_status.get('authenticated'):
            return {
                "success": False,
                "error": "Gmail not authenticated",
                "requires_auth": True
            }
        
        # For now, return hardcoded admin emails since we know the system is for these users
        # In a real implementation, you'd get this from the Gmail API profile
        admin_emails = [
            'brainlyarpit8649@gmail.com',
            'kumararpit9468@gmail.com'
        ]
        
        # For this demo, return the first admin email as the authenticated user
        # In production, you'd call Gmail API to get actual user info
        return {
            "success": True,
            "email": admin_emails[0],  # Default to first admin email
            "name": "Admin User",
            "authenticated": True
        }
        
    except Exception as e:
        logger.error(f"Gmail user info error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@api_router.get("/admin/debug/context")
async def admin_debug_context(request: dict, token: str = Header(None, alias="x-debug-token")):
    """
    Admin Debug Toggle: View MCP-stored messages for debugging
    Commands: 'show my context' or 'show context for session <session_id>'
    """
    try:
        # Verify admin token
        if token != os.getenv("DEBUG_ADMIN_TOKEN", "elva-admin-debug-2024-secure"):
            raise HTTPException(status_code=403, detail="Invalid debug token")
        
        command = request.get('command', '').lower().strip()
        session_id = request.get('session_id')
        
        if not command:
            return {"error": "Missing command parameter"}
        
        # Parse command
        if command == "show my context":
            if not session_id:
                return {"error": "Session ID required for 'show my context' command"}
            target_session = session_id
        elif command.startswith("show context for session "):
            target_session = command.replace("show context for session ", "").strip()
            if not target_session:
                return {"error": "Invalid session ID in command"}
        else:
            return {"error": "Invalid command. Use 'show my context' or 'show context for session <session_id>'"}
        
        # Read context from MCP
        mcp_context = await mcp_service.read_context(target_session)
        
        if not mcp_context.get('success'):
            return {
                "success": False,
                "session_id": target_session,
                "error": "Failed to read MCP context",
                "details": mcp_context.get('error', 'Unknown error')
            }
        
        # Format the response for clean display in chat
        context_data = mcp_context.get('data', {})
        appends = mcp_context.get('appends', [])
        
        # Create a formatted response for chat display
        formatted_context = f"🔒 **Admin Debug: MCP Context for Session `{target_session}`**\n\n"
        
        # Add context summary
        formatted_context += f"📊 **Context Summary:**\n"
        formatted_context += f"• **Session ID:** {target_session}\n"
        formatted_context += f"• **Total Message History:** {len(appends)} entries\n"
        formatted_context += f"• **Last Updated:** {context_data.get('updated_at', 'Unknown')}\n\n"
        
        # Add initial context if available
        if context_data.get('context'):
            formatted_context += f"🎯 **Initial Context:**\n"
            initial_ctx = context_data.get('context', {})
            for key, value in initial_ctx.items():
                formatted_context += f"• **{key}:** {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}\n"
            formatted_context += "\n"
        
        # Add recent message history (last 5 entries)
        if appends:
            formatted_context += f"📝 **Recent Message History (Last {min(5, len(appends))} entries):**\n\n"
            for i, append in enumerate(appends[-5:], 1):
                formatted_context += f"**{i}.** **Agent:** {append.get('source', 'unknown')}\n"
                formatted_context += f"   **Time:** {append.get('timestamp', 'Unknown')}\n"
                
                output = append.get('output', {})
                if output.get('message'):
                    message = str(output.get('message', ''))[:200]
                    formatted_context += f"   **Message:** {message}{'...' if len(str(output.get('message', ''))) > 200 else ''}\n"
                
                if output.get('email_summary'):
                    formatted_context += f"   **Email Summary:** {str(output.get('email_summary', ''))[:100]}...\n"
                
                formatted_context += "\n"
        
        if not appends and not context_data.get('context'):
            formatted_context += "📝 **No message history found for this session.**\n"
        
        return {
            "success": True,
            "session_id": target_session,
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
        logger.error(f"Admin debug context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gmail/classification-stats")
async def get_gmail_classification_stats():
    """Get DeBERTa Gmail intent classification statistics and performance metrics"""
    try:
        stats = deberta_gmail_detector.get_classification_stats()
        
        return {
            "success": True,
            "message": "Gmail classification statistics retrieved successfully",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Gmail classification stats error: {e}")
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
        
        # Check MCP service health
        mcp_health = await mcp_service.health_check()
        
        # Get DeBERTa Gmail classifier stats
        deberta_stats = deberta_gmail_detector.get_classification_stats()
        
        health_status = {
            "status": "healthy",
            "mongodb": "connected",
            "mcp_integration": {
                "status": "enabled" if mcp_health.get("success") else "error",
                "service_url": mcp_service.mcp_base_url,
                "authentication": "configured" if mcp_service.mcp_api_token else "missing",
                "health_check": mcp_health,
                "features": [
                    "context_write", "context_read", "context_append",
                    "redis_caching", "mongodb_persistence", 
                    "session_management", "agent_result_storage"
                ],
                "endpoints": [
                    "/api/mcp/write-context",
                    "/api/mcp/read-context/{session_id}",
                    "/api/mcp/append-context"
                ]
            },
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
            "advanced_gmail_integration": {
                "version": "2.0_deberta_enhanced",
                "intent_detection": "DeBERTa-v3-base + HuggingFace Inference API",
                "fallback_model": "facebook/bart-large-mnli",
                "confidence_threshold": deberta_stats.get('confidence_threshold', 0.7),
                "supported_intents": deberta_stats.get('supported_intents', []),
                "real_data_fetching": "enabled",
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