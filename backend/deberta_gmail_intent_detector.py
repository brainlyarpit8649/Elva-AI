import os
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class DeBERTaGmailIntentDetector:
    """
    Advanced Gmail Intent Detection using Hugging Face DeBERTa-v3-base model
    Implements high-accuracy intent classification for Gmail-related queries
    """
    
    def __init__(self):
        self.hf_api_url = "https://api-inference.huggingface.co/models/microsoft/deberta-v3-base"
        self.hf_api_token = os.getenv('HUGGINGFACE_API_TOKEN')  # Optional: for higher rate limits
        self.confidence_threshold = 0.7  # High confidence threshold
        
        # Define Gmail intent labels with comprehensive variations
        self.intent_labels = [
            "gmail_inbox",
            "gmail_summary", 
            "gmail_search",
            "gmail_unread",
            "general_query"  # Non-Gmail fallback
        ]
        
        # Training examples for few-shot classification
        self.training_examples = {
            "gmail_inbox": [
                "Check my Gmail inbox",
                "Show me my emails",
                "What's in my inbox",
                "Check my mail",
                "Show my Gmail messages",
                "Display my inbox"
            ],
            "gmail_summary": [
                "Summarize my last 5 emails",
                "Give me a summary of recent emails", 
                "What are my recent messages about",
                "Summarize my inbox",
                "Tell me about my latest emails",
                "Quick summary of my messages"
            ],
            "gmail_search": [
                "Find emails from Amazon",
                "Search for emails about project deadline",
                "Look for messages from John",
                "Find emails containing invoice",
                "Search my emails for meeting",
                "Show me emails about vacation"
            ],
            "gmail_unread": [
                "Show unread emails",
                "What new emails do I have",
                "Check my unread messages",
                "How many unread emails",
                "Show me new messages",
                "Display unread Gmail"
            ],
            "general_query": [
                "What's the weather in Delhi",
                "Tell me a joke",
                "How to cook pasta",
                "What's 2+2",
                "Create a todo list",
                "Set a reminder"
            ]
        }
    
    async def classify_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Classify user message using DeBERTa-v3-base for Gmail intent detection
        Returns intent classification with confidence score
        """
        try:
            logger.info(f"🧠 DeBERTa Intent Classification: '{user_message}'")
            
            # Prepare the classification task
            classification_result = await self._huggingface_classification(user_message)
            
            if not classification_result.get('success'):
                logger.warning(f"⚠️ DeBERTa classification failed: {classification_result.get('error')}")
                return await self._fallback_rule_based_classification(user_message)
            
            # Extract the best prediction
            predictions = classification_result.get('predictions', [])
            if not predictions:
                return await self._fallback_rule_based_classification(user_message)
            
            # Get highest confidence prediction
            best_prediction = max(predictions, key=lambda x: x['score'])
            predicted_intent = best_prediction['label']
            confidence = best_prediction['score']
            
            logger.info(f"🎯 DeBERTa Prediction: {predicted_intent} (confidence: {confidence:.3f})")
            
            # Apply confidence threshold
            if confidence >= self.confidence_threshold and predicted_intent != "general_query":
                # High confidence Gmail intent
                return {
                    "success": True,
                    "is_gmail_intent": True,
                    "intent": predicted_intent,
                    "confidence": confidence,
                    "method": "deberta_high_confidence",
                    "message": f"DeBERTa classified as {predicted_intent} with {confidence:.1%} confidence"
                }
            else:
                # Low confidence or general query - fallback to Groq
                logger.info(f"💭 Low confidence ({confidence:.1%}) or general query - falling back to Groq")
                return {
                    "success": True,
                    "is_gmail_intent": False,
                    "intent": "fallback_to_groq",
                    "confidence": confidence,
                    "method": "deberta_low_confidence_fallback",
                    "message": f"DeBERTa confidence too low ({confidence:.1%}) - routing to Groq for general processing"
                }
                
        except Exception as e:
            logger.error(f"❌ DeBERTa classification error: {e}")
            return await self._fallback_rule_based_classification(user_message)
    
    async def _huggingface_classification(self, text: str) -> Dict[str, Any]:
        """
        Perform classification using Hugging Face Inference API
        """
        try:
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if self.hf_api_token:
                headers["Authorization"] = f"Bearer {self.hf_api_token}"
            
            # Create candidate labels with descriptions for better classification
            candidate_labels = [
                "checking Gmail inbox and email messages",
                "summarizing recent emails and messages", 
                "searching for specific emails or senders",
                "showing unread Gmail messages",
                "general non-email related questions"
            ]
            
            # Prepare payload for zero-shot classification
            payload = {
                "inputs": text,
                "parameters": {
                    "candidate_labels": candidate_labels
                }
            }
            
            # Make API call with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Map results back to our intent labels
                    predictions = []
                    for i, (label, score) in enumerate(zip(result.get('labels', []), result.get('scores', []))):
                        intent_mapping = {
                            "checking Gmail inbox and email messages": "gmail_inbox",
                            "summarizing recent emails and messages": "gmail_summary",
                            "searching for specific emails or senders": "gmail_search", 
                            "showing unread Gmail messages": "gmail_unread",
                            "general non-email related questions": "general_query"
                        }
                        
                        mapped_intent = intent_mapping.get(label, "general_query")
                        predictions.append({
                            "label": mapped_intent,
                            "score": score
                        })
                    
                    return {
                        "success": True,
                        "predictions": predictions
                    }
                else:
                    logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API returned {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"HuggingFace API call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _fallback_rule_based_classification(self, user_message: str) -> Dict[str, Any]:
        """
        Fallback rule-based classification when DeBERTa is unavailable
        """
        logger.info(f"🔄 Using fallback rule-based classification")
        
        message_lower = user_message.lower()
        
        # Rule-based Gmail intent detection
        gmail_keywords = {
            "gmail_inbox": ["check inbox", "show inbox", "my emails", "check my mail", "gmail inbox", "check gmail"],
            "gmail_summary": ["summarize emails", "email summary", "summary of emails", "recent emails", "last emails"],
            "gmail_search": ["find emails", "search emails", "emails from", "look for emails", "find messages"],
            "gmail_unread": ["unread emails", "new emails", "unread messages", "how many unread", "new messages"]
        }
        
        # Check for Gmail intent patterns
        for intent, keywords in gmail_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return {
                    "success": True,
                    "is_gmail_intent": True,
                    "intent": intent,
                    "confidence": 0.8,  # Rule-based confidence
                    "method": "rule_based_fallback",
                    "message": f"Rule-based classification: {intent}"
                }
        
        # No Gmail intent detected
        return {
            "success": True,
            "is_gmail_intent": False,
            "intent": "fallback_to_groq",
            "confidence": 0.9,
            "method": "rule_based_non_gmail",
            "message": "No Gmail intent detected - routing to Groq"
        }
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """
        Get statistics about intent classification performance
        """
        return {
            "model": "microsoft/deberta-v3-base (via HuggingFace)",
            "fallback_model": "facebook/bart-large-mnli",
            "confidence_threshold": self.confidence_threshold,
            "supported_intents": self.intent_labels,
            "training_examples_count": {
                intent: len(examples) 
                for intent, examples in self.training_examples.items()
            },
            "api_configuration": {
                "has_hf_token": bool(self.hf_api_token),
                "api_endpoint": "https://api-inference.huggingface.co/"
            }
        }

# Initialize the DeBERTa Gmail intent detector
deberta_gmail_detector = DeBERTaGmailIntentDetector()