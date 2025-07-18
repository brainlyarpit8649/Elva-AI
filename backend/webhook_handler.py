import requests
import logging
from typing import Dict, Any
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("N8N_WEBHOOK_URL not found in environment variables")
    
    async def send_to_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send data to n8n webhook and return response
        
        Args:
            payload: Data to send to webhook
            
        Returns:
            dict: Response from webhook
        """
        try:
            # Add timestamp to payload
            payload["timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Sending payload to webhook: {payload}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Elva-AI-Chat/1.0"
                }
            )
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                webhook_response = response.json()
                logger.info(f"Webhook response: {webhook_response}")
                return webhook_response
            except:
                # If not JSON, return text response
                return {
                    "message": response.text,
                    "status": "success"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Webhook request timed out")
            return {
                "error": "Webhook request timed out",
                "status": "timeout"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request failed: {str(e)}")
            return {
                "error": f"Webhook request failed: {str(e)}",
                "status": "error"
            }
        except Exception as e:
            logger.error(f"Unexpected error in webhook handler: {str(e)}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error"
            }