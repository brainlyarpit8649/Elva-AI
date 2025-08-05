import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# MongoDB imports
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class GmailOAuthService:
    """
    Gmail API service with OAuth2 authentication
    Handles authentication, email reading, sending, and management with session-based token storage
    """
    
    def __init__(self, db=None):
        self.credentials = None
        self.service = None
        self.current_session_id = None  # Track current session
        self.db = db  # MongoDB database connection
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        
        # Load credentials configuration
        self.credentials_file_path = Path(__file__).parent / 'credentials.json'
        
        # OAuth2 configuration from environment
        self.redirect_uri = os.getenv('GMAIL_REDIRECT_URI', 'https://0fbf6255-bf7b-4ad7-b4ea-c5da62fa1669.preview.emergentagent.com/api/gmail/callback')
        
    def _load_credentials_config(self) -> Dict[str, Any]:
        """Load OAuth2 credentials configuration from credentials.json"""
        try:
            if not self.credentials_file_path.exists():
                logger.warning("⚠️ Gmail credentials.json not found. Please add it to enable Gmail API integration.")
                return None
                
            with open(self.credentials_file_path, 'r') as f:
                credentials_config = json.load(f)
                
            if 'web' in credentials_config:
                return credentials_config['web']
            elif 'installed' in credentials_config:
                return credentials_config['installed']
            else:
                logger.error("❌ Invalid credentials.json format")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error loading credentials.json: {e}")
            return None
    
    async def _save_token(self, credentials: Credentials, session_id: str):
        """Save OAuth2 token to MongoDB with both session and user-global storage"""
        try:
            if self.db is None:
                logger.error("❌ No database connection available for token storage")
                return
                
            user_id = f'session_{session_id}' if session_id else 'default_user'
            
            token_data = {
                'session_id': session_id,
                'user_id': user_id,
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'service': 'gmail'
            }
            
            # Save session-specific token
            await self.db.oauth_tokens.update_one(
                {'session_id': session_id, 'service': 'gmail'},
                {'$set': token_data},
                upsert=True
            )
            
            # Also save as global user token for persistence across sessions
            global_token_data = {**token_data, 'is_global': True, 'session_id': 'global'}
            await self.db.oauth_tokens.update_one(
                {'user_id': user_id, 'service': 'gmail', 'is_global': True},
                {'$set': global_token_data},
                upsert=True
            )
            
            logger.info(f"✅ Gmail OAuth2 token saved for session: {session_id} and globally for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving OAuth2 token: {e}")
    
    async def _load_token(self, session_id: str) -> Optional[Credentials]:
        """Load OAuth2 token from MongoDB with fallback to global user token"""
        try:
            if self.db is None:
                logger.error("❌ No database connection available for token loading")
                return None
            
            user_id = f'session_{session_id}' if session_id else 'default_user'
            
            # First, try to load session-specific token
            token_record = await self.db.oauth_tokens.find_one({
                'session_id': session_id,
                'service': 'gmail'
            })
            
            # If no session-specific token, try global user token
            if not token_record:
                token_record = await self.db.oauth_tokens.find_one({
                    'user_id': user_id,
                    'service': 'gmail',
                    'is_global': True
                })
                
                if token_record:
                    logger.info(f"ℹ️ Using global Gmail token for session: {session_id}")
            
            if not token_record:
                logger.info(f"ℹ️ No Gmail token found for session: {session_id} or user: {user_id}")
                return None
            
            credentials = Credentials(
                token=token_record.get('token'),
                refresh_token=token_record.get('refresh_token'),
                token_uri=token_record.get('token_uri'),
                client_id=token_record.get('client_id'),
                client_secret=token_record.get('client_secret'),
                scopes=token_record.get('scopes')
            )
            
            # Set expiry if available
            if token_record.get('expiry'):
                credentials.expiry = datetime.fromisoformat(token_record['expiry'])
            
            logger.info(f"✅ Gmail token loaded successfully for session: {session_id}")
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error loading OAuth2 token: {e}")
            return None
    
    def get_auth_url(self) -> Dict[str, str]:
        """Get OAuth2 authentication URL for user authorization"""
        try:
            credentials_config = self._load_credentials_config()
            if not credentials_config:
                return {
                    'success': False,
                    'message': 'Gmail credentials.json not configured'
                }
            
            flow = Flow.from_client_config(
                {'web': credentials_config},
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            return {
                'success': True,
                'auth_url': auth_url,
                'message': 'OAuth2 authorization URL generated successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating auth URL: {e}")
            return {
                'success': False,
                'message': f'Failed to generate auth URL: {str(e)}'
            }
    
    async def handle_oauth_callback(self, authorization_code: str, session_id: str) -> Dict[str, Any]:
        """Handle OAuth2 callback and exchange code for credentials"""
        try:
            credentials_config = self._load_credentials_config()
            if not credentials_config:
                return {
                    'success': False,
                    'authenticated': False,
                    'message': 'Gmail credentials.json not configured'
                }
            
            flow = Flow.from_client_config(
                {'web': credentials_config},
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=authorization_code)
            
            self.credentials = flow.credentials
            self.current_session_id = session_id
            await self._save_token(self.credentials, session_id)
            
            # Initialize Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            
            return {
                'success': True,
                'authenticated': True,
                'message': 'Gmail OAuth2 authentication completed successfully',
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"❌ OAuth2 callback error: {e}")
            return {
                'success': False,
                'authenticated': False,
                'message': f'OAuth2 authentication failed: {str(e)}'
            }
    
    async def _authenticate(self, session_id: str) -> bool:
        """Authenticate with Gmail API using stored or refreshed credentials for specific session"""
        try:
            # Set current session
            self.current_session_id = session_id
            
            # Try to load existing credentials for this session
            if not self.credentials or self.current_session_id != session_id:
                self.credentials = await self._load_token(session_id)
            
            if not self.credentials:
                logger.info(f"ℹ️ No Gmail credentials found for session {session_id}. OAuth2 flow required.")
                return False
            
            # Refresh credentials if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                await self._save_token(self.credentials, session_id)
                logger.info(f"🔄 Gmail credentials refreshed successfully for session: {session_id}")
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info(f"✅ Gmail authentication successful for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Gmail authentication failed for session {session_id}: {e}")
            return False
    
    async def check_inbox(self, session_id: str, max_results: int = 10, query: str = 'is:unread') -> Dict[str, Any]:
        """Check Gmail inbox and return email list for specific session"""
        try:
            if not await self._authenticate(session_id):
                return {
                    'success': False,
                    'message': 'Gmail authentication required. Please complete OAuth2 flow.',
                    'requires_auth': True,
                    'session_id': session_id
                }
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', 
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = msg.get('payload', {}).get('headers', [])
                email_data = {
                    'id': message['id'],
                    'thread_id': msg.get('threadId'),
                    'snippet': msg.get('snippet', ''),
                    'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date'),
                    'labels': msg.get('labelIds', [])
                }
                email_list.append(email_data)
            
            return {
                'success': True,
                'data': {
                    'emails': email_list,
                    'total_count': len(email_list),
                    'query_used': query
                },
                'message': f'Successfully retrieved {len(email_list)} emails'
            }
            
        except HttpError as e:
            logger.error(f"❌ Gmail API error: {e}")
            return {
                'success': False,
                'message': f'Gmail API error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ Inbox check error: {e}")
            return {
                'success': False,
                'message': f'Failed to check inbox: {str(e)}'
            }
    
    def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        sender_email: str = None,
        cc: str = None,
        bcc: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Send email using Gmail API"""
        try:
            if not session_id:
                session_id = self.current_session_id or 'default_session'
                
            # Use async authentication check
            import asyncio
            if not asyncio.run(self._authenticate(session_id)):
                return {
                    'success': False,
                    'message': 'Gmail authentication required. Please complete OAuth2 flow.',
                    'requires_auth': True
                }
            
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if sender_email:
                message['from'] = sender_email
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            send_result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'success': True,
                'data': {
                    'message_id': send_result['id'],
                    'thread_id': send_result.get('threadId'),
                    'to': to,
                    'subject': subject
                },
                'message': f'Email sent successfully to {to}'
            }
            
        except HttpError as e:
            logger.error(f"❌ Gmail send error: {e}")
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ Email send error: {e}")
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }
    
    def get_email_content(self, message_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get full email content by message ID"""
        try:
            if not session_id:
                session_id = self.current_session_id or 'default_session'
                
            # Use async authentication check
            import asyncio
            if not asyncio.run(self._authenticate(session_id)):
                return {
                    'success': False,
                    'message': 'Gmail authentication required. Please complete OAuth2 flow.',
                    'requires_auth': True
                }
            
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract email content
            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'snippet': message.get('snippet', ''),
                'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                'to': next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown'),
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date'),
                'body': self._extract_body(payload),
                'labels': message.get('labelIds', [])
            }
            
            return {
                'success': True,
                'data': email_data,
                'message': 'Email content retrieved successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting email content: {e}")
            return {
                'success': False,
                'message': f'Failed to get email content: {str(e)}'
            }
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with Gmail API"""
        return self._authenticate()
    
    async def get_auth_status(self, session_id: str = None) -> Dict[str, Any]:
        """Get Gmail authentication status with enhanced session and user-global token checking"""
        try:
            credentials_configured = self._load_credentials_config() is not None
            
            if session_id:
                # Check if we have valid credentials for this session or user
                credentials = await self._load_token(session_id)
                authenticated = credentials is not None
                
                # If credentials exist, check if they're still valid
                if authenticated and credentials:
                    try:
                        if credentials.expired and credentials.refresh_token:
                            credentials.refresh(Request())
                            await self._save_token(credentials, session_id)
                            logger.info(f"🔄 Refreshed expired Gmail credentials for session: {session_id}")
                        
                        # Try to build service to verify credentials work
                        service = build('gmail', 'v1', credentials=credentials)
                        
                        # Test with a simple API call
                        profile = service.users().getProfile(userId='me').execute()
                        authenticated = True
                        logger.info(f"✅ Gmail credentials verified for session: {session_id}, email: {profile.get('emailAddress', 'unknown')}")
                        
                    except Exception as e:
                        logger.warning(f"Gmail credentials invalid for session {session_id}: {e}")
                        authenticated = False
                        
                        # Clean up invalid tokens
                        if self.db is not None:
                            await self.db.oauth_tokens.delete_many({
                                '$or': [
                                    {'session_id': session_id, 'service': 'gmail'},
                                    {'user_id': f'session_{session_id}', 'service': 'gmail', 'is_global': True}
                                ]
                            })
                            logger.info(f"🧹 Cleaned up invalid tokens for session: {session_id}")
            else:
                authenticated = False
                
                # For health checks, try to find any valid tokens
                if self.db is not None:
                    try:
                        token_count = await self.db.oauth_tokens.count_documents({'service': 'gmail'})
                        if token_count > 0:
                            logger.info(f"📊 Found {token_count} Gmail tokens in database")
                    except Exception as e:
                        logger.error(f"Error counting tokens: {e}")
            
            return {
                'success': True,
                'credentials_configured': credentials_configured,
                'authenticated': authenticated,
                'session_id': session_id,
                'requires_auth': not authenticated,
                'scopes': self.scopes,
                'service': 'gmail'
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking Gmail auth status: {e}")
            return {
                'success': False,
                'credentials_configured': False,
                'authenticated': False,
                'session_id': session_id,
                'requires_auth': True,
                'error': str(e)
            }
    
    async def get_user_profile(self, session_id: str = None) -> Dict[str, Any]:
        """Get Gmail user profile information for admin detection"""
        try:
            if not session_id:
                session_id = self.current_session_id or 'default_session'
            
            # Check authentication
            if not await self._authenticate(session_id):
                return {
                    'success': False,
                    'message': 'Gmail authentication required',
                    'requires_auth': True
                }
            
            # Get user profile
            profile = self.service.users().getProfile(userId='me').execute()
            
            return {
                'success': True,
                'email': profile.get('emailAddress'),
                'name': profile.get('emailAddress'),  # Gmail API doesn't provide display name in profile
                'messages_total': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0),
                'history_id': profile.get('historyId'),
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting user profile: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get user profile'
            }

# Gmail OAuth service will be instantiated in server.py with database connection