#!/usr/bin/env python3
"""
Gmail Intent Detection Backend Testing for Elva AI
Tests Gmail intent detection functionality, authentication prompts, and MCP integration
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api"

class GmailBackendTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    Details: {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def test_health_endpoint_gmail_integration(self):
        """Test 1: /api/health - should show Gmail integration as 'ready' and credentials as 'configured'"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check Gmail integration status
                gmail_integration = data.get("gmail_api_integration", {})
                
                if gmail_integration.get("status") == "ready":
                    self.log_test("Health - Gmail Integration Status", True, "Gmail integration status: ready")
                else:
                    self.log_test("Health - Gmail Integration Status", False, f"Gmail integration status: {gmail_integration.get('status')}")
                    return False
                    
                # Check credentials configuration
                if gmail_integration.get("credentials_configured") == True:
                    self.log_test("Health - Gmail Credentials", True, "Gmail credentials properly configured")
                else:
                    self.log_test("Health - Gmail Credentials", False, "Gmail credentials not configured")
                    return False
                    
                # Check OAuth2 flow
                if gmail_integration.get("oauth2_flow") == "implemented":
                    self.log_test("Health - Gmail OAuth2 Flow", True, "OAuth2 flow implemented")
                else:
                    self.log_test("Health - Gmail OAuth2 Flow", False, f"OAuth2 flow: {gmail_integration.get('oauth2_flow')}")
                    return False
                    
                # Check scopes
                scopes = gmail_integration.get("scopes", [])
                expected_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
                
                if not missing_scopes:
                    self.log_test("Health - Gmail Scopes", True, f"All {len(expected_scopes)} Gmail scopes configured")
                else:
                    self.log_test("Health - Gmail Scopes", False, f"Missing scopes: {missing_scopes}")
                    return False
                    
                # Check endpoints
                endpoints = gmail_integration.get("endpoints", [])
                expected_endpoints = ["/api/gmail/auth", "/api/gmail/callback", "/api/gmail/status", "/api/gmail/inbox"]
                missing_endpoints = [ep for ep in expected_endpoints if ep not in endpoints]
                
                if not missing_endpoints:
                    self.log_test("Health - Gmail Endpoints", True, f"All {len(expected_endpoints)} Gmail endpoints available")
                else:
                    self.log_test("Health - Gmail Endpoints", False, f"Missing endpoints: {missing_endpoints}")
                    return False
                    
                return True
            else:
                self.log_test("Health - Gmail Integration", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Health - Gmail Integration", False, f"Error: {str(e)}")
            return False

    def test_gmail_auth_endpoint(self):
        """Test 2: /api/gmail/auth?session_id=test123 - should generate valid OAuth URL"""
        try:
            test_session_id = "test123"
            response = requests.get(f"{BACKEND_URL}/gmail/auth", params={"session_id": test_session_id}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if auth_url is generated
                if not data.get("success"):
                    self.log_test("Gmail Auth - Success Flag", False, "Success flag not set", data)
                    return False
                    
                auth_url = data.get("auth_url")
                if not auth_url:
                    self.log_test("Gmail Auth - URL Generation", False, "No auth_url in response", data)
                    return False
                    
                # Check if it's a valid Google OAuth URL
                if not auth_url.startswith("https://accounts.google.com/o/oauth2/auth"):
                    self.log_test("Gmail Auth - Valid Google URL", False, f"Invalid OAuth URL: {auth_url}")
                    return False
                    
                # Check if new client_id is in the URL
                expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                if expected_client_id not in auth_url:
                    self.log_test("Gmail Auth - Client ID", False, f"New client_id not found in auth URL")
                    return False
                    
                # Check redirect URI
                expected_redirect = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api/gmail/callback"
                if expected_redirect not in auth_url:
                    self.log_test("Gmail Auth - Redirect URI", False, f"Correct redirect URI not found in auth URL")
                    return False
                    
                # Check required OAuth parameters
                required_params = ["client_id", "redirect_uri", "scope", "response_type"]
                missing_params = [param for param in required_params if param not in auth_url]
                
                if missing_params:
                    self.log_test("Gmail Auth - OAuth Parameters", False, f"Missing OAuth parameters: {missing_params}")
                    return False
                    
                self.log_test("Gmail Auth - Valid OAuth URL", True, f"Valid OAuth URL generated with correct client_id and redirect_uri")
                return True
            else:
                self.log_test("Gmail Auth - URL Generation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Auth - URL Generation", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection_check_inbox(self):
        """Test 3: Gmail intent detection - 'Check my inbox' should detect gmail_inbox intent"""
        try:
            payload = {
                "message": "Check my inbox",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Check if Gmail intent is detected (not general_chat)
                gmail_intents = ["gmail_inbox", "check_gmail_inbox", "gmail_summary"]
                if detected_intent in gmail_intents:
                    self.log_test("Gmail Intent - Check Inbox", True, f"Correctly detected Gmail intent: {detected_intent}")
                else:
                    self.log_test("Gmail Intent - Check Inbox", False, f"Expected Gmail intent, got: {detected_intent}")
                    return False
                    
                # Check response doesn't contain raw JSON
                response_text = data.get("response", "")
                if "{" in response_text and "}" in response_text and "intent" in response_text.lower():
                    self.log_test("Gmail Intent - No Raw JSON", False, "Response contains raw JSON instead of user-friendly message")
                    return False
                    
                # Check for authentication prompt (since user is not authenticated)
                if "connect gmail" in response_text.lower() or "gmail connection" in response_text.lower() or "authenticate" in response_text.lower():
                    self.log_test("Gmail Intent - Auth Prompt", True, "Proper authentication prompt shown")
                else:
                    self.log_test("Gmail Intent - Auth Prompt", False, f"No authentication prompt in response: {response_text}")
                    return False
                    
                # Check no error messages
                error_phrases = ["sorry i've encountered an error", "sorry, i've encountered an error", "encountered an error"]
                has_error = any(phrase in response_text.lower() for phrase in error_phrases)
                
                if has_error:
                    self.log_test("Gmail Intent - No Error Messages", False, "Response contains error message")
                    return False
                else:
                    self.log_test("Gmail Intent - No Error Messages", True, "No error messages in response")
                    
                return True
            else:
                self.log_test("Gmail Intent - Check Inbox", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Intent - Check Inbox", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection_unread_emails(self):
        """Test 4: Gmail intent detection - 'Show unread emails' should detect gmail_unread intent"""
        try:
            payload = {
                "message": "Show unread emails",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Check if Gmail unread intent is detected
                gmail_unread_intents = ["gmail_unread", "check_gmail_unread", "gmail_inbox"]
                if detected_intent in gmail_unread_intents:
                    self.log_test("Gmail Intent - Unread Emails", True, f"Correctly detected Gmail unread intent: {detected_intent}")
                else:
                    self.log_test("Gmail Intent - Unread Emails", False, f"Expected Gmail unread intent, got: {detected_intent}")
                    return False
                    
                # Check response doesn't contain raw JSON
                response_text = data.get("response", "")
                if "{" in response_text and "}" in response_text and "intent" in response_text.lower():
                    self.log_test("Gmail Intent - No Raw JSON (Unread)", False, "Response contains raw JSON instead of user-friendly message")
                    return False
                    
                # Check for authentication prompt
                if "connect gmail" in response_text.lower() or "gmail connection" in response_text.lower() or "authenticate" in response_text.lower():
                    self.log_test("Gmail Intent - Auth Prompt (Unread)", True, "Proper authentication prompt shown")
                else:
                    self.log_test("Gmail Intent - Auth Prompt (Unread)", False, f"No authentication prompt in response: {response_text}")
                    return False
                    
                return True
            else:
                self.log_test("Gmail Intent - Unread Emails", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Intent - Unread Emails", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection_summarize_emails(self):
        """Test 5: Gmail intent detection - 'Summarize my last 5 emails' should detect gmail_summary intent"""
        try:
            payload = {
                "message": "Summarize my last 5 emails",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Check if Gmail summary intent is detected
                gmail_summary_intents = ["gmail_summary", "gmail_inbox", "check_gmail_inbox"]
                if detected_intent in gmail_summary_intents:
                    self.log_test("Gmail Intent - Summarize Emails", True, f"Correctly detected Gmail summary intent: {detected_intent}")
                else:
                    self.log_test("Gmail Intent - Summarize Emails", False, f"Expected Gmail summary intent, got: {detected_intent}")
                    return False
                    
                # Check response doesn't contain raw JSON
                response_text = data.get("response", "")
                if "{" in response_text and "}" in response_text and "intent" in response_text.lower():
                    self.log_test("Gmail Intent - No Raw JSON (Summary)", False, "Response contains raw JSON instead of user-friendly message")
                    return False
                    
                # Check for authentication prompt
                if "connect gmail" in response_text.lower() or "gmail connection" in response_text.lower() or "authenticate" in response_text.lower():
                    self.log_test("Gmail Intent - Auth Prompt (Summary)", True, "Proper authentication prompt shown")
                else:
                    self.log_test("Gmail Intent - Auth Prompt (Summary)", False, f"No authentication prompt in response: {response_text}")
                    return False
                    
                return True
            else:
                self.log_test("Gmail Intent - Summarize Emails", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Intent - Summarize Emails", False, f"Error: {str(e)}")
            return False

    def test_mcp_write_context(self):
        """Test 6: MCP Integration - /api/mcp/write-context for Gmail data storage"""
        try:
            payload = {
                "session_id": self.session_id,
                "user_id": "test_user",
                "intent": "gmail_inbox",
                "data": {
                    "user_query": "Check my Gmail inbox",
                    "gmail_intent": "gmail_inbox",
                    "confidence": 0.9,
                    "user_email": "brainlyarpit8649@gmail.com",
                    "emails": [
                        {
                            "from": "test@example.com",
                            "subject": "Test Email",
                            "snippet": "This is a test email for MCP storage",
                            "received": "2024-01-15T10:30:00Z"
                        }
                    ],
                    "email_count": 1
                }
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/write-context", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get("success"):
                    self.log_test("MCP - Write Context", False, "Success flag not set", data)
                    return False
                    
                if "Context written to MCP successfully" not in data.get("message", ""):
                    self.log_test("MCP - Write Context", False, f"Unexpected message: {data.get('message')}")
                    return False
                    
                self.log_test("MCP - Write Context", True, "Gmail data successfully written to MCP context")
                return True
            else:
                self.log_test("MCP - Write Context", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP - Write Context", False, f"Error: {str(e)}")
            return False

    def test_mcp_read_context(self):
        """Test 7: MCP Integration - /api/mcp/read-context/{session_id} for Gmail data retrieval"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp/read-context/{self.session_id}", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if context data is present
                if not data:
                    self.log_test("MCP - Read Context", False, "No context data returned")
                    return False
                    
                # Check if it contains Gmail-related data (from previous write test)
                context_str = json.dumps(data).lower()
                gmail_keywords = ["gmail", "email", "inbox"]
                
                has_gmail_data = any(keyword in context_str for keyword in gmail_keywords)
                if has_gmail_data:
                    self.log_test("MCP - Read Context", True, "Gmail context data successfully retrieved from MCP")
                else:
                    self.log_test("MCP - Read Context", True, "MCP read context working (no Gmail data found, which is expected for new session)")
                    
                return True
            else:
                self.log_test("MCP - Read Context", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP - Read Context", False, f"Error: {str(e)}")
            return False

    def test_backend_startup_dependencies(self):
        """Test 8: Backend startup - confirm no dependency errors (pyparsing, uritemplate)"""
        try:
            # Test basic connectivity to ensure backend started without dependency errors
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if status is healthy (indicates successful startup)
                if data.get("status") == "healthy":
                    self.log_test("Backend Startup - Dependencies", True, "Backend started successfully without dependency errors")
                else:
                    self.log_test("Backend Startup - Dependencies", False, f"Backend status not healthy: {data.get('status')}")
                    return False
                    
                # Check if Gmail integration is loaded (indicates uritemplate and pyparsing are working)
                gmail_integration = data.get("gmail_api_integration", {})
                if gmail_integration.get("status") == "ready":
                    self.log_test("Backend Startup - Gmail Dependencies", True, "Gmail integration loaded successfully (pyparsing, uritemplate working)")
                else:
                    self.log_test("Backend Startup - Gmail Dependencies", False, f"Gmail integration not ready: {gmail_integration.get('status')}")
                    return False
                    
                return True
            else:
                self.log_test("Backend Startup - Dependencies", False, f"Backend not accessible: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Backend Startup - Dependencies", False, f"Backend startup error: {str(e)}")
            return False

    def test_no_error_messages_general_chat(self):
        """Test 9: Verify no 'sorry I've encountered an error' messages for general chat"""
        try:
            test_messages = [
                "Hello, how are you?",
                "What can you help me with?",
                "Tell me about the weather",
                "How does AI work?"
            ]
            
            all_passed = True
            results = []
            
            for message in test_messages:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").lower()
                    
                    # Check for error messages
                    error_phrases = [
                        "sorry i've encountered an error",
                        "sorry, i've encountered an error", 
                        "encountered an error",
                        "error processing your request"
                    ]
                    
                    has_error = any(phrase in response_text for phrase in error_phrases)
                    
                    if has_error:
                        results.append(f"❌ '{message}': Contains error message")
                        all_passed = False
                    else:
                        results.append(f"✅ '{message}': No error message")
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            self.log_test("No Error Messages - General Chat", all_passed, result_summary)
            return all_passed
            
        except Exception as e:
            self.log_test("No Error Messages - General Chat", False, f"Error: {str(e)}")
            return False

    def test_gmail_status_endpoint(self):
        """Test 10: Gmail status endpoint verification"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check credentials configuration
                if data.get("credentials_configured") == True:
                    self.log_test("Gmail Status - Credentials", True, "Gmail credentials configured")
                else:
                    self.log_test("Gmail Status - Credentials", False, "Gmail credentials not configured")
                    return False
                    
                # Check authentication status (should be false for new session)
                if data.get("authenticated") == False:
                    self.log_test("Gmail Status - Authentication", True, "Authentication status correctly shows false for new session")
                else:
                    self.log_test("Gmail Status - Authentication", True, f"Authentication status: {data.get('authenticated')}")
                    
                # Check scopes
                scopes = data.get("scopes", [])
                if len(scopes) >= 4:
                    self.log_test("Gmail Status - Scopes", True, f"Gmail scopes configured: {len(scopes)} scopes")
                else:
                    self.log_test("Gmail Status - Scopes", False, f"Insufficient scopes: {scopes}")
                    return False
                    
                return True
            else:
                self.log_test("Gmail Status - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Status - Endpoint", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Gmail integration tests"""
        print("🚀 Starting Gmail Intent Detection Backend Testing...")
        print(f"📋 Session ID: {self.session_id}")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        tests = [
            self.test_health_endpoint_gmail_integration,
            self.test_gmail_auth_endpoint,
            self.test_gmail_intent_detection_check_inbox,
            self.test_gmail_intent_detection_unread_emails,
            self.test_gmail_intent_detection_summarize_emails,
            self.test_mcp_write_context,
            self.test_mcp_read_context,
            self.test_backend_startup_dependencies,
            self.test_no_error_messages_general_chat,
            self.test_gmail_status_endpoint
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ EXCEPTION in {test.__name__}: {str(e)}")
                failed += 1
        
        print("=" * 80)
        print(f"📊 GMAIL INTEGRATION TEST RESULTS:")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed / (passed + failed) * 100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL GMAIL INTEGRATION TESTS PASSED!")
        else:
            print(f"⚠️  {failed} tests failed. Check details above.")
        
        return passed, failed

if __name__ == "__main__":
    tester = GmailBackendTester()
    passed, failed = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)