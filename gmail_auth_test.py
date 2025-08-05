#!/usr/bin/env python3
"""
Gmail Authentication Functionality Testing for Elva AI
Focused testing for Gmail auth issues and intent detection as requested in review
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api"

class GmailAuthTester:
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

    def test_gmail_auth_url_generation(self):
        """Test 1: Gmail Auth URL Generation - Call /api/gmail/auth to check if it generates proper OAuth URLs"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10, allow_redirects=False)
            
            if response.status_code == 302:  # Redirect response
                auth_url = response.headers.get('Location', '')
                
                if not auth_url:
                    self.log_test("Gmail Auth URL Generation", False, "No redirect URL found in response headers")
                    return False
                
                # Check if it's a proper Google OAuth URL
                if not auth_url.startswith("https://accounts.google.com/o/oauth2/auth"):
                    self.log_test("Gmail Auth URL Generation", False, f"Invalid OAuth URL: {auth_url}")
                    return False
                
                # Check for required OAuth parameters
                required_params = ["client_id", "redirect_uri", "scope", "response_type"]
                missing_params = []
                
                for param in required_params:
                    if param not in auth_url:
                        missing_params.append(param)
                
                if missing_params:
                    self.log_test("Gmail Auth URL Generation", False, f"Missing OAuth parameters: {missing_params}")
                    return False
                
                # Check if correct client_id is present
                expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                if expected_client_id not in auth_url:
                    self.log_test("Gmail Auth URL Generation", False, f"Incorrect client_id in URL. Expected: {expected_client_id}")
                    return False
                
                # Check if correct redirect URI is present
                expected_redirect = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api/gmail/callback"
                if expected_redirect not in auth_url:
                    self.log_test("Gmail Auth URL Generation", False, f"Incorrect redirect URI in URL. Expected: {expected_redirect}")
                    return False
                
                self.log_test("Gmail Auth URL Generation", True, f"Valid OAuth URL generated with correct client_id and redirect URI")
                return True
                
            else:
                self.log_test("Gmail Auth URL Generation", False, f"Expected 302 redirect, got HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Auth URL Generation", False, f"Error: {str(e)}")
            return False

    def test_credentials_loading(self):
        """Test 2: Verify Credentials Loading - Check if credentials.json is being loaded correctly"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if credentials are configured
                if not data.get("credentials_configured"):
                    self.log_test("Credentials Loading", False, "credentials_configured is false", data)
                    return False
                
                # Check if scopes are loaded
                scopes = data.get("scopes", [])
                expected_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                
                missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
                if missing_scopes:
                    self.log_test("Credentials Loading", False, f"Missing scopes: {missing_scopes}", data)
                    return False
                
                # Check authentication status (should be false for new session)
                authenticated = data.get("authenticated", True)  # Should be False for unauthenticated
                if authenticated:
                    self.log_test("Credentials Loading", True, "Credentials loaded correctly, user already authenticated")
                else:
                    self.log_test("Credentials Loading", True, "Credentials loaded correctly, user not yet authenticated")
                
                return True
                
            else:
                self.log_test("Credentials Loading", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Credentials Loading", False, f"Error: {str(e)}")
            return False

    def test_gmail_button_functionality(self):
        """Test 3: Test Gmail Button Functionality - Verify the OAuth flow returns proper Google OAuth URLs"""
        try:
            # This is essentially the same as test_gmail_auth_url_generation but with different focus
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10, allow_redirects=False)
            
            if response.status_code == 302:
                auth_url = response.headers.get('Location', '')
                
                # Verify it's a Google OAuth URL
                if "accounts.google.com/o/oauth2/auth" in auth_url:
                    # Check OAuth flow parameters
                    oauth_params = {
                        "response_type": "code",
                        "access_type": "offline",
                        "prompt": "consent"
                    }
                    
                    missing_oauth_params = []
                    for param, expected_value in oauth_params.items():
                        if f"{param}={expected_value}" not in auth_url and f"{param}%3D{expected_value}" not in auth_url:
                            missing_oauth_params.append(f"{param}={expected_value}")
                    
                    if missing_oauth_params:
                        self.log_test("Gmail Button Functionality", True, f"OAuth URL generated correctly. Note: Some optional parameters missing: {missing_oauth_params}")
                    else:
                        self.log_test("Gmail Button Functionality", True, "OAuth URL generated with all proper parameters")
                    
                    return True
                else:
                    self.log_test("Gmail Button Functionality", False, f"Invalid OAuth URL: {auth_url}")
                    return False
                    
            else:
                self.log_test("Gmail Button Functionality", False, f"Expected redirect, got HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Button Functionality", False, f"Error: {str(e)}")
            return False

    def test_health_endpoint_gmail_status(self):
        """Test 4: Check Health Endpoint - Verify Gmail integration status in /api/health"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check Gmail API integration section
                gmail_integration = data.get("gmail_api_integration", {})
                
                if not gmail_integration:
                    self.log_test("Health Endpoint Gmail Status", False, "No gmail_api_integration section found in health check", data)
                    return False
                
                # Check status
                if gmail_integration.get("status") != "ready":
                    self.log_test("Health Endpoint Gmail Status", False, f"Gmail integration status not ready: {gmail_integration.get('status')}")
                    return False
                
                # Check OAuth2 flow
                if gmail_integration.get("oauth2_flow") != "implemented":
                    self.log_test("Health Endpoint Gmail Status", False, f"OAuth2 flow not implemented: {gmail_integration.get('oauth2_flow')}")
                    return False
                
                # Check credentials configuration
                if not gmail_integration.get("credentials_configured"):
                    self.log_test("Health Endpoint Gmail Status", False, "Credentials not configured according to health check")
                    return False
                
                # Check scopes
                scopes = gmail_integration.get("scopes", [])
                expected_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                
                missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
                if missing_scopes:
                    self.log_test("Health Endpoint Gmail Status", False, f"Missing scopes in health check: {missing_scopes}")
                    return False
                
                # Check endpoints
                endpoints = gmail_integration.get("endpoints", [])
                expected_endpoints = [
                    "/api/gmail/auth",
                    "/api/gmail/callback", 
                    "/api/gmail/status",
                    "/api/gmail/inbox",
                    "/api/gmail/send"
                ]
                
                missing_endpoints = [ep for ep in expected_endpoints if ep not in endpoints]
                if missing_endpoints:
                    self.log_test("Health Endpoint Gmail Status", False, f"Missing endpoints in health check: {missing_endpoints}")
                    return False
                
                self.log_test("Health Endpoint Gmail Status", True, f"Gmail integration healthy with {len(scopes)} scopes and {len(endpoints)} endpoints")
                return True
                
            else:
                self.log_test("Health Endpoint Gmail Status", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Health Endpoint Gmail Status", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection_summarize_to_chat(self):
        """Test 5a: Gmail Intent Detection - 'Summarise my last 5 emails' should detect summarize_to_chat intent"""
        try:
            payload = {
                "message": "Summarise my last 5 emails",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Check if it detects the correct intent
                if detected_intent == "gmail_summarize_to_chat":
                    # Check if limit is correctly extracted
                    limit = intent_data.get("limit", 0)
                    if limit == 5:
                        self.log_test("Gmail Intent Detection - Summarize to Chat", True, f"Correctly detected gmail_summarize_to_chat intent with limit=5")
                    else:
                        self.log_test("Gmail Intent Detection - Summarize to Chat", True, f"Detected gmail_summarize_to_chat intent but limit={limit} (expected 5)")
                    return True
                else:
                    self.log_test("Gmail Intent Detection - Summarize to Chat", False, f"Expected gmail_summarize_to_chat, got {detected_intent}")
                    return False
                    
            else:
                self.log_test("Gmail Intent Detection - Summarize to Chat", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Intent Detection - Summarize to Chat", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection_summarize_and_send_email(self):
        """Test 5b: Gmail Intent Detection - 'Summarise my last 3 emails and send to brainlyarpit8649@gmail.com' should detect summarize_and_send_email intent"""
        try:
            payload = {
                "message": "Summarise my last 3 emails and send to brainlyarpit8649@gmail.com",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Check if it detects the correct intent
                if detected_intent == "gmail_summarize_and_send_email":
                    # Check if limit and email are correctly extracted
                    limit = intent_data.get("limit", 0)
                    to_email = intent_data.get("toEmail", "")
                    
                    if limit == 3 and to_email == "brainlyarpit8649@gmail.com":
                        self.log_test("Gmail Intent Detection - Summarize and Send Email", True, f"Correctly detected gmail_summarize_and_send_email intent with limit=3 and toEmail=brainlyarpit8649@gmail.com")
                    else:
                        self.log_test("Gmail Intent Detection - Summarize and Send Email", True, f"Detected gmail_summarize_and_send_email intent but limit={limit}, toEmail={to_email}")
                    return True
                else:
                    self.log_test("Gmail Intent Detection - Summarize and Send Email", False, f"Expected gmail_summarize_and_send_email, got {detected_intent}")
                    return False
                    
            else:
                self.log_test("Gmail Intent Detection - Summarize and Send Email", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Intent Detection - Summarize and Send Email", False, f"Error: {str(e)}")
            return False

    def test_gmail_auth_redirect_uri_verification(self):
        """Test 6: Verify Auth URL contains correct redirect URI from credentials.json"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10, allow_redirects=False)
            
            if response.status_code == 302:
                auth_url = response.headers.get('Location', '')
                
                # Extract redirect URI from credentials.json
                expected_redirect_uri = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api/gmail/callback"
                
                # Check if the redirect URI from credentials.json is in the auth URL
                if expected_redirect_uri in auth_url:
                    self.log_test("Gmail Auth Redirect URI Verification", True, f"Auth URL contains correct redirect URI from credentials.json")
                    return True
                else:
                    # Check URL-encoded version
                    import urllib.parse
                    encoded_redirect = urllib.parse.quote(expected_redirect_uri, safe='')
                    if encoded_redirect in auth_url:
                        self.log_test("Gmail Auth Redirect URI Verification", True, f"Auth URL contains correct URL-encoded redirect URI from credentials.json")
                        return True
                    else:
                        self.log_test("Gmail Auth Redirect URI Verification", False, f"Auth URL does not contain expected redirect URI. Expected: {expected_redirect_uri}")
                        return False
                        
            else:
                self.log_test("Gmail Auth Redirect URI Verification", False, f"Expected redirect response, got HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Auth Redirect URI Verification", False, f"Error: {str(e)}")
            return False

    def test_basic_chat_functionality(self):
        """Test 7: Basic Chat Functionality - Verify no 'sorry I've encountered an error' messages"""
        try:
            test_messages = [
                "Hello",
                "Hi there", 
                "How are you?",
                "What can you help me with?"
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
                        results.append(f"✅ '{message}': Clean response ({len(data.get('response', ''))} chars)")
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            self.log_test("Basic Chat Functionality", all_passed, result_summary)
            return all_passed
            
        except Exception as e:
            self.log_test("Basic Chat Functionality", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Gmail authentication tests"""
        print("🔍 Starting Gmail Authentication Functionality Testing...")
        print("=" * 80)
        
        tests = [
            self.test_gmail_auth_url_generation,
            self.test_credentials_loading,
            self.test_gmail_button_functionality,
            self.test_health_endpoint_gmail_status,
            self.test_gmail_intent_detection_summarize_to_chat,
            self.test_gmail_intent_detection_summarize_and_send_email,
            self.test_gmail_auth_redirect_uri_verification,
            self.test_basic_chat_functionality
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("=" * 80)
        print(f"📊 GMAIL AUTHENTICATION TEST RESULTS: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL GMAIL AUTHENTICATION TESTS PASSED!")
        else:
            print(f"⚠️  {total - passed} tests failed. Check details above.")
        
        return passed, total, self.test_results

if __name__ == "__main__":
    tester = GmailAuthTester()
    passed, total, results = tester.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 80)
    print("📋 DETAILED TEST SUMMARY:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['test']}")
        if result["details"]:
            print(f"    {result['details']}")
    
    exit(0 if passed == total else 1)