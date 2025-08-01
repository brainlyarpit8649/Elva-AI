"""
Enhanced Chat Models with Support for User/AI Message Distinction
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class EnhancedChatMessage(BaseModel):
    """Enhanced chat message model that supports user/AI distinction"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str = "default_user"
    message: str = ""  # User input message
    response: str = ""  # AI response
    is_user: bool = False  # True for user messages, False for AI messages
    intent_data: Optional[dict] = None
    approved: Optional[bool] = None
    n8n_response: Optional[dict] = None
    is_system: bool = False  # For system messages
    is_welcome: bool = False  # For welcome messages
    is_edit: bool = False  # For edit messages
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserMessage(BaseModel):
    """Dedicated model for user messages"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str = "default_user"
    message: str
    is_user: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AIMessage(BaseModel):
    """Dedicated model for AI messages"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str = "default_user"
    response: str
    is_user: bool = False
    intent_data: Optional[dict] = None
    approved: Optional[bool] = None
    n8n_response: Optional[dict] = None
    is_system: bool = False
    is_welcome: bool = False
    is_edit: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class GmailActionRequest(BaseModel):
    """Request model for Gmail-specific actions"""
    session_id: str
    user_id: str = "default_user"
    action: str  # inbox, unread, summary, search
    query: Optional[str] = None  # For search queries
    limit: int = 10
    authenticated: bool = False

class GmailActionResponse(BaseModel):
    """Response model for Gmail API results"""
    success: bool
    action: str
    data: Optional[Dict[str, Any]] = None
    message: str
    requires_auth: bool = False
    formatted_response: str = ""
    session_id: str