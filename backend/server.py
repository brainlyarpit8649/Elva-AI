from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List
from datetime import datetime

# Import our custom modules
from chat_models import ChatMessage, ChatMessageCreate, ChatMessageResponse, ChatSession
from intent_detection import detect_intent, format_intent_for_webhook
from webhook_handler import WebhookHandler

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize webhook handler
webhook_handler = WebhookHandler()

# Create the main app without a prefix
app = FastAPI(title="Elva AI Chat API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@api_router.get("/")
async def root():
    return {"message": "Elva AI Chat API is running"}

@api_router.post("/chat/message", response_model=ChatMessageResponse)
async def send_message(message_data: ChatMessageCreate):
    """
    Send a chat message and get AI response
    
    Flow:
    1. Save user message to database
    2. Detect intent using LangChain + Groq
    3. Send intent to n8n webhook
    4. Get response from webhook
    5. Save AI response to database
    6. Return AI response
    """
    try:
        # Save user message
        user_message = ChatMessage(
            session_id=message_data.session_id,
            user_id=message_data.user_id,
            message=message_data.message,
            sender="user"
        )
        await db.messages.insert_one(user_message.dict())
        
        # Detect intent
        logger.info(f"Detecting intent for message: {message_data.message}")
        intent_data = detect_intent(message_data.message)
        logger.info(f"Intent detected: {intent_data}")
        
        # Format payload for webhook
        webhook_payload = format_intent_for_webhook(
            intent_data, 
            message_data.user_id, 
            message_data.session_id
        )
        
        # Send to n8n webhook
        webhook_response = await webhook_handler.send_to_webhook(webhook_payload)
        
        # Create AI response message
        ai_response_text = "I've processed your request and sent it to the appropriate system."
        
        # If webhook returned a message, use that
        if webhook_response.get("message"):
            ai_response_text = webhook_response["message"]
        elif webhook_response.get("error"):
            ai_response_text = f"I encountered an issue: {webhook_response['error']}"
        
        # Save AI response
        ai_message = ChatMessage(
            session_id=message_data.session_id,
            user_id=message_data.user_id,
            message=ai_response_text,
            sender="ai",
            intent_data=intent_data,
            webhook_response=webhook_response
        )
        await db.messages.insert_one(ai_message.dict())
        
        # Update session activity
        await db.sessions.update_one(
            {"id": message_data.session_id},
            {
                "$set": {"last_activity": datetime.utcnow()},
                "$inc": {"message_count": 2}
            },
            upsert=True
        )
        
        return ChatMessageResponse(
            id=ai_message.id,
            session_id=ai_message.session_id,
            user_id=ai_message.user_id,
            message=ai_message.message,
            sender=ai_message.sender,
            timestamp=ai_message.timestamp,
            intent_data=intent_data
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@api_router.get("/chat/history/{session_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session"""
    try:
        messages = await db.messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).limit(limit).to_list(limit)
        
        return [
            ChatMessageResponse(
                id=msg["id"],
                session_id=msg["session_id"],
                user_id=msg["user_id"],
                message=msg["message"],
                sender=msg["sender"],
                timestamp=msg["timestamp"],
                intent_data=msg.get("intent_data")
            )
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting chat history: {str(e)}")

@api_router.post("/chat/session", response_model=ChatSession)
async def create_chat_session(user_id: str = "anonymous"):
    """Create a new chat session"""
    try:
        session = ChatSession(user_id=user_id)
        await db.sessions.insert_one(session.dict())
        return session
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@api_router.get("/chat/session/{session_id}", response_model=ChatSession)
async def get_chat_session(session_id: str):
    """Get chat session details"""
    try:
        session = await db.sessions.find_one({"id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return ChatSession(**session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting session: {str(e)}")

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
