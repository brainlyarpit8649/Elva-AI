"""
MCP Integration Service for Elva AI Backend
Handles all communication with the MCP (Model Context Protocol) microservice
Replaces local memory storage with centralized context management
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MCPContextData(BaseModel):
    session_id: str
    user_id: str = "default_user"
    intent: str
    data: Dict[str, Any]
    timestamp: str = None

class MCPAppendData(BaseModel):
    session_id: str
    output: Dict[str, Any]
    source: str = "elva"  # elva, superagi, n8n

class MCPIntegrationService:
    """
    Centralized service for all MCP microservice interactions.
    Handles context writing, reading, and result appending.
    """
    
    def __init__(self):
        # MCP service configuration
        self.mcp_base_url = os.getenv("MCP_BASE_URL", "https://elva-mcp-service.onrender.com")
        self.mcp_api_token = os.getenv("MCP_API_TOKEN", "kumararpit9468")
        
        # HTTP client configuration
        self.timeout = 10.0  # 10 second timeout
        self.retry_attempts = 2
        
        logger.info(f"🔗 MCP Integration Service initialized - URL: {self.mcp_base_url}")
    
    async def write_context(
        self, 
        session_id: str, 
        intent: str, 
        data: Dict[str, Any], 
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Write context to MCP service after every user or AI message.
        
        Args:
            session_id: Unique session identifier
            intent: Detected intent or "general_chat"
            data: Context data including messages, AI responses, metadata
            user_id: User identifier
            
        Returns:
            MCP response with success status
        """
        try:
            context_data = MCPContextData(
                session_id=session_id,
                user_id=user_id,
                intent=intent,
                data=data,
                timestamp=datetime.utcnow().isoformat()
            )
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.mcp_base_url}/context/write",
                    json=context_data.dict(),
                    headers={"Authorization": f"Bearer {self.mcp_api_token}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📝 Context written to MCP - Session: {session_id}, Intent: {intent}")
                    return {"success": True, "mcp_response": result}
                else:
                    logger.error(f"❌ MCP write failed - Status: {response.status_code}, Response: {response.text}")
                    return {
                        "success": False, 
                        "error": f"MCP write failed with status {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.warning(f"⏱️ MCP write timeout for session {session_id}")
            return {"success": False, "error": "MCP write timeout"}
        except Exception as e:
            logger.error(f"❌ MCP write error for session {session_id}: {e}")
            return {"success": False, "error": str(e)}

    async def read_context(self, session_id: str) -> Dict[str, Any]:
        """
        Read context from MCP service before generating responses or triggering agents.
        Fetches complete conversation history and agent results.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Complete context data including history and appends
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.mcp_base_url}/context/read/{session_id}",
                    headers={"Authorization": f"Bearer {self.mcp_api_token}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📖 Context read from MCP - Session: {session_id}, Appends: {result.get('total_appends', 0)}")
                    return {"success": True, "context": result}
                elif response.status_code == 404:
                    logger.info(f"📭 No context found in MCP for session: {session_id}")
                    return {"success": True, "context": None, "message": "No context found"}
                else:
                    logger.error(f"❌ MCP read failed - Status: {response.status_code}, Response: {response.text}")
                    return {
                        "success": False, 
                        "error": f"MCP read failed with status {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.warning(f"⏱️ MCP read timeout for session {session_id}")
            return {"success": False, "error": "MCP read timeout"}
        except Exception as e:
            logger.error(f"❌ MCP read error for session {session_id}: {e}")
            return {"success": False, "error": str(e)}

    async def append_context(
        self, 
        session_id: str, 
        output: Dict[str, Any], 
        source: str = "elva"
    ) -> Dict[str, Any]:
        """
        Append agent results to existing context in MCP service.
        Called when SuperAGI or n8n agents complete tasks.
        
        Args:
            session_id: Unique session identifier
            output: Agent results or execution outputs
            source: Source of the append (elva, superagi, n8n)
            
        Returns:
            MCP response with append confirmation
        """
        try:
            append_data = MCPAppendData(
                session_id=session_id,
                output=output,
                source=source
            )
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.mcp_base_url}/context/append",
                    json=append_data.dict(),
                    headers={"Authorization": f"Bearer {self.mcp_api_token}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"➕ Context appended to MCP - Session: {session_id}, Source: {source}")
                    return {"success": True, "mcp_response": result}
                else:
                    logger.error(f"❌ MCP append failed - Status: {response.status_code}, Response: {response.text}")
                    return {
                        "success": False, 
                        "error": f"MCP append failed with status {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.warning(f"⏱️ MCP append timeout for session {session_id}")
            return {"success": False, "error": "MCP append timeout"}
        except Exception as e:
            logger.error(f"❌ MCP append error for session {session_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_context_for_prompt(self, session_id: str) -> str:
        """
        Get formatted context for including in AI prompts.
        Extracts conversation history and relevant context data.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Formatted context string for AI prompts
        """
        try:
            context_result = await self.read_context(session_id)
            
            if not context_result.get("success") or not context_result.get("context"):
                return "No previous conversation context available."
            
            context_data = context_result["context"]
            context_parts = []
            
            # Add session info
            context_parts.append(f"Session ID: {session_id}")
            context_parts.append(f"Last Updated: {context_data.get('last_updated', 'Unknown')}")
            
            # Add conversation history
            if "context" in context_data and "data" in context_data["context"]:
                chat_history = context_data["context"]["data"].get("chat_history", [])
                
                if chat_history:
                    context_parts.append("\n=== Conversation History ===")
                    for message in chat_history[-10:]:  # Last 10 messages
                        role = message.get("role", "unknown")
                        content = message.get("content", "")
                        timestamp = message.get("timestamp", "")
                        context_parts.append(f"{role.title()}: {content}")
            
            # Add agent results/appends
            appends = context_data.get("appends", [])
            if appends:
                context_parts.append("\n=== Agent Results ===")
                for append in appends[-5:]:  # Last 5 agent results
                    source = append.get("source", "unknown")
                    output = append.get("output", {})
                    context_parts.append(f"Source: {source}")
                    context_parts.append(f"Result: {json.dumps(output, indent=2)}")
                    context_parts.append("---")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"❌ Error formatting context for prompt: {e}")
            return f"Error retrieving context: {str(e)}"

    async def delete_context(self, session_id: str) -> Dict[str, Any]:
        """
        Delete all context data for a session (for cleanup operations).
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            MCP response with deletion confirmation
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.mcp_base_url}/context/{session_id}",
                    headers={"Authorization": f"Bearer {self.mcp_api_token}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"🗑️ Context deleted from MCP - Session: {session_id}")
                    return {"success": True, "mcp_response": result}
                else:
                    logger.error(f"❌ MCP delete failed - Status: {response.status_code}")
                    return {
                        "success": False, 
                        "error": f"MCP delete failed with status {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ MCP delete error for session {session_id}: {e}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """
        Check MCP service health and connectivity.
        
        Returns:
            Health status information
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.mcp_base_url}/health")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("✅ MCP service health check passed")
                    return {"success": True, "health": result}
                else:
                    logger.error(f"❌ MCP health check failed - Status: {response.status_code}")
                    return {
                        "success": False, 
                        "error": f"MCP health check failed with status {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ MCP health check error: {e}")
            return {"success": False, "error": str(e)}

    def prepare_context_data(
        self, 
        user_message: str, 
        ai_response: str, 
        intent_data: Dict[str, Any], 
        routing_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Prepare context data structure for MCP storage.
        
        Args:
            user_message: User's input message
            ai_response: AI's response message
            intent_data: Detected intent and associated data
            routing_info: AI routing decision information
            
        Returns:
            Structured context data for MCP
        """
        context_data = {
            "intent_data": intent_data,
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
            "chat_history": [
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "emails": [],  # To be populated by Gmail integration
            "calendar_events": []  # To be populated by calendar integration
        }
        
        # Add routing information if available
        if routing_info:
            context_data["routing_info"] = routing_info
            
        return context_data

# Global instance
mcp_service: Optional[MCPIntegrationService] = None

def initialize_mcp_service():
    """Initialize the global MCP integration service instance."""
    global mcp_service
    mcp_service = MCPIntegrationService()
    return mcp_service

def get_mcp_service() -> MCPIntegrationService:
    """Get the global MCP service instance."""
    if mcp_service is None:
        return initialize_mcp_service()
    return mcp_service