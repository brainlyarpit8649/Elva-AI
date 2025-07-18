from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str = Field(default="anonymous")
    message: str
    sender: str  # "user" or "ai"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    intent_data: Optional[dict] = None
    webhook_response: Optional[dict] = None

class ChatMessageCreate(BaseModel):
    session_id: str
    user_id: str = Field(default="anonymous")
    message: str

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    message: str
    sender: str
    timestamp: datetime
    intent_data: Optional[dict] = None

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(default="anonymous")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0

class WebhookPayload(BaseModel):
    user_id: str
    session_id: str
    intent: str
    data: dict
    timestamp: datetime