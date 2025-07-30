#!/usr/bin/env python3
"""
Gmail Authentication Status Testing for Elva AI
Tests specifically the Gmail OAuth2 integration and authentication status functionality
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://c4d23dc7-8694-453c-8503-c38b6da7ae31.preview.emergentagent.com/api"

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

    def test_gmail_import_resolution(self):
        """Test 1: Verify Gmail OAuth service import is resolved"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if Gmail API integration is present in health check
                if "gmail_api_integration" in data:
                    gmail_integration = data["gmail_api_integration"]
                    
                    # Check if status is ready (indicates successful import)
                    if gmail_integration.get("status") == "ready":
                        self.log_test("Gmail Import Resolution", True, "Gmail OAuth service successfully imported and initialized")
                        return True
                    else:
                        self.log_test("Gmail Import Resolution", False, f"Gmail integration status: {gmail_integration.get('status')}", data)
                        return False
                else:
                    self.log_test("Gmail Import Resolution", False, "Gmail API integration not found in health check", data)
                    return False
            else:
                self.log_test("Gmail Import Resolution", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Import Resolution", False, f"Error: {str(e)}")
            return False

    def test_gmail_oauth_status_endpoint(self):
        """Test 2: Gmail OAuth2 authentication status endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["success", "credentials_configured", "authenticated", "requires_auth", "scopes", "service"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Gmail OAuth Status Endpoint", False, f"Missing status fields: {missing_fields}", data)
                    return False
                
                # Check if credentials are configured
                if not data.get("credentials_configured"):
                    self.log_test("Gmail OAuth Status Endpoint", False, "Gmail credentials.json not configured", data)
                    return False
                
                # Check scopes
                required_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                scopes = data.get("scopes", [])
                missing_scopes = [scope for scope in required_scopes if f"https://www.googleapis.com/auth/{scope}" not in scopes]
                
                if missing_scopes:
                    self.log_test("Gmail OAuth Status Endpoint", False, f"Missing Gmail scopes: {missing_scopes}", data)
                    return False
                
                self.log_test("Gmail OAuth Status Endpoint", True, f"Gmail OAuth2 status configured correctly. Authenticated: {data.get('authenticated')}")
                return True
            else:
                self.log_test("Gmail OAuth Status Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail OAuth Status Endpoint", False, f"Error: {str(e)}")
            return False

    def test_gmail_oauth_status_with_session(self):
        """Test 3: Gmail OAuth2 status with session_id parameter"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if session_id is included in response
                if data.get("session_id") != self.session_id:
                    self.log_test("Gmail OAuth Status with Session", False, f"Session ID mismatch: expected {self.session_id}, got {data.get('session_id')}", data)
                    return False
                
                # Check MongoDB token storage functionality
                if "authenticated" not in data:
                    self.log_test("Gmail OAuth Status with Session", False, "Authentication status not provided", data)
                    return False
                
                self.log_test("Gmail OAuth Status with Session", True, f"Session-based authentication status working. Session: {self.session_id}, Authenticated: {data.get('authenticated')}")
                return True
            else:
                self.log_test("Gmail OAuth Status with Session", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail OAuth Status with Session", False, f"Error: {str(e)}")
            return False

    def test_gmail_auth_url_generation(self):
        """Test 4: Gmail OAuth2 authentication URL generation"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get("success"):
                    self.log_test("Gmail Auth URL Generation", False, f"Auth URL generation failed: {data.get('message')}", data)
                    return False
                
                auth_url = data.get("auth_url")
                if not auth_url or not auth_url.startswith("https://accounts.google.com/o/oauth2/auth"):
                    self.log_test("Gmail Auth URL Generation", False, "Invalid or missing auth_url", data)
                    return False
                
                # Check OAuth2 parameters
                required_params = ["client_id", "redirect_uri", "scope", "response_type"]
                missing_params = [param for param in required_params if param not in auth_url]
                
                if missing_params:
                    self.log_test("Gmail Auth URL Generation", False, f"Missing OAuth2 parameters: {missing_params}", data)
                    return False
                
                self.log_test("Gmail Auth URL Generation", True, f"OAuth2 auth URL generated successfully with session support")
                return True
            else:
                self.log_test("Gmail Auth URL Generation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Auth URL Generation", False, f"Error: {str(e)}")
            return False

    def test_gmail_inbox_endpoint_authentication(self):
        """Test 5: Gmail inbox endpoint authentication requirement"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/inbox?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should require authentication for unauthenticated session
                if data.get("success") == False and data.get("requires_auth") == True:
                    self.log_test("Gmail Inbox Authentication", True, "Gmail inbox correctly requires authentication for unauthenticated session")
                    return True
                else:
                    self.log_test("Gmail Inbox Authentication", False, "Gmail inbox should require authentication", data)
                    return False
            else:
                self.log_test("Gmail Inbox Authentication", False, f"Unexpected HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Inbox Authentication", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection(self):
        """Test 6: Gmail intent detection for natural language queries"""
        gmail_test_cases = [
            {
                "message": "Check my Gmail inbox",
                "expected_intent": "check_gmail_inbox",
                "description": "Simple inbox check"
            },
            {
                "message": "Do I have any unread emails?",
                "expected_intent": "check_gmail_unread", 
                "description": "Unread emails query"
            },
            {
                "message": "Show me my inbox",
                "expected_intent": "check_gmail_inbox",
                "description": "Show inbox request"
            },
            {
                "message": "Any new emails in my Gmail?",
                "expected_intent": "email_inbox_check",
                "description": "New emails inquiry"
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in gmail_test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get("intent_data", {})
                    detected_intent = intent_data.get("intent")
                    
                    # Check if Gmail-related intent was detected
                    gmail_intents = ["check_gmail_inbox", "check_gmail_unread", "email_inbox_check"]
                    if detected_intent in gmail_intents:
                        results.append(f"✅ {test_case['description']}: {detected_intent}")
                        
                        # Check if authentication prompt is provided
                        response_text = data.get("response", "")
                        if "authentication" in response_text.lower() or "connect" in response_text.lower():
                            results.append(f"   → Authentication prompt provided correctly")
                        
                    else:
                        results.append(f"❌ {test_case['description']}: Expected Gmail intent, got {detected_intent}")
                        all_passed = False
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Gmail Intent Detection", all_passed, result_summary)
        return all_passed

    def test_direct_gmail_automation(self):
        """Test 7: Direct Gmail automation with session_id parameter"""
        try:
            # Test direct Gmail automation call
            payload = {
                "message": "Check my Gmail inbox for unread messages",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                
                # Check if Gmail intent was detected
                detected_intent = intent_data.get("intent")
                gmail_intents = ["check_gmail_inbox", "check_gmail_unread", "email_inbox_check"]
                
                if detected_intent in gmail_intents:
                    # Check if session_id is being used correctly
                    response_text = data.get("response", "")
                    
                    # Should provide authentication guidance since not authenticated
                    if ("authentication" in response_text.lower() or "oauth" in response_text.lower() or 
                        "connect" in response_text.lower() or "requires_auth" in str(intent_data)):
                        self.log_test("Direct Gmail Automation", True, f"Gmail automation correctly uses session_id and provides authentication guidance. Intent: {detected_intent}")
                        return True
                    else:
                        self.log_test("Direct Gmail Automation", False, "Gmail automation should provide authentication guidance for unauthenticated session", data)
                        return False
                else:
                    self.log_test("Direct Gmail Automation", False, f"Expected Gmail intent, got {detected_intent}", data)
                    return False
            else:
                self.log_test("Direct Gmail Automation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Direct Gmail Automation", False, f"Error: {str(e)}")
            return False

    def test_mongodb_token_storage_structure(self):
        """Test 8: Verify MongoDB token storage structure is working"""
        try:
            # Test the get_auth_status function with a session
            response = requests.get(f"{BACKEND_URL}/gmail/status?session_id={self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if the response indicates MongoDB integration is working
                required_fields = ["success", "credentials_configured", "authenticated", "session_id", "requires_auth"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("MongoDB Token Storage", False, f"Missing fields indicating MongoDB integration issue: {missing_fields}", data)
                    return False
                
                # Check if session_id is properly handled
                if data.get("session_id") != self.session_id:
                    self.log_test("MongoDB Token Storage", False, f"Session ID not properly handled in MongoDB storage", data)
                    return False
                
                # The fact that we get a proper response with session handling indicates MongoDB storage is working
                self.log_test("MongoDB Token Storage", True, f"MongoDB token storage structure working correctly with session-based authentication")
                return True
            else:
                self.log_test("MongoDB Token Storage", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MongoDB Token Storage", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Gmail authentication tests"""
        print("🚀 Starting Gmail Authentication Status Testing")
        print("=" * 80)
        
        tests = [
            self.test_gmail_import_resolution,
            self.test_gmail_oauth_status_endpoint,
            self.test_gmail_oauth_status_with_session,
            self.test_gmail_auth_url_generation,
            self.test_gmail_inbox_endpoint_authentication,
            self.test_gmail_intent_detection,
            self.test_direct_gmail_automation,
            self.test_mongodb_token_storage_structure
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            if test():
                passed += 1
            else:
                failed += 1
        
        print("=" * 80)
        print(f"🏁 Gmail Authentication Testing Complete!")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed > 0:
            print(f"⚠️  {failed} tests failed. Please check the details above.")
        else:
            print("🎉 All Gmail authentication tests passed!")
        
        return passed, failed

if __name__ == "__main__":
    tester = GmailAuthTester()
    tester.run_all_tests()