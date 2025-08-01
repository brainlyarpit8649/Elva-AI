"""
Enhanced Gmail Service with Real Data Fetching (No Defaults/Placeholders)
Integrates with Gmail OAuth service to provide actual email data
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from gmail_oauth_service import GmailOAuthService
from enhanced_gmail_intent_detector import enhanced_gmail_detector

logger = logging.getLogger(__name__)

class EnhancedGmailService:
    """Enhanced Gmail service that ensures real data fetching with no placeholders"""
    
    def __init__(self, gmail_oauth_service: GmailOAuthService):
        self.gmail_oauth = gmail_oauth_service
        self.detector = enhanced_gmail_detector
    
    async def process_gmail_query(self, query: str, session_id: str) -> Dict[str, Any]:
        """
        Process Gmail query and return real email data (no placeholders)
        
        Args:
            query: User's Gmail-related query
            session_id: Session identifier
            
        Returns:
            Dict containing Gmail action results with real data
        """
        try:
            # Step 1: Detect Gmail intent with enhanced detection
            intent_result = await self.detector.detect_gmail_intent(query, session_id)
            
            if not intent_result['gmail_specific']:
                return {
                    'success': False,
                    'message': 'Not a Gmail-related query',
                    'intent': 'general_chat',
                    'requires_gmail_api': False
                }
            
            # Step 2: Check authentication status
            auth_status = await self.gmail_oauth.get_auth_status(session_id)
            if not auth_status.get('authenticated', False):
                return {
                    'success': False,
                    'message': '🔐 Please connect your Gmail account to access your emails.\n\nClick the "Connect Gmail" button above to authenticate.',
                    'intent': intent_result['intent'],
                    'requires_auth': True,
                    'requires_gmail_api': True,
                    'auth_url': '/api/gmail/auth'
                }
            
            # Step 3: Execute real Gmail API calls based on intent
            gmail_intent = intent_result['intent']
            
            if gmail_intent == 'gmail_inbox':
                return await self._fetch_inbox_emails(session_id, query)
            elif gmail_intent == 'gmail_unread':
                return await self._fetch_unread_emails(session_id, query)
            elif gmail_intent == 'gmail_summary':
                return await self._generate_email_summary(session_id, query)
            elif gmail_intent == 'gmail_search':
                return await self._search_emails(session_id, query)
            else:
                return await self._fetch_inbox_emails(session_id, query)  # Default to inbox
                
        except Exception as e:
            logger.error(f"❌ Gmail query processing error: {e}")
            return {
                'success': False,
                'message': f'Gmail service error: {str(e)}',
                'intent': 'gmail_error',
                'requires_gmail_api': False
            }
    
    async def _fetch_inbox_emails(self, session_id: str, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Fetch real inbox emails using Gmail API"""
        try:
            result = await self.gmail_oauth.check_inbox(
                session_id=session_id, 
                max_results=max_results, 
                query='in:inbox'
            )
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to fetch inbox emails'),
                    'requires_auth': result.get('requires_auth', False)
                }
            
            emails = result.get('data', {}).get('emails', [])
            
            if not emails:
                return {
                    'success': True,
                    'message': '✅ Your inbox is empty! No messages found.',
                    'intent': 'gmail_inbox',
                    'data': {'emails': [], 'count': 0},
                    'formatted_response': '✅ Your inbox is empty! No messages found.'
                }
            
            # Format real email data for display
            formatted_response = self._format_email_list(emails, "📥 Your Gmail Inbox")
            
            return {
                'success': True,
                'message': f'Retrieved {len(emails)} emails from your inbox',
                'intent': 'gmail_inbox',
                'data': {'emails': emails, 'count': len(emails)},
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Inbox fetch error: {e}")
            return {
                'success': False,
                'message': f'Failed to fetch inbox: {str(e)}',
                'intent': 'gmail_inbox'
            }
    
    async def _fetch_unread_emails(self, session_id: str, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Fetch real unread emails using Gmail API"""
        try:
            result = await self.gmail_oauth.check_inbox(
                session_id=session_id, 
                max_results=max_results, 
                query='is:unread'
            )
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to fetch unread emails'),
                    'requires_auth': result.get('requires_auth', False)
                }
            
            emails = result.get('data', {}).get('emails', [])
            
            if not emails:
                return {
                    'success': True,
                    'message': '✅ No unread emails! Your inbox is all caught up.',
                    'intent': 'gmail_unread',
                    'data': {'emails': [], 'count': 0},
                    'formatted_response': '✅ No unread emails! Your inbox is all caught up.'
                }
            
            # Format real unread email data
            formatted_response = self._format_email_list(emails, f"📬 You have {len(emails)} unread email{'s' if len(emails) != 1 else ''}")
            
            return {
                'success': True,
                'message': f'Found {len(emails)} unread emails',
                'intent': 'gmail_unread',
                'data': {'emails': emails, 'count': len(emails)},
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Unread fetch error: {e}")
            return {
                'success': False,
                'message': f'Failed to fetch unread emails: {str(e)}',
                'intent': 'gmail_unread'
            }
    
    async def _generate_email_summary(self, session_id: str, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Generate real email summary from recent emails"""
        try:
            # Extract number from query if specified (e.g., "last 5 emails")
            import re
            num_match = re.search(r'(\d+)', query)
            if num_match:
                max_results = min(int(num_match.group(1)), 20)  # Cap at 20
            
            result = await self.gmail_oauth.check_inbox(
                session_id=session_id, 
                max_results=max_results, 
                query='in:inbox'
            )
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to fetch emails for summary'),
                    'requires_auth': result.get('requires_auth', False)
                }
            
            emails = result.get('data', {}).get('emails', [])
            
            if not emails:
                return {
                    'success': True,
                    'message': '✅ No emails to summarize. Your inbox is empty.',
                    'intent': 'gmail_summary',
                    'data': {'emails': [], 'count': 0},
                    'formatted_response': '✅ No emails to summarize. Your inbox is empty.'
                }
            
            # Generate summary from real email data
            summary_response = self._generate_smart_summary(emails, max_results)
            
            return {
                'success': True,
                'message': f'Generated summary of {len(emails)} recent emails',
                'intent': 'gmail_summary',
                'data': {'emails': emails, 'count': len(emails), 'summary': summary_response},
                'formatted_response': summary_response
            }
            
        except Exception as e:
            logger.error(f"❌ Email summary error: {e}")
            return {
                'success': False,
                'message': f'Failed to generate email summary: {str(e)}',
                'intent': 'gmail_summary'
            }
    
    async def _search_emails(self, session_id: str, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search emails based on query criteria"""
        try:
            # Extract search terms from query
            search_query = self._extract_search_query(query)
            
            result = await self.gmail_oauth.check_inbox(
                session_id=session_id, 
                max_results=max_results, 
                query=search_query
            )
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to search emails'),
                    'requires_auth': result.get('requires_auth', False)
                }
            
            emails = result.get('data', {}).get('emails', [])
            
            if not emails:
                return {
                    'success': True,
                    'message': f'🔍 No emails found matching: "{search_query}"',
                    'intent': 'gmail_search',
                    'data': {'emails': [], 'count': 0, 'search_query': search_query},
                    'formatted_response': f'🔍 No emails found matching: "{search_query}"'
                }
            
            # Format search results
            formatted_response = self._format_email_list(emails, f"🔍 Found {len(emails)} email{'s' if len(emails) != 1 else ''} matching: \"{search_query}\"")
            
            return {
                'success': True,
                'message': f'Found {len(emails)} emails matching search criteria',
                'intent': 'gmail_search',
                'data': {'emails': emails, 'count': len(emails), 'search_query': search_query},
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Email search error: {e}")
            return {
                'success': False,
                'message': f'Failed to search emails: {str(e)}',
                'intent': 'gmail_search'
            }
    
    def _format_email_list(self, emails: List[Dict], header: str) -> str:
        """Format email list for display - returns raw text for ChatBox.js renderEmailDisplay"""
        if not emails:
            return "✅ No emails found."
        
        # Use the format that ChatBox.js expects for email rendering
        formatted = f"{header}\n\n"
        
        for i, email in enumerate(emails, 1):
            sender = email.get('from', 'Unknown Sender')
            subject = email.get('subject', 'No Subject')
            date = email.get('date', 'Unknown Date')
            snippet = email.get('snippet', '').strip()
            
            # Format each email with the pattern ChatBox.js recognizes
            formatted += f"**{i}.**\n"
            formatted += f"**From:** {sender}\n"
            formatted += f"**Subject:** {subject}\n"
            formatted += f"**Received:** {date}\n"
            if snippet:
                formatted += f"**Snippet:** \"{snippet}\"\n"
            formatted += "\n"
        
        return formatted.strip()
    
    def _generate_smart_summary(self, emails: List[Dict], count: int) -> str:
        """Generate intelligent summary of emails"""
        if not emails:
            return "✅ No emails to summarize."
        
        summary = f"📊 **Summary of Your Last {count} Email{'s' if count != 1 else ''}**\n\n"
        
        # Categorize emails by sender domain
        domains = {}
        for email in emails:
            sender = email.get('from', '')
            if '@' in sender:
                domain = sender.split('@')[-1].split('>')[0].strip()
                domains[domain] = domains.get(domain, 0) + 1
        
        # Add summary statistics
        if domains:
            top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:3]
            summary += f"**Top Senders:** {', '.join([f'{domain} ({count})' for domain, count in top_domains])}\n\n"
        
        # List recent emails with summary
        summary += "**Recent Messages:**\n"
        for i, email in enumerate(emails[:count], 1):
            sender = email.get('from', 'Unknown')
            subject = email.get('subject', 'No Subject')
            snippet = email.get('snippet', '')[:50] + "..." if len(email.get('snippet', '')) > 50 else email.get('snippet', '')
            
            summary += f"{i}️⃣ **{sender.split('<')[0].strip()}** - {subject}\n"
            if snippet:
                summary += f"   ↳ {snippet}\n"
            summary += "\n"
        
        return summary.strip()
    
    def _extract_search_query(self, user_query: str) -> str:
        """Extract Gmail search query from user input"""
        import re
        
        user_query_lower = user_query.lower()
        
        # Extract "from" searches
        from_match = re.search(r'from\s+(\w+)', user_query_lower)
        if from_match:
            return f"from:{from_match.group(1)}"
        
        # Extract "about" searches
        about_match = re.search(r'about\s+(["\']?)([^"\']+)\1', user_query_lower)
        if about_match:
            return f'"{about_match.group(2)}"'
        
        # Extract quoted searches
        quoted_match = re.search(r'["\']([^"\']+)["\']', user_query)
        if quoted_match:
            return f'"{quoted_match.group(1)}"'
        
        # Extract keyword searches
        keywords = ['project', 'meeting', 'deadline', 'report', 'update', 'invoice', 'order']
        for keyword in keywords:
            if keyword in user_query_lower:
                return keyword
        
        # Default to general search
        return 'in:inbox'