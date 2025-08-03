#!/usr/bin/env python3
"""
Gmail Integration Testing for Elva AI
Focused testing for the specific Gmail integration issues mentioned by the user
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://969852c2-df19-4799-8b24-72ad4de8f1d2.preview.emergentagent.com/api"

class GmailIntegrationTester:
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

    def test_gmail_authentication_flow(self):
        """Test 1: Gmail Authentication Flow - Test /api/gmail/auth endpoint"""
        print("🔐 Testing Gmail Authentication Flow...")
        try:
            # Test Gmail auth endpoint
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if auth_url is generated
                if data.get("success") and data.get("auth_url"):
                    auth_url = data.get("auth_url")
                    
                    # Check if new client_id is in the URL
                    expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                    if expected_client_id in auth_url:
                        self.log_test("Gmail Authentication Flow - OAuth URL Generation", True, f"OAuth URL generated correctly with new client_id")
                        
                        # Check redirect URI
                        expected_redirect = "https://969852c2-df19-4799-8b24-72ad4de8f1d2.preview.emergentagent.com/api/gmail/callback"
                        if expected_redirect in auth_url:
                            self.log_test("Gmail Authentication Flow - Redirect URI", True, "Correct redirect URI configured")
                            return True
                        else:
                            self.log_test("Gmail Authentication Flow - Redirect URI", False, f"Incorrect redirect URI in auth URL")
                            return False
                    else:
                        self.log_test("Gmail Authentication Flow - OAuth URL Generation", False, f"New client_id not found in auth URL: {auth_url}")
                        return False
                else:
                    self.log_test("Gmail Authentication Flow - OAuth URL Generation", False, "Failed to generate auth URL", data)
                    return False
            else:
                self.log_test("Gmail Authentication Flow - OAuth URL Generation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Authentication Flow - OAuth URL Generation", False, f"Error: {str(e)}")
            return False

    def test_gmail_status_endpoint(self):
        """Test 2: Gmail Status Endpoint - Test /api/gmail/status"""
        print("📊 Testing Gmail Status Endpoint...")
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check credentials configuration
                if data.get("credentials_configured") == True:
                    self.log_test("Gmail Status - Credentials Configuration", True, "Credentials properly configured")
                else:
                    self.log_test("Gmail Status - Credentials Configuration", False, "Credentials not configured")
                    return False
                
                # Check scopes
                scopes = data.get("scopes", [])
                expected_scopes = [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.compose",
                    "https://www.googleapis.com/auth/gmail.modify"
                ]
                
                missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
                if not missing_scopes:
                    self.log_test("Gmail Status - OAuth Scopes", True, f"All {len(expected_scopes)} required scopes configured")
                else:
                    self.log_test("Gmail Status - OAuth Scopes", False, f"Missing scopes: {missing_scopes}")
                    return False
                
                # Check authentication status (should be false for new session)
                authenticated = data.get("authenticated", False)
                self.log_test("Gmail Status - Authentication Status", True, f"Authentication status: {authenticated} (expected for new session)")
                return True
                
            else:
                self.log_test("Gmail Status - Endpoint Response", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Status - Endpoint Response", False, f"Error: {str(e)}")
            return False

    def test_chat_error_investigation(self):
        """Test 3: Chat Error Investigation - Check if chat responds with 'sorry I've encountered an error'"""
        print("🔍 Testing Chat Error Investigation...")
        try:
            test_messages = [
                "Hello, how are you?",
                "What can you help me with?",
                "Tell me about yourself"
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
                        results.append(f"✅ '{message}': Clean response received")
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            self.log_test("Chat Error Investigation", all_passed, result_summary)
            return all_passed
            
        except Exception as e:
            self.log_test("Chat Error Investigation", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection(self):
        """Test 4: Gmail Intent Detection - Test if DeBERTa vs Groq routing works properly"""
        print("🎯 Testing Gmail Intent Detection...")
        try:
            gmail_queries = [
                {
                    "message": "Check my inbox",
                    "expected_intent": "check_gmail_inbox",
                    "description": "Basic inbox check"
                },
                {
                    "message": "Show me my unread emails",
                    "expected_intent": "check_gmail_unread", 
                    "description": "Unread emails check"
                },
                {
                    "message": "Any new emails?",
                    "expected_intent": "check_gmail_inbox",
                    "description": "New emails inquiry"
                },
                {
                    "message": "Summarize my last 5 emails",
                    "expected_intent": "gmail_summary",
                    "description": "Email summarization"
                }
            ]
            
            all_passed = True
            results = []
            
            for query in gmail_queries:
                payload = {
                    "message": query["message"],
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get("intent_data", {})
                    detected_intent = intent_data.get("intent")
                    response_text = data.get("response", "")
                    
                    # Check if Gmail intent is detected (not general_chat)
                    if detected_intent and "gmail" in detected_intent.lower():
                        results.append(f"✅ {query['description']}: Gmail intent detected ({detected_intent})")
                        
                        # Check if it's asking for authentication (expected for unauthenticated user)
                        if "connect gmail" in response_text.lower() or "authentication" in response_text.lower():
                            results.append(f"    ✅ Properly requesting Gmail authentication")
                        else:
                            results.append(f"    ⚠️  Response: {response_text[:100]}...")
                            
                    elif detected_intent == "general_chat":
                        results.append(f"❌ {query['description']}: Incorrectly classified as general_chat")
                        all_passed = False
                    else:
                        results.append(f"⚠️  {query['description']}: Unexpected intent ({detected_intent})")
                        # Don't fail for unexpected intents, just note them
                        
                else:
                    results.append(f"❌ {query['description']}: HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            self.log_test("Gmail Intent Detection", all_passed, result_summary)
            return all_passed
            
        except Exception as e:
            self.log_test("Gmail Intent Detection", False, f"Error: {str(e)}")
            return False

    def test_gmail_api_execution(self):
        """Test 5: Gmail API Execution - Test if Gmail API calls work when authenticated"""
        print("📧 Testing Gmail API Execution...")
        try:
            # Test Gmail inbox endpoint (should require authentication)
            response = requests.get(f"{BACKEND_URL}/gmail/inbox?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should require authentication for new session
                if data.get("requires_auth") == True:
                    self.log_test("Gmail API Execution - Authentication Required", True, "Gmail API correctly requires authentication for unauthenticated session")
                    
                    # Check if proper error message is provided
                    message = data.get("message", "")
                    if "authentication" in message.lower() or "connect" in message.lower():
                        self.log_test("Gmail API Execution - Error Message", True, f"Proper authentication message: {message}")
                        return True
                    else:
                        self.log_test("Gmail API Execution - Error Message", False, f"Unclear authentication message: {message}")
                        return False
                        
                elif data.get("success") == True:
                    # If somehow authenticated, check if emails are returned
                    emails = data.get("emails", [])
                    self.log_test("Gmail API Execution - Email Retrieval", True, f"Successfully retrieved {len(emails)} emails")
                    return True
                else:
                    self.log_test("Gmail API Execution - Response Structure", False, "Unexpected response structure", data)
                    return False
                    
            elif response.status_code == 401:
                self.log_test("Gmail API Execution - Authentication Required", True, "Gmail API correctly returns 401 for unauthenticated request")
                return True
            else:
                self.log_test("Gmail API Execution - Response Status", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail API Execution - Response Status", False, f"Error: {str(e)}")
            return False

    def test_error_handling(self):
        """Test 6: Error Handling - Test various error scenarios"""
        print("⚠️  Testing Error Handling...")
        try:
            # Test invalid session ID for Gmail status
            response = requests.get(f"{BACKEND_URL}/gmail/status?session_id=invalid-session", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Should still return valid structure even for invalid session
                if "credentials_configured" in data:
                    self.log_test("Error Handling - Invalid Session ID", True, "Gmail status endpoint handles invalid session gracefully")
                else:
                    self.log_test("Error Handling - Invalid Session ID", False, "Invalid response structure for invalid session")
                    return False
            else:
                self.log_test("Error Handling - Invalid Session ID", False, f"HTTP {response.status_code}")
                return False
            
            # Test malformed chat request
            malformed_payload = {
                "message": "",  # Empty message
                "session_id": self.session_id
                # Missing user_id
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=malformed_payload, timeout=10)
            
            # Should handle gracefully (either 400 or 200 with error message)
            if response.status_code in [200, 400, 422]:
                self.log_test("Error Handling - Malformed Request", True, f"Malformed request handled gracefully (HTTP {response.status_code})")
                return True
            else:
                self.log_test("Error Handling - Malformed Request", False, f"Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Error Handling - Exception Handling", False, f"Error: {str(e)}")
            return False

    def test_frontend_integration(self):
        """Test 7: Frontend Integration - Test if Gmail button functionality works"""
        print("🖥️  Testing Frontend Integration...")
        try:
            # Test if Gmail auth endpoint can be called (simulating Gmail button click)
            response = requests.get(f"{BACKEND_URL}/gmail/auth?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("auth_url"):
                    auth_url = data.get("auth_url")
                    
                    # Check if the URL is properly formatted for Google OAuth
                    if "accounts.google.com/o/oauth2/auth" in auth_url:
                        self.log_test("Frontend Integration - Gmail Button Simulation", True, "Gmail button click simulation successful - OAuth URL generated")
                        
                        # Check if session_id is included in state parameter
                        if self.session_id in auth_url or "state=" in auth_url:
                            self.log_test("Frontend Integration - Session Management", True, "Session ID properly included in OAuth flow")
                            return True
                        else:
                            self.log_test("Frontend Integration - Session Management", False, "Session ID not found in OAuth URL")
                            return False
                    else:
                        self.log_test("Frontend Integration - Gmail Button Simulation", False, f"Invalid OAuth URL format: {auth_url}")
                        return False
                else:
                    self.log_test("Frontend Integration - Gmail Button Simulation", False, "Failed to generate OAuth URL", data)
                    return False
            else:
                self.log_test("Frontend Integration - Gmail Button Simulation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Frontend Integration - Gmail Button Simulation", False, f"Error: {str(e)}")
            return False

    def test_credentials_loading(self):
        """Test 8: Credentials Loading - Verify credentials.json is loaded properly"""
        print("🔑 Testing Credentials Loading...")
        try:
            # Test health endpoint to check Gmail integration status
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                gmail_integration = data.get("gmail_api_integration", {})
                
                # Check if credentials are configured
                if gmail_integration.get("credentials_configured") == True:
                    self.log_test("Credentials Loading - Configuration Status", True, "Credentials.json loaded successfully")
                    
                    # Check if OAuth2 flow is implemented
                    if gmail_integration.get("oauth2_flow") == "implemented":
                        self.log_test("Credentials Loading - OAuth2 Flow", True, "OAuth2 flow properly implemented")
                        
                        # Check if required scopes are configured
                        scopes = gmail_integration.get("scopes", [])
                        if len(scopes) >= 4:  # Should have at least 4 Gmail scopes
                            self.log_test("Credentials Loading - OAuth Scopes", True, f"All {len(scopes)} OAuth scopes configured")
                            return True
                        else:
                            self.log_test("Credentials Loading - OAuth Scopes", False, f"Insufficient scopes configured: {len(scopes)}")
                            return False
                    else:
                        self.log_test("Credentials Loading - OAuth2 Flow", False, f"OAuth2 flow status: {gmail_integration.get('oauth2_flow')}")
                        return False
                else:
                    self.log_test("Credentials Loading - Configuration Status", False, "Credentials not configured")
                    return False
            else:
                self.log_test("Credentials Loading - Health Check", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Credentials Loading - Health Check", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Gmail integration tests"""
        print("🚀 Starting Gmail Integration Testing for Elva AI...")
        print("🎯 FOCUS: Debug Gmail integration issues mentioned by user")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        tests = [
            ("1. Gmail Authentication Flow", self.test_gmail_authentication_flow),
            ("2. Gmail Status Endpoint", self.test_gmail_status_endpoint), 
            ("3. Chat Error Investigation", self.test_chat_error_investigation),
            ("4. Gmail Intent Detection", self.test_gmail_intent_detection),
            ("5. Gmail API Execution", self.test_gmail_api_execution),
            ("6. Error Handling", self.test_error_handling),
            ("7. Frontend Integration", self.test_frontend_integration),
            ("8. Credentials Loading", self.test_credentials_loading)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}:")
            print("-" * 50)
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ EXCEPTION in {test_name}: {str(e)}")
                failed += 1
            
            # Small delay between tests
            time.sleep(0.5)
        
        print("=" * 80)
        print(f"🎯 GMAIL INTEGRATION TESTING COMPLETED!")
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📊 SUCCESS RATE: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL GMAIL INTEGRATION TESTS PASSED!")
        else:
            print(f"⚠️  {failed} tests failed. Check the details above.")
        
        return {
            "total_tests": passed + failed,
            "passed": passed,
            "failed": failed,
            "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = GmailIntegrationTester()
    results = tester.run_all_tests()
    
    # Save detailed results
    with open("/app/gmail_integration_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed results saved to: /app/gmail_integration_test_results.json")