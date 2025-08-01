import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from gmail_oauth_service import GmailOAuthService
from deberta_gmail_intent_detector import deberta_gmail_detector

logger = logging.getLogger(__name__)

class RealTimeGmailService:
    """
    Real-time Gmail service that fetches actual Gmail data and formats responses
    No placeholder text - only real Gmail results with proper chat formatting
    """
    
    def __init__(self, gmail_oauth_service: GmailOAuthService):
        self.gmail_oauth = gmail_oauth_service
        self.detector = deberta_gmail_detector
    
    async def process_gmail_query(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """
        Process Gmail queries with DeBERTa intent detection and real Gmail data fetching
        Returns formatted responses ready for chat display
        """
        try:
            logger.info(f"🔍 Processing Gmail query: '{user_message}' for session: {session_id}")
            
            # STEP 1: DeBERTa Intent Classification
            intent_result = await self.detector.classify_intent(user_message)
            
            if not intent_result.get('is_gmail_intent'):
                # Not a Gmail intent - let Groq handle it
                return {
                    "success": True,
                    "is_gmail_query": False,
                    "requires_gmail_api": False,
                    "intent": "non_gmail",
                    "message": "Not a Gmail query - routing to general AI processing"
                }
            
            gmail_intent = intent_result.get('intent')
            confidence = intent_result.get('confidence')
            
            logger.info(f"🎯 Gmail Intent Detected: {gmail_intent} (confidence: {confidence:.1%})")
            
            # STEP 2: Check Gmail Authentication
            auth_status = await self.gmail_oauth.get_auth_status(session_id)
            
            if not auth_status.get('authenticated'):
                return {
                    "success": True,
                    "is_gmail_query": True,
                    "requires_gmail_api": True,
                    "requires_auth": True,
                    "intent": gmail_intent,
                    "message": "🔐 **Gmail Connection Required**\n\nTo access your Gmail, please click the 'Connect Gmail' button above to authenticate with Google.",
                    "formatted_response": "🔐 **Gmail Connection Required**\n\nTo access your Gmail, please click the 'Connect Gmail' button above to authenticate with Google."
                }
            
            # STEP 3: Fetch Real Gmail Data Based on Intent
            gmail_response = await self._fetch_gmail_data(gmail_intent, user_message, session_id)
            
            return {
                "success": True,
                "is_gmail_query": True,
                "requires_gmail_api": True,
                "requires_auth": False,
                "intent": gmail_intent,
                "confidence": confidence,
                "data": gmail_response.get('data', {}),
                "message": gmail_response.get('message', ''),
                "formatted_response": gmail_response.get('formatted_response', gmail_response.get('message', ''))
            }
            
        except Exception as e:
            logger.error(f"❌ Gmail query processing error: {e}")
            return {
                "success": False,
                "is_gmail_query": True,
                "requires_gmail_api": True,
                "error": str(e),
                "message": f"❌ **Gmail Error**\n\nSorry, I encountered an error while accessing your Gmail: {str(e)}"
            }
    
    async def _fetch_gmail_data(self, intent: str, user_message: str, session_id: str) -> Dict[str, Any]:
        """
        Fetch real Gmail data based on detected intent
        Returns formatted chat response with actual Gmail content
        """
        try:
            if intent == "gmail_inbox":
                return await self._get_inbox_summary(session_id)
            elif intent == "gmail_summary":
                return await self._get_email_summary(user_message, session_id)
            elif intent == "gmail_search":
                return await self._search_emails(user_message, session_id)
            elif intent == "gmail_unread":
                return await self._get_unread_emails(session_id)
            else:
                return {
                    "success": False,
                    "message": f"❌ **Unsupported Gmail Intent**\n\nI don't know how to handle the intent: {intent}"
                }
                
        except Exception as e:
            logger.error(f"❌ Gmail data fetch error for intent {intent}: {e}")
            return {
                "success": False,
                "message": f"❌ **Gmail API Error**\n\nFailed to fetch Gmail data: {str(e)}"
            }
    
    async def _get_inbox_summary(self, session_id: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Get Gmail inbox summary with real email data
        """
        try:
            result = await self.gmail_oauth.check_inbox(session_id, max_results=max_results, query='')
            
            if not result.get('success'):
                return {
                    "success": False,
                    "message": f"❌ **Inbox Access Failed**\n\n{result.get('message', 'Unable to access your inbox')}"
                }
            
            emails = result.get('data', {}).get('emails', [])
            total_count = result.get('data', {}).get('total_count', 0)
            
            if not emails:
                return {
                    "success": True,
                    "data": {"emails": [], "count": 0},
                    "message": "📭 **Your inbox is empty!**\n\nNo emails found in your Gmail inbox.",
                    "formatted_response": "📭 **Your inbox is empty!**\n\nNo emails found in your Gmail inbox."
                }
            
            # Format inbox summary for chat
            formatted_response = f"📧 **Your Gmail Inbox** ({total_count} messages)\n\n"
            
            for i, email in enumerate(emails[:10], 1):
                sender = self._extract_sender_name(email.get('from', 'Unknown'))
                subject = email.get('subject', 'No Subject')[:50]
                if len(email.get('subject', '')) > 50:
                    subject += "..."
                
                # Format timestamp
                timestamp = self._format_email_timestamp(email.get('date', ''))
                
                # Get snippet
                snippet = email.get('snippet', '')[:80]
                if len(email.get('snippet', '')) > 80:
                    snippet += "..."
                
                formatted_response += f"{i}️⃣ **{sender} – {subject}** ({timestamp})\n"
                if snippet:
                    formatted_response += f"   \"{snippet}\"\n\n"
                else:
                    formatted_response += "\n"
            
            formatted_response += "✅ That's your latest Gmail activity!"
            
            return {
                "success": True,
                "data": {"emails": emails, "count": total_count},
                "message": formatted_response,
                "formatted_response": formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Inbox summary error: {e}")
            return {
                "success": False,
                "message": f"❌ **Inbox Summary Failed**\n\nError accessing your inbox: {str(e)}"
            }
    
    async def _get_email_summary(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """
        Get summary of recent emails based on user request
        """
        try:
            # Extract number of emails to summarize (default 5)
            import re
            numbers = re.findall(r'\d+', user_message)
            count = int(numbers[0]) if numbers else 5
            count = min(count, 20)  # Limit to maximum 20
            
            result = await self.gmail_oauth.check_inbox(session_id, max_results=count, query='')
            
            if not result.get('success'):
                return {
                    "success": False,
                    "message": f"❌ **Email Summary Failed**\n\n{result.get('message', 'Unable to access your emails')}"
                }
            
            emails = result.get('data', {}).get('emails', [])
            
            if not emails:
                return {
                    "success": True,
                    "data": {"emails": [], "count": 0},
                    "message": "📭 **No emails to summarize**\n\nYour inbox appears to be empty.",
                    "formatted_response": "📭 **No emails to summarize**\n\nYour inbox appears to be empty."
                }
            
            # Format email summary
            actual_count = len(emails)
            formatted_response = f"📬 **Here's a quick summary of your last {actual_count} emails:**\n\n"
            
            for i, email in enumerate(emails, 1):
                sender = self._extract_sender_name(email.get('from', 'Unknown'))
                subject = email.get('subject', 'No Subject')
                timestamp = self._format_email_timestamp(email.get('date', ''))
                snippet = email.get('snippet', 'No preview available')[:100]
                if len(email.get('snippet', '')) > 100:
                    snippet += "..."
                
                formatted_response += f"{i}️⃣ **{sender} – {subject}** ({timestamp})\n"
                formatted_response += f"   \"{snippet}\"\n\n"
            
            formatted_response += f"✅ That's all from the last {actual_count} emails."
            
            return {
                "success": True,
                "data": {"emails": emails, "count": actual_count, "requested_count": count},
                "message": formatted_response,
                "formatted_response": formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Email summary error: {e}")
            return {
                "success": False,
                "message": f"❌ **Email Summary Failed**\n\nError creating summary: {str(e)}"
            }
    
    async def _search_emails(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """
        Search emails based on user query
        """
        try:
            # Extract search terms from user message
            search_query = self._extract_search_query(user_message)
            
            if not search_query:
                return {
                    "success": False,
                    "message": "❌ **Search Query Missing**\n\nI couldn't determine what to search for. Please specify what emails you're looking for."
                }
            
            result = await self.gmail_oauth.check_inbox(session_id, max_results=10, query=search_query)
            
            if not result.get('success'):
                return {
                    "success": False,
                    "message": f"❌ **Email Search Failed**\n\n{result.get('message', 'Unable to search your emails')}"
                }
            
            emails = result.get('data', {}).get('emails', [])
            search_used = result.get('data', {}).get('query_used', search_query)
            
            if not emails:
                return {
                    "success": True,
                    "data": {"emails": [], "count": 0, "search_query": search_used},
                    "message": f"🔍 **No results found**\n\nNo emails matching your search were found.\n\n**Search:** {search_used}",
                    "formatted_response": f"🔍 **No results found**\n\nNo emails matching your search were found.\n\n**Search:** {search_used}"
                }
            
            # Format search results
            search_term_display = self._extract_search_display_term(user_message)
            formatted_response = f"🔍 **Found {len(emails)} emails{f' from **{search_term_display}**' if search_term_display else ''}:**\n\n"
            
            for i, email in enumerate(emails, 1):
                sender = self._extract_sender_name(email.get('from', 'Unknown'))
                subject = email.get('subject', 'No Subject')
                timestamp = self._format_email_timestamp(email.get('date', ''))
                
                formatted_response += f"{i}️⃣ **{subject}** ({timestamp})\n"
                formatted_response += f"   From: {sender}\n\n"
            
            return {
                "success": True,
                "data": {"emails": emails, "count": len(emails), "search_query": search_used},
                "message": formatted_response,
                "formatted_response": formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Email search error: {e}")
            return {
                "success": False,
                "message": f"❌ **Email Search Failed**\n\nError searching emails: {str(e)}"
            }
    
    async def _get_unread_emails(self, session_id: str) -> Dict[str, Any]:
        """
        Get unread emails with count and details
        """
        try:
            result = await self.gmail_oauth.check_inbox(session_id, max_results=20, query='is:unread')
            
            if not result.get('success'):
                return {
                    "success": False,
                    "message": f"❌ **Unread Emails Check Failed**\n\n{result.get('message', 'Unable to check unread emails')}"
                }
            
            emails = result.get('data', {}).get('emails', [])
            unread_count = len(emails)
            
            if unread_count == 0:
                return {
                    "success": True,
                    "data": {"emails": [], "count": 0},
                    "message": "✅ **All caught up!**\n\nYou have no unread emails in your Gmail inbox.",
                    "formatted_response": "✅ **All caught up!**\n\nYou have no unread emails in your Gmail inbox."
                }
            
            # Format unread emails
            formatted_response = f"📨 **You have {unread_count} unread email{'s' if unread_count != 1 else ''}:**\n\n"
            
            for i, email in enumerate(emails[:10], 1):  # Show first 10 unread
                sender = self._extract_sender_name(email.get('from', 'Unknown'))
                subject = email.get('subject', 'No Subject')[:60]
                if len(email.get('subject', '')) > 60:
                    subject += "..."
                timestamp = self._format_email_timestamp(email.get('date', ''))
                
                formatted_response += f"{i}️⃣ **{sender} – {subject}** ({timestamp})\n"
            
            if unread_count > 10:
                formatted_response += f"\n... and {unread_count - 10} more unread emails.\n"
            
            formatted_response += f"\n📧 **Total unread:** {unread_count} messages"
            
            return {
                "success": True,
                "data": {"emails": emails, "count": unread_count},
                "message": formatted_response,
                "formatted_response": formatted_response
            }
            
        except Exception as e:
            logger.error(f"❌ Unread emails error: {e}")
            return {
                "success": False,
                "message": f"❌ **Unread Check Failed**\n\nError checking unread emails: {str(e)}"
            }
    
    def _extract_sender_name(self, from_field: str) -> str:
        """
        Extract clean sender name from email 'from' field
        """
        if not from_field:
            return "Unknown"
        
        # Handle "Name <email@domain.com>" format
        import re
        match = re.match(r'^(.+?)\s*<.+>$', from_field.strip())
        if match:
            name = match.group(1).strip().strip('"')
            return name if name else from_field.split('<')[0].strip()
        
        # Handle just email format
        if '@' in from_field:
            return from_field.split('@')[0].strip()
        
        return from_field.strip()
    
    def _format_email_timestamp(self, date_str: str) -> str:
        """
        Format email timestamp for chat display
        """
        if not date_str:
            return "Unknown time"
        
        try:
            # Parse common Gmail date formats
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            
            # Convert to local timezone for display
            now = datetime.now(timezone.utc)
            diff = now - dt.replace(tzinfo=timezone.utc)
            
            if diff.days == 0:
                # Today - show time
                return dt.strftime("Today, %I:%M %p")
            elif diff.days == 1:
                # Yesterday
                return dt.strftime("Yesterday, %I:%M %p")
            elif diff.days < 7:
                # This week
                return dt.strftime("%a, %I:%M %p")
            else:
                # Older
                return dt.strftime("%b %d, %I:%M %p")
                
        except Exception:
            # Fallback to original string
            return date_str[:20] if len(date_str) > 20 else date_str
    
    def _extract_search_query(self, user_message: str) -> str:
        """
        Extract Gmail search query from user message
        """
        message_lower = user_message.lower()
        
        # Look for "from" queries
        import re
        from_match = re.search(r'(?:from|emails from)\s+([a-zA-Z0-9@.\-_]+)', message_lower)
        if from_match:
            return f"from:{from_match.group(1)}"
        
        # Look for subject/content queries
        about_match = re.search(r'(?:about|containing|with)\s+([a-zA-Z0-9\s]+)', user_message)
        if about_match:
            search_term = about_match.group(1).strip()
            return f'"{search_term}"'
        
        # Look for specific sender names
        sender_patterns = [
            r'find emails from\s+([a-zA-Z\s]+)',
            r'search.*emails.*from\s+([a-zA-Z\s]+)',
            r'emails from\s+([a-zA-Z\s]+)'
        ]
        
        for pattern in sender_patterns:
            match = re.search(pattern, message_lower)
            if match:
                sender = match.group(1).strip()
                if sender and not any(word in sender for word in ['the', 'my', 'all', 'any']):
                    return f"from:{sender}"
        
        # Default search in subject and body
        words = user_message.replace('find', '').replace('search', '').replace('emails', '').strip()
        if len(words) > 3:
            return words
        
        return ""
    
    def _extract_search_display_term(self, user_message: str) -> Optional[str]:
        """
        Extract display term for search results (e.g., "Amazon", "John")
        """
        import re
        
        # Look for specific sender mentions
        from_match = re.search(r'(?:from|emails from)\s+([a-zA-Z0-9@.\-_]+)', user_message, re.IGNORECASE)
        if from_match:
            return from_match.group(1)
        
        return None

# This will be imported by the main enhanced Gmail service