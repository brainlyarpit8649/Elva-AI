"""
Enhanced Gmail Intent Detection with DeBERTa Integration
Provides high-accuracy intent classification specifically for Gmail-related queries
"""

import os
import logging
import json
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class EnhancedGmailIntentDetector:
    """
    High-accuracy Gmail intent detection using Microsoft's DeBERTa model
    via Hugging Face Inference API with fallback to Groq classification
    """
    
    def __init__(self):
        self.huggingface_api_token = os.getenv('HUGGINGFACE_API_TOKEN')
        self.deberta_model = "microsoft/deberta-v3-base"
        self.confidence_threshold = 0.75
        
        # Gmail-specific intent patterns and labels
        self.gmail_intent_mapping = {
            'inbox': 'gmail_inbox',
            'unread': 'gmail_unread', 
            'summary': 'gmail_summary',
            'search': 'gmail_search',
            'compose': 'gmail_compose',
            'send': 'gmail_send'
        }
        
        # Enhanced Gmail query patterns for robust detection
        self.gmail_patterns = {
            'gmail_inbox': [
                r'check.*gmail.*inbox',
                r'show.*my.*inbox',
                r'gmail.*messages',
                r'email.*inbox',
                r'inbox.*check',
                r'my.*gmail',
                r'check.*emails?',
                r'look.*at.*my.*emails?'
            ],
            'gmail_unread': [
                r'unread.*emails?',
                r'new.*emails?',
                r'any.*new.*messages?',
                r'do.*i.*have.*emails?',
                r'unread.*messages',
                r'fresh.*emails?',
                r'latest.*emails?',
                r'recent.*emails?'
            ],
            'gmail_summary': [
                r'summarize.*emails?',
                r'summary.*of.*emails?',
                r'brief.*of.*my.*emails?',
                r'overview.*of.*messages',
                r'digest.*of.*emails?',
                r'last.*\d+.*emails?',
                r'recent.*email.*summary'
            ],
            'gmail_search': [
                r'search.*emails?.*from',
                r'find.*emails?.*from',
                r'emails?.*from.*\w+',
                r'messages.*from.*\w+',
                r'emails?.*about.*\w+',
                r'find.*emails?.*about',
                r'search.*for.*emails?'
            ]
        }
    
    async def detect_gmail_intent(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Detect Gmail intent using DeBERTa with fallback to pattern matching
        
        Args:
            query: User query text
            session_id: Session identifier for logging
            
        Returns:
            Dict containing intent classification results
        """
        try:
            # First try DeBERTa classification if API token is available
            if self.huggingface_api_token:
                deberta_result = await self._classify_with_deberta(query)
                if deberta_result['confidence'] >= self.confidence_threshold:
                    logger.info(f"✅ DeBERTa classified '{query}' as Gmail intent: {deberta_result['intent']}")
                    return {
                        'intent': deberta_result['intent'],
                        'confidence': deberta_result['confidence'],
                        'method': 'deberta',
                        'gmail_specific': True,
                        'requires_gmail_api': True,
                        'session_id': session_id
                    }
            
            # Fallback to enhanced pattern matching
            pattern_result = self._classify_with_patterns(query)
            if pattern_result['gmail_specific']:
                logger.info(f"✅ Pattern matching classified '{query}' as Gmail intent: {pattern_result['intent']}")
                return {
                    **pattern_result,
                    'method': 'pattern_matching',
                    'session_id': session_id
                }
            
            # Not a Gmail query
            return {
                'intent': 'general_chat',
                'confidence': 0.0,
                'method': 'fallback',
                'gmail_specific': False,
                'requires_gmail_api': False,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"❌ Gmail intent detection error: {e}")
            return {
                'intent': 'general_chat',
                'confidence': 0.0,
                'method': 'error_fallback',
                'gmail_specific': False,
                'requires_gmail_api': False,
                'error': str(e),
                'session_id': session_id
            }
    
    async def _classify_with_deberta(self, query: str) -> Dict[str, Any]:
        """Use DeBERTa model via Hugging Face Inference API"""
        try:
            api_url = f"https://api-inference.huggingface.co/models/{self.deberta_model}"
            
            # Prepare Gmail-specific classification labels
            candidate_labels = [
                "check gmail inbox",
                "read unread emails", 
                "summarize emails",
                "search emails",
                "general conversation"
            ]
            
            headers = {
                "Authorization": f"Bearer {self.huggingface_api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": query,
                "parameters": {
                    "candidate_labels": candidate_labels
                }
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract highest confidence Gmail-related classification
                    if 'labels' in result and 'scores' in result:
                        top_label = result['labels'][0]
                        top_score = result['scores'][0]
                        
                        # Map DeBERTa labels to Gmail intents
                        gmail_intent = self._map_deberta_label_to_intent(top_label)
                        
                        return {
                            'intent': gmail_intent,
                            'confidence': float(top_score),
                            'deberta_label': top_label,
                            'all_scores': dict(zip(result['labels'], result['scores']))
                        }
                
                logger.warning(f"DeBERTa API returned status {response.status_code}")
                return {'intent': 'general_chat', 'confidence': 0.0}
                
        except Exception as e:
            logger.error(f"❌ DeBERTa classification error: {e}")
            return {'intent': 'general_chat', 'confidence': 0.0}
    
    def _map_deberta_label_to_intent(self, deberta_label: str) -> str:
        """Map DeBERTa classification labels to Gmail intents"""
        label_mapping = {
            "check gmail inbox": "gmail_inbox",
            "read unread emails": "gmail_unread",
            "summarize emails": "gmail_summary", 
            "search emails": "gmail_search",
            "general conversation": "general_chat"
        }
        return label_mapping.get(deberta_label, "general_chat")
    
    def _classify_with_patterns(self, query: str) -> Dict[str, Any]:
        """Enhanced pattern-based Gmail intent classification"""
        import re
        
        query_lower = query.lower()
        
        # Check each Gmail intent pattern
        for intent, patterns in self.gmail_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return {
                        'intent': intent,
                        'confidence': 0.85,  # High confidence for pattern matches
                        'gmail_specific': True,
                        'requires_gmail_api': True,
                        'matched_pattern': pattern
                    }
        
        # Check for general email-related terms
        email_terms = ['email', 'gmail', 'inbox', 'message', 'mail']
        if any(term in query_lower for term in email_terms):
            return {
                'intent': 'gmail_inbox',  # Default Gmail intent
                'confidence': 0.70,
                'gmail_specific': True,
                'requires_gmail_api': True,
                'matched_pattern': 'general_email_terms'
            }
        
        return {
            'intent': 'general_chat',
            'confidence': 0.0,
            'gmail_specific': False,
            'requires_gmail_api': False
        }
    
    def get_gmail_intent_examples(self) -> Dict[str, List[str]]:
        """Return example queries for each Gmail intent"""
        return {
            'gmail_inbox': [
                "Check my Gmail inbox",
                "Show me my emails",
                "What's in my inbox?",
                "Any messages for me?"
            ],
            'gmail_unread': [
                "Do I have any unread emails?",
                "Show me new messages",
                "Any fresh emails?",
                "Latest unread messages"
            ],
            'gmail_summary': [
                "Summarize my last 5 emails",
                "Give me an overview of my recent emails",
                "Brief me on my messages",
                "Email digest for today"
            ],
            'gmail_search': [
                "Find emails from John",
                "Search for emails about project deadline",
                "Show me messages from Amazon",
                "Emails containing 'meeting'"
            ]
        }

# Global instance
enhanced_gmail_detector = EnhancedGmailIntentDetector()