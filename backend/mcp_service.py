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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
MCP_API_TOKEN = os.getenv("MCP_API_TOKEN", "kumararpit9468")

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

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "MCP (Model Context Protocol)",
        "description": "Centralized context management for Elva AI + SuperAGI integration",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)