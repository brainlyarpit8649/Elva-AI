# MCP (Model Context Protocol) Microservice
# FastAPI-based service for centralized context management

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os
import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from dotenv import load_dotenv
import uuid
import httpx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
MCP_API_TOKEN = os.getenv("MCP_API_TOKEN", "kumararpit9468")

# Backend URL for processing WhatsApp messages
ELVA_BACKEND_URL = os.getenv("ELVA_BACKEND_URL", "https://036e8f47-2d63-48b2-8d92-5307403f57fb.preview.emergentagent.com")

# Initialize FastAPI app
app = FastAPI(
    title="MCP (Model Context Protocol) Service",
    description="Centralized context management for Elva AI + SuperAGI integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connections
mongo_client = None
mongo_db = None
redis_client = None

# Redis settings
REDIS_TTL = 86400  # 24 hours
CONTEXT_PREFIX = "mcp:context:"
APPEND_PREFIX = "mcp:append:"

# Models
class ContextData(BaseModel):
    session_id: str
    user_id: str = "default_user"
    intent: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = REDIS_TTL

class AppendData(BaseModel):
    session_id: str
    output: Dict[str, Any]
    source: str = "superagi"  # superagi, elva, n8n
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ContextResponse(BaseModel):
    session_id: str
    context: Dict[str, Any]
    appends: List[Dict[str, Any]] = []
    total_appends: int = 0
    last_updated: datetime
    expires_at: Optional[datetime] = None

# Security dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify MCP API token"""
    if credentials.credentials != MCP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return credentials.credentials

# Database initialization
async def init_databases():
    """Initialize MongoDB and Redis connections"""
    global mongo_client, mongo_db, redis_client
    
    try:
        # MongoDB connection - use MCP-specific Atlas URL if available
        mongo_url = os.getenv("MCP_MONGO_URI") or os.getenv("MONGO_ATLAS_URL") or os.getenv("MONGO_URL", "mongodb://localhost:27017")
        mongo_client = AsyncIOMotorClient(mongo_url)
        db_name = os.getenv("MCP_DB_NAME", "elva_mcp")
        mongo_db = mongo_client[db_name]
        
        # Test MongoDB connection
        await mongo_client.admin.command('ping')
        logger.info(f"✅ MongoDB connected: {db_name}")
        
        # Redis connection - use MCP-specific Upstash URL if available
        redis_url = os.getenv("MCP_REDIS_URL") or os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Handle SSL connections for Upstash Redis
        if redis_url.startswith("rediss://"):
            redis_client = await redis.from_url(redis_url, decode_responses=True, ssl_cert_reqs=None)
        else:
            redis_client = await redis.from_url(redis_url, decode_responses=True)
        
        # Test Redis connection
        await redis_client.ping()
        logger.info(f"✅ Redis connected: {redis_url}")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize databases on startup"""
    await init_databases()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    if mongo_client:
        mongo_client.close()
    if redis_client:
        await redis_client.close()

# Core MCP Endpoints

@app.post("/context/write")
async def write_context(
    context_data: ContextData,
    token: str = Depends(verify_token)
):
    """
    Store full context (session_id, intent, emails, calendar, chat history)
    Uses Redis for fast access and MongoDB for persistence
    """
    try:
        context_key = f"{CONTEXT_PREFIX}{context_data.session_id}"
        
        # Prepare context document
        context_doc = {
            "session_id": context_data.session_id,
            "user_id": context_data.user_id,
            "intent": context_data.intent,
            "data": context_data.data,
            "timestamp": context_data.timestamp,
            "expires_at": context_data.timestamp + timedelta(seconds=context_data.ttl_seconds)
        }
        
        # Store in Redis with TTL
        await redis_client.setex(
            context_key,
            context_data.ttl_seconds,
            json.dumps(context_doc, default=str)
        )
        
        # Store in MongoDB for long-term persistence
        await mongo_db.mcp_contexts.replace_one(
            {"session_id": context_data.session_id},
            context_doc,
            upsert=True
        )
        
        logger.info(f"📝 Context written for session: {context_data.session_id}")
        
        return {
            "success": True,
            "message": "Context stored successfully",
            "session_id": context_data.session_id,
            "expires_at": context_doc["expires_at"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error writing context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/read/{session_id}")
async def read_context(
    session_id: str,
    token: str = Depends(verify_token)
) -> ContextResponse:
    """
    Read context for a given session with appended data
    Tries Redis first, falls back to MongoDB
    """
    try:
        context_key = f"{CONTEXT_PREFIX}{session_id}"
        append_key = f"{APPEND_PREFIX}{session_id}"
        
        # Try Redis first
        context_data = await redis_client.get(context_key)
        appended_data = await redis_client.lrange(append_key, 0, -1)
        
        if context_data:
            # Parse Redis data
            context = json.loads(context_data)
            appends = [json.loads(item) for item in appended_data] if appended_data else []
            
            logger.info(f"📖 Context read from Redis: {session_id}")
            
        else:
            # Fallback to MongoDB
            context = await mongo_db.mcp_contexts.find_one({"session_id": session_id})
            appends_cursor = mongo_db.mcp_appends.find({"session_id": session_id}).sort("timestamp", 1)
            appends = await appends_cursor.to_list(100)  # Limit to 100 appends
            
            if not context:
                raise HTTPException(status_code=404, detail="Context not found")
                
            logger.info(f"📖 Context read from MongoDB: {session_id}")
        
        return ContextResponse(
            session_id=session_id,
            context=context,
            appends=appends,
            total_appends=len(appends),
            last_updated=datetime.fromisoformat(context["timestamp"]) if isinstance(context["timestamp"], str) else context["timestamp"],
            expires_at=datetime.fromisoformat(context["expires_at"]) if isinstance(context.get("expires_at"), str) else context.get("expires_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error reading context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/context/append")
async def append_context(
    append_data: AppendData,
    token: str = Depends(verify_token)
):
    """
    Append new agent outputs or messages to existing context
    """
    try:
        append_key = f"{APPEND_PREFIX}{append_data.session_id}"
        
        # Prepare append document
        append_doc = {
            "id": str(uuid.uuid4()),
            "session_id": append_data.session_id,
            "output": append_data.output,
            "source": append_data.source,
            "timestamp": append_data.timestamp
        }
        
        # Add to Redis list
        await redis_client.lpush(append_key, json.dumps(append_doc, default=str))
        await redis_client.expire(append_key, REDIS_TTL)
        
        # Store in MongoDB
        await mongo_db.mcp_appends.insert_one(append_doc)
        
        logger.info(f"➕ Context appended for session: {append_data.session_id} from {append_data.source}")
        
        return {
            "success": True,
            "message": "Context appended successfully",
            "session_id": append_data.session_id,
            "append_id": append_doc["id"],
            "source": append_data.source
        }
        
    except Exception as e:
        logger.error(f"❌ Error appending context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional MCP Endpoints

@app.delete("/context/{session_id}")
async def delete_context(
    session_id: str,
    token: str = Depends(verify_token)
):
    """Delete context and all appends for a session"""
    try:
        context_key = f"{CONTEXT_PREFIX}{session_id}"
        append_key = f"{APPEND_PREFIX}{session_id}"
        
        # Delete from Redis
        await redis_client.delete(context_key, append_key)
        
        # Delete from MongoDB
        await mongo_db.mcp_contexts.delete_many({"session_id": session_id})
        await mongo_db.mcp_appends.delete_many({"session_id": session_id})
        
        logger.info(f"🗑️ Context deleted for session: {session_id}")
        
        return {
            "success": True,
            "message": "Context deleted successfully",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error deleting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contexts/list")
async def list_contexts(
    token: str = Depends(verify_token),
    limit: int = 50,
    skip: int = 0
):
    """List all active contexts"""
    try:
        # Get from MongoDB with pagination
        contexts = await mongo_db.mcp_contexts.find().skip(skip).limit(limit).sort("timestamp", -1).to_list(limit)
        
        return {
            "success": True,
            "contexts": contexts,
            "total": len(contexts),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test connections
        await mongo_client.admin.command('ping')
        await redis_client.ping()
        
        return {
            "status": "healthy",
            "service": "MCP (Model Context Protocol)",
            "version": "1.0.0",
            "databases": {
                "mongodb": "connected",
                "redis": "connected"
            },
            "endpoints": [
                "POST /context/write",
                "GET /context/read/{session_id}",
                "POST /context/append",
                "DELETE /context/{session_id}",
                "GET /contexts/list",
                "GET /health"
            ],
            "authentication": "Bearer token required",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# WhatsApp MCP Integration - Production Endpoint
@app.post("/api/mcp")
async def whatsapp_mcp_handler(
    request: dict,
    token: str = None,
    authorization: str = Header(None)
):
    """
    Production WhatsApp MCP Integration Handler
    Processes WhatsApp messages through Elva AI backend pipeline
    
    Supports token authentication via:
    - Query parameter: ?token=<TOKEN>
    - Authorization header: Bearer <TOKEN>
    
    Flexible payload formats:
    - {"session_id": "...", "message": "..."}
    - {"session_id": "...", "text": "..."}
    - {"session_id": "...", "query": "..."}
    """
    try:
        # Extract and validate authentication token
        auth_token = None
        
        # Check query parameter first (from request if available)
        if hasattr(request, 'query_params') and 'token' in request.query_params:
            auth_token = request.query_params.get('token')
        elif token:
            auth_token = token
        
        # Check Authorization header
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]  # Remove 'Bearer ' prefix
            else:
                auth_token = authorization
        
        # Validate token against environment variable
        if not auth_token or auth_token != MCP_API_TOKEN:
            logger.warning(f"🚫 WhatsApp MCP - Invalid token attempt")
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
        
        # Extract message with flexible field names
        session_id = request.get('session_id')
        message = (
            request.get('message') or 
            request.get('text') or 
            request.get('query') or 
            request.get('content') or
            ""
        )
        user_id = request.get('user_id', 'whatsapp_user')
        
        # Handle connection test cases - more flexible
        if not session_id and not message:
            logger.info("🔄 WhatsApp MCP - Empty payload connection test")
            return {
                "status": "ok", 
                "message": "MCP connection successful - ready for messages",
                "service": "WhatsApp MCP Integration",
                "platform": "whatsapp"
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
        
        # Forward to main Elva AI backend for processing
        try:
            backend_url = ELVA_BACKEND_URL
            
            chat_payload = {
                "message": message,
                "session_id": f"whatsapp_{session_id}",  # Prefix to distinguish WhatsApp sessions
                "user_id": user_id
            }
            
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{backend_url}/api/chat",
                    json=chat_payload,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    chat_response = response.json()
                    
                    # Store WhatsApp conversation in MCP context
                    context_data = {
                        "platform": "whatsapp",
                        "session_id": session_id,
                        "user_id": user_id,
                        "user_message": message,
                        "ai_response": chat_response.get("response", ""),
                        "intent_data": chat_response.get("intent_data", {}),
                        "needs_approval": chat_response.get("needs_approval", False),
                        "chat_history": [
                            {
                                "role": "user",
                                "content": message,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            {
                                "role": "assistant", 
                                "content": chat_response.get("response", ""),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        ]
                    }
                    
                    # Write to MCP context for session memory
                    context_key = f"{CONTEXT_PREFIX}whatsapp_{session_id}"
                    await redis_client.setex(
                        context_key,
                        REDIS_TTL,
                        json.dumps(context_data, default=str)
                    )
                    
                    # Store in MongoDB for persistence
                    await mongo_db.whatsapp_conversations.replace_one(
                        {"session_id": f"whatsapp_{session_id}"},
                        {
                            **context_data,
                            "timestamp": datetime.utcnow(),
                            "conversation_id": str(uuid.uuid4())
                        },
                        upsert=True
                    )
                    
                    logger.info(f"💾 WhatsApp context stored - Session: whatsapp_{session_id}")
                    
                    # Format response for WhatsApp/Puch AI
                    whatsapp_response = {
                        "success": True,
                        "status": "ok",
                        "session_id": session_id,
                        "message": chat_response.get("response", ""),
                        "intent": chat_response.get("intent_data", {}).get("intent", "general_chat"),
                        "needs_approval": chat_response.get("needs_approval", False),
                        "platform": "whatsapp",
                        "timestamp": chat_response.get("timestamp", datetime.utcnow().isoformat()),
                        "mcp_service": "elva-mcp-service.onrender.com"
                    }
                    
                    # Add special handling for Gmail and Weather intents
                    if chat_response.get("intent_data") and chat_response["intent_data"].get("intent") in ["check_gmail_inbox", "gmail_summary", "get_weather_forecast"]:
                        whatsapp_response["intent_data"] = {
                            "type": chat_response["intent_data"].get("intent"),
                            "confidence": chat_response["intent_data"].get("confidence", 0.8),
                            "data": chat_response["intent_data"]
                        }
                    
                    # Add approval workflow info if needed
                    if chat_response.get("needs_approval"):
                        whatsapp_response["approval_info"] = {
                            "required": True,
                            "intent": chat_response.get("intent_data", {}).get("intent"),
                            "message_id": chat_response.get("id"),
                            "approval_endpoint": f"{backend_url}/api/approve"
                        }
                    
                    logger.info(f"✅ WhatsApp MCP Response - Session: {session_id}, Intent: {whatsapp_response['intent']}")
                    return whatsapp_response
                    
                else:
                    logger.error(f"❌ Backend processing failed - Status: {response.status_code}")
                    raise HTTPException(
                        status_code=502,
                        detail={
                            "error": "backend_processing_failed",
                            "message": "Failed to process message through Elva AI backend",
                            "backend_status": response.status_code
                        }
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"⏱️ Backend processing timeout for session {session_id}")
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "processing_timeout",
                    "message": "Message processing timed out",
                    "session_id": session_id
                }
            )
        except Exception as backend_error:
            logger.error(f"💥 Backend communication error: {backend_error}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "backend_communication_failed",
                    "message": "Failed to communicate with Elva AI backend",
                    "details": str(backend_error)
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 WhatsApp MCP Handler Error: {e}")
        
        # Log error to MongoDB for debugging
        try:
            error_log = {
                "id": str(uuid.uuid4()),
                "platform": "whatsapp",
                "session_id": request.get('session_id', 'unknown') if isinstance(request, dict) else 'unknown',
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow()
            }
            await mongo_db.whatsapp_errors.insert_one(error_log)
        except:
            pass  # Don't fail if error logging fails
        
        # Return a more user-friendly error for connection issues
        return {
            "status": "error",
            "error": "processing_failed",
            "message": "Failed to process WhatsApp message, but MCP connection is working",
            "details": str(e),
            "session_id": request.get('session_id') if isinstance(request, dict) else None,
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/mcp")
async def whatsapp_mcp_connection_test(
    token: str = None,
    authorization: str = Header(None)
):
    """
    WhatsApp MCP Connection Test (GET)
    Handles GET requests from Puch AI for connection verification
    Returns simple status as required by Puch AI
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
        if not auth_token or auth_token != MCP_API_TOKEN:
            logger.warning(f"🚫 WhatsApp MCP GET - Invalid token attempt")
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "invalid_token",
                    "message": "Invalid or missing MCP API token"
                }
            )
        
        logger.info("🔄 WhatsApp MCP - GET connection test successful")
        
        # Return simple status as preferred by Puch AI
        return {
            "status": "ok",
            "message": "MCP server active"
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

@app.get("/api/mcp/health")
async def whatsapp_mcp_health():
    """WhatsApp MCP Health Check for Production"""
    try:
        # Test database connections
        await mongo_client.admin.command('ping')
        await redis_client.ping()
        
        # Test backend connectivity
        backend_url = ELVA_BACKEND_URL
        backend_healthy = False
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{backend_url}/api/health")
                backend_healthy = response.status_code == 200
        except:
            backend_healthy = False
        
        return {
            "status": "healthy",
            "service": "WhatsApp MCP Integration (Production)",
            "version": "1.0.0",
            "platform": "whatsapp",
            "deployment": "elva-mcp-service.onrender.com",
            "uptime": "24/7",
            "databases": {
                "mongodb": "connected",
                "redis": "connected"
            },
            "backend_connection": {
                "url": backend_url,
                "status": "connected" if backend_healthy else "disconnected"
            },
            "integrations": {
                "gmail": "ready",
                "weather": "ready", 
                "hybrid_ai": "ready",
                "mcp_context": "ready"
            },
            "endpoints": [
                "POST /api/mcp",
                "GET /api/mcp/health",
                "GET /api/mcp/sessions"
            ],
            "authentication": {
                "methods": ["query_parameter", "authorization_header"],
                "token_configured": bool(MCP_API_TOKEN),
                "example_usage": [
                    "POST /api/mcp?token=<TOKEN>",
                    "POST /api/mcp (with Authorization: Bearer <TOKEN>)"
                ]
            },
            "whatsapp_integration": {
                "puch_ai_compatible": True,
                "session_memory": True,
                "intent_detection": ["gmail", "weather", "general_chat"],
                "approval_workflows": True,
                "conversation_logging": True
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

@app.get("/api/mcp/sessions")
async def get_whatsapp_sessions(
    token: str = None,
    authorization: str = Header(None),
    limit: int = 20
):
    """Get recent WhatsApp conversation sessions"""
    try:
        # Validate token (same logic as main endpoint)
        auth_token = token
        if not auth_token and authorization:
            if authorization.startswith('Bearer '):
                auth_token = authorization[7:]
            else:
                auth_token = authorization
        
        if not auth_token or auth_token != MCP_API_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get recent WhatsApp sessions from MongoDB
        sessions = []
        cursor = mongo_db.whatsapp_conversations.find().sort([("timestamp", -1)]).limit(limit)
        async for session in cursor:
            # Convert ObjectId to string for JSON serialization
            session_data = {}
            for key, value in session.items():
                if hasattr(value, '__dict__') and hasattr(value, 'binary'):  # ObjectId
                    session_data[key] = str(value)
                else:
                    session_data[key] = value
            sessions.append(session_data)
        
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions),
            "platform": "whatsapp",
            "service": "elva-mcp-service.onrender.com"
        }
        
    except Exception as e:
        logger.error(f"❌ WhatsApp sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Puch AI Required Validation Endpoint
@app.post("/api/mcp/validate")
async def validate_tool(
    token: str = None,
    authorization: str = Header(None)
):
    """
    Puch AI Validation Endpoint
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
        if not auth_token or auth_token != MCP_API_TOKEN:
            logger.warning(f"🚫 Puch AI Validate - Invalid token attempt")
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "invalid_token",
                    "message": "Invalid or missing MCP API token"
                }
            )
        
        logger.info("✅ Puch AI Validation - Token verified successfully")
        
        # Return user's WhatsApp number as required by Puch AI
        return {
            "number": "919654030351"  # Country code (91) + phone number (9654030351)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Puch AI Validate Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "validation_failed",
                "message": "Validation endpoint error"
            }
        )

@app.get("/api/mcp/validate")  
async def validate_tool_get(
    token: str = None,
    authorization: str = Header(None)
):
    """
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
        if not auth_token or auth_token != MCP_API_TOKEN:
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

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "MCP (Model Context Protocol)",
        "description": "Centralized context management for Elva AI + SuperAGI integration",
        "version": "1.0.0",
        "whatsapp_integration": {
            "status": "production_ready",
            "endpoint": "/api/mcp",
            "health_check": "/api/mcp/health",
            "sessions": "/api/mcp/sessions",
            "puch_ai_validate": "/api/mcp/validate"
        },
        "documentation": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)