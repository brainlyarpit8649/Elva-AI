import os
import httpx
import logging
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()
logger = logging.getLogger(__name__)

# N8N webhook URL from environment
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://kumararpit8649.app.n8n.cloud/webhook/main-controller")

async def send_to_n8n(webhook_data: dict) -> dict:
    """
    Send approved action data to n8n webhook
    
    Args:
        webhook_data (dict): Formatted data to send to n8n
        
    Returns:
        dict: Response from n8n webhook or error information
    """
    try:
        logger.info(f"Sending data to n8n webhook: {N8N_WEBHOOK_URL}")
        logger.info(f"Webhook payload: {webhook_data}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                N8N_WEBHOOK_URL, 
                json=webhook_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Log response details
            logger.info(f"N8N webhook response status: {response.status_code}")
            logger.info(f"N8N webhook response headers: {response.headers}")
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                logger.info(f"N8N webhook response data: {response_data}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response_data
                }
            except Exception:
                # If response is not JSON, return text
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.text
                }
                
    except httpx.TimeoutException as e:
        error_msg = f"N8N webhook timeout: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": "timeout",
            "message": error_msg
        }
        
    except httpx.HTTPStatusError as e:
        error_msg = f"N8N webhook HTTP error {e.response.status_code}: {e.response.text}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": "http_error",
            "status_code": e.response.status_code,
            "message": error_msg
        }
        
    except Exception as e:
        error_msg = f"N8N webhook unexpected error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": "unexpected_error",
            "message": error_msg
        }

def validate_webhook_data(webhook_data: dict) -> bool:
    """
    Validate webhook data before sending to n8n
    
    Args:
        webhook_data (dict): Data to validate
        
    Returns:
        bool: True if data is valid, False otherwise
    """
    required_fields = ["user_id", "session_id", "intent", "data", "timestamp"]
    
    for field in required_fields:
        if field not in webhook_data:
            logger.error(f"Missing required field in webhook data: {field}")
            return False
    
    # Validate intent is one of the supported types
    supported_intents = ["send_email", "create_event", "add_todo", "set_reminder"]
    if webhook_data.get("intent") not in supported_intents:
        logger.error(f"Unsupported intent: {webhook_data.get('intent')}")
        return False
    
    return True

async def send_approved_action(intent_data: dict, user_id: str, session_id: str) -> dict:
    """
    High-level function to send approved action to n8n
    
    Args:
        intent_data (dict): Intent data from LLM
        user_id (str): User identifier
        session_id (str): Session identifier
        
    Returns:
        dict: Result of webhook call
    """
    from advanced_hybrid_ai import format_intent_for_webhook
    
    # Format data for webhook
    webhook_data = format_intent_for_webhook(intent_data, user_id, session_id)
    
    # Validate data
    if not validate_webhook_data(webhook_data):
        return {
            "success": False,
            "error": "validation_error",
            "message": "Invalid webhook data format"
        }
    
    # Send to n8n
    return await send_to_n8n(webhook_data)