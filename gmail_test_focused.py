#!/usr/bin/env python3
"""
Focused Gmail Integration Testing for Elva AI
Tests the specific Gmail integration pipeline as requested in the review
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://329904b0-2cf4-48ba-8d24-e322e324860a.preview.emergentagent.com/api"

class GmailIntegrationTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data = None):
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

    def test_gmail_credentials_verification(self):
        """Test 1: Gmail Credentials Verification - Test /api/health endpoint to confirm credentials_configured: true"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if Gmail integration section exists
                gmail_integration = data.get("gmail_integration", {})
                if not gmail_integration:
                    self.log_test("Gmail Credentials Verification", False, "No gmail_integration section in health check", data)
                    return False
                
                # Check credentials_configured flag
                credentials_configured = gmail_integration.get("credentials_configured")
                if credentials_configured != True:
                    self.log_test("Gmail Credentials Verification", False, f"credentials_configured should be true, got: {credentials_configured}", gmail_integration)
                    return False
                
                # Check OAuth2 flow status
                oauth2_flow = gmail_integration.get("oauth2_flow")
                if oauth2_flow != "implemented":
                    self.log_test("Gmail Credentials Verification", False, f"oauth2_flow should be 'implemented', got: {oauth2_flow}", gmail_integration)
                    return False
                
                # Check scopes configuration
                scopes = gmail_integration.get("scopes", [])
                expected_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
                
                if missing_scopes:
                    self.log_test("Gmail Credentials Verification", False, f"Missing Gmail scopes: {missing_scopes}", gmail_integration)
                    return False
                
                # Check endpoints availability
                endpoints = gmail_integration.get("endpoints", [])
                expected_endpoints = ["/api/gmail/auth", "/api/gmail/callback", "/api/gmail/status", "/api/gmail/inbox"]
                missing_endpoints = [endpoint for endpoint in expected_endpoints if endpoint not in endpoints]
                
                if missing_endpoints:
                    self.log_test("Gmail Credentials Verification", False, f"Missing Gmail endpoints: {missing_endpoints}", gmail_integration)
                    return False
                
                self.log_test("Gmail Credentials Verification", True, f"Gmail credentials properly configured with {len(scopes)} scopes and {len(endpoints)} endpoints")
                return True
            else:
                self.log_test("Gmail Credentials Verification", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Credentials Verification", False, f"Error: {str(e)}")
            return False

    def test_gmail_authentication_flow(self):
        """Test 2: Gmail Authentication Flow - Test /api/gmail/auth endpoint to ensure it generates valid Google OAuth URLs"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if auth_url is present
                auth_url = data.get("auth_url")
                if not auth_url:
                    self.log_test("Gmail Authentication Flow", False, "No auth_url in response", data)
                    return False
                
                # Check if it's a valid Google OAuth URL
                if not auth_url.startswith("https://accounts.google.com/o/oauth2/auth"):
                    self.log_test("Gmail Authentication Flow", False, f"Invalid OAuth URL format: {auth_url}", data)
                    return False
                
                # Check required OAuth parameters
                required_params = ["client_id", "redirect_uri", "scope", "response_type"]
                missing_params = []
                
                for param in required_params:
                    if param not in auth_url:
                        missing_params.append(param)
                
                if missing_params:
                    self.log_test("Gmail Authentication Flow", False, f"Missing OAuth parameters: {missing_params}", {"auth_url": auth_url})
                    return False
                
                # Check if client_id is the expected one from credentials
                if "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com" not in auth_url:
                    self.log_test("Gmail Authentication Flow", False, "OAuth URL doesn't contain expected client_id", {"auth_url": auth_url})
                    return False
                
                # Check success flag
                if not data.get("success"):
                    self.log_test("Gmail Authentication Flow", False, "Success flag not set", data)
                    return False
                
                self.log_test("Gmail Authentication Flow", True, f"Valid Google OAuth URL generated with all required parameters")
                return True
            else:
                self.log_test("Gmail Authentication Flow", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Authentication Flow", False, f"Error: {str(e)}")
            return False

    def test_gmail_status_check(self):
        """Test 3: Gmail Status Check - Test /api/gmail/status endpoint to verify proper credential configuration"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check credentials_configured flag
                credentials_configured = data.get("credentials_configured")
                if credentials_configured != True:
                    self.log_test("Gmail Status Check", False, f"credentials_configured should be true, got: {credentials_configured}", data)
                    return False
                
                # Check authenticated status (should be false for new session)
                authenticated = data.get("authenticated")
                if authenticated != False:
                    self.log_test("Gmail Status Check", False, f"authenticated should be false for new session, got: {authenticated}", data)
                    return False
                
                # Check scopes
                scopes = data.get("scopes", [])
                if len(scopes) < 4:
                    self.log_test("Gmail Status Check", False, f"Expected at least 4 scopes, got: {len(scopes)}", data)
                    return False
                
                # Check redirect URI
                redirect_uri = data.get("redirect_uri")
                if not redirect_uri or "gmail/callback" not in redirect_uri:
                    self.log_test("Gmail Status Check", False, f"Invalid redirect_uri: {redirect_uri}", data)
                    return False
                
                self.log_test("Gmail Status Check", True, f"Gmail status properly configured - credentials: {credentials_configured}, authenticated: {authenticated}, scopes: {len(scopes)}")
                return True
            else:
                self.log_test("Gmail Status Check", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Status Check", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection(self):
        """Test 4: Gmail Intent Detection - Test chat endpoint with Gmail queries"""
        gmail_queries = [
            {
                "message": "Check my Gmail inbox",
                "expected_intent": "check_gmail_inbox",
                "description": "Gmail inbox check"
            },
            {
                "message": "Summarize my last 5 emails",
                "expected_intent": "gmail_summary",
                "description": "Gmail email summary"
            },
            {
                "message": "Show me unread emails",
                "expected_intent": "check_gmail_unread",
                "description": "Gmail unread emails"
            },
            {
                "message": "Any new emails in my Gmail?",
                "expected_intent": "check_gmail_inbox",
                "description": "Gmail new emails check"
            }
        ]
        
        all_passed = True
        results = []
        
        for query in gmail_queries:
            try:
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
                    
                    # Check if Gmail intent was detected
                    if detected_intent and "gmail" in detected_intent.lower():
                        # Check if authentication prompt is shown
                        response_text = data.get("response", "")
                        if "Gmail Connection Required" in response_text or "Connect Gmail" in response_text or intent_data.get("requires_auth"):
                            results.append(f"✅ {query['description']}: Gmail intent detected with auth prompt")
                        else:
                            results.append(f"❌ {query['description']}: Gmail intent detected but no auth prompt")
                            all_passed = False
                    else:
                        results.append(f"❌ {query['description']}: Expected Gmail intent, got {detected_intent}")
                        all_passed = False
                else:
                    results.append(f"❌ {query['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {query['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Gmail Intent Detection", all_passed, result_summary)
        return all_passed

    def test_chat_error_investigation(self):
        """Test 5: Chat Error Investigation - Test basic chat functionality with 'Hello' message"""
        try:
            payload = {
                "message": "Hello",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["id", "message", "response", "intent_data", "needs_approval", "timestamp"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Chat Error Investigation", False, f"Missing response fields: {missing_fields}", data)
                    return False
                
                # Check for error messages
                response_text = data.get("response", "")
                error_indicators = [
                    "sorry I've encountered an error",
                    "Sorry, I encountered an error",
                    "error processing your request",
                    "Error:",
                    "Exception:",
                    "Failed to"
                ]
                
                has_error = any(indicator.lower() in response_text.lower() for indicator in error_indicators)
                
                if has_error:
                    self.log_test("Chat Error Investigation", False, f"Error message detected in response: {response_text}", data)
                    return False
                
                # Check if response is not empty
                if not response_text or len(response_text.strip()) == 0:
                    self.log_test("Chat Error Investigation", False, "Empty response from chat endpoint", data)
                    return False
                
                # Check intent classification
                intent_data = data.get("intent_data", {})
                if intent_data.get("intent") != "general_chat":
                    self.log_test("Chat Error Investigation", False, f"Wrong intent for 'Hello': {intent_data.get('intent')}", data)
                    return False
                
                # Check needs_approval is False
                if data.get("needs_approval") != False:
                    self.log_test("Chat Error Investigation", False, "Hello message should not need approval", data)
                    return False
                
                self.log_test("Chat Error Investigation", True, f"Basic chat working correctly - Response: {response_text[:100]}...")
                return True
            else:
                self.log_test("Chat Error Investigation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Chat Error Investigation", False, f"Error: {str(e)}")
            return False

    def test_complete_gmail_pipeline(self):
        """Test 6: Complete Gmail Pipeline Test - Test the complete flow"""
        try:
            # Step 1: Test Gmail query with intent detection
            payload = {
                "message": "Check my Gmail inbox for new emails",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code != 200:
                self.log_test("Complete Gmail Pipeline", False, f"Chat endpoint failed: HTTP {response.status_code}", response.text)
                return False
            
            data = response.json()
            
            # Step 2: Verify Gmail intent detection
            intent_data = data.get("intent_data", {})
            detected_intent = intent_data.get("intent", "")
            
            if "gmail" not in detected_intent.lower():
                self.log_test("Complete Gmail Pipeline", False, f"Gmail intent not detected: {detected_intent}", data)
                return False
            
            # Step 3: Verify authentication check
            requires_auth = intent_data.get("requires_auth", False)
            response_text = data.get("response", "")
            
            if not requires_auth and "Connect Gmail" not in response_text:
                self.log_test("Complete Gmail Pipeline", False, "Authentication check not working", data)
                return False
            
            # Step 4: Test Gmail auth URL generation
            auth_response = requests.get(f"{BACKEND_URL}/gmail/auth?session_id={self.session_id}", timeout=10)
            
            if auth_response.status_code != 200:
                self.log_test("Complete Gmail Pipeline", False, f"Gmail auth endpoint failed: HTTP {auth_response.status_code}")
                return False
            
            auth_data = auth_response.json()
            auth_url = auth_data.get("auth_url", "")
            
            if not auth_url or "accounts.google.com" not in auth_url:
                self.log_test("Complete Gmail Pipeline", False, f"Invalid auth URL: {auth_url}")
                return False
            
            # Step 5: Test Gmail status endpoint
            status_response = requests.get(f"{BACKEND_URL}/gmail/status?session_id={self.session_id}", timeout=10)
            
            if status_response.status_code != 200:
                self.log_test("Complete Gmail Pipeline", False, f"Gmail status endpoint failed: HTTP {status_response.status_code}")
                return False
            
            status_data = status_response.json()
            
            if not status_data.get("credentials_configured"):
                self.log_test("Complete Gmail Pipeline", False, "Gmail credentials not configured in status", status_data)
                return False
            
            # Step 6: Verify response formatting
            if not data.get("response") or len(data.get("response", "").strip()) == 0:
                self.log_test("Complete Gmail Pipeline", False, "Empty response in Gmail pipeline", data)
                return False
            
            self.log_test("Complete Gmail Pipeline", True, f"Complete Gmail pipeline working: Intent detection → Authentication check → Response formatting")
            return True
            
        except Exception as e:
            self.log_test("Complete Gmail Pipeline", False, f"Error: {str(e)}")
            return False

    def run_gmail_tests(self):
        """Run all Gmail integration tests"""
        print("🚀 Starting Gmail Integration Pipeline Testing for Elva AI...")
        print("🎯 FOCUS: Gmail Integration Pipeline as requested in review")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        # Gmail Integration Pipeline Tests (Priority)
        gmail_tests = [
            ("Gmail Credentials Verification", self.test_gmail_credentials_verification),
            ("Gmail Authentication Flow", self.test_gmail_authentication_flow),
            ("Gmail Status Check", self.test_gmail_status_check),
            ("Gmail Intent Detection", self.test_gmail_intent_detection),
            ("Chat Error Investigation", self.test_chat_error_investigation),
            ("Complete Gmail Pipeline", self.test_complete_gmail_pipeline),
        ]
        
        passed = 0
        failed = 0
        
        print("\n🎯 GMAIL INTEGRATION PIPELINE TESTS:")
        print("=" * 50)
        
        for test_name, test_func in gmail_tests:
            print(f"\n📋 Running: {test_name}")
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
            print("🎉 ALL GMAIL TESTS PASSED! Gmail integration is working perfectly!")
        else:
            print(f"⚠️  {failed} Gmail tests failed. Check the details above.")
        
        return {
            "total_tests": passed + failed,
            "passed": passed,
            "failed": failed,
            "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = GmailIntegrationTester()
    results = tester.run_gmail_tests()
    
    # Save detailed results
    with open("/app/gmail_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed Gmail test results saved to: /app/gmail_test_results.json")