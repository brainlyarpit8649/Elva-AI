#!/usr/bin/env python3
"""
Critical Fixes Testing for Elva AI - Focus on Review Request Issues
Tests the specific fixes mentioned in the review request
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://395a2c43-f9bd-494c-beb2-dd30fbdf7e7e.preview.emergentagent.com/api"

class CriticalFixesTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        self.message_ids = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    Details: {details}")
        print()

    def test_intent_detection_fix(self):
        """Test 1: Intent Detection Fix - JSON escaping issues resolved"""
        try:
            payload = {
                "message": "Send an email to john@example.com about the project",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                
                # Check if send_email intent is properly detected (not general_chat)
                if intent_data.get("intent") == "send_email":
                    self.log_test("Intent Detection Fix", True, "send_email intent correctly detected, not classified as general_chat")
                    
                    # Check needs_approval is properly set to true
                    if data.get("needs_approval") == True:
                        self.log_test("Send Email Approval Modal Fix", True, "needs_approval=true properly set for send_email intent")
                        
                        # Check structured intent data is present
                        required_fields = ["recipient_name", "subject", "body"]
                        missing_fields = [field for field in required_fields if not intent_data.get(field)]
                        
                        if not missing_fields:
                            self.log_test("Gmail Response Structure Fix", True, "Structured intent data with all required fields present")
                            self.message_ids.append(data["id"])
                            return True
                        else:
                            self.log_test("Gmail Response Structure Fix", False, f"Missing structured data fields: {missing_fields}")
                            return False
                    else:
                        self.log_test("Send Email Approval Modal Fix", False, f"needs_approval should be true, got {data.get('needs_approval')}")
                        return False
                else:
                    self.log_test("Intent Detection Fix", False, f"Expected send_email, got {intent_data.get('intent')}")
                    return False
            else:
                self.log_test("Intent Detection Fix", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Intent Detection Fix", False, f"Error: {str(e)}")
            return False

    def test_error_message_resolution(self):
        """Test 2: Error Message Resolution - No more 'sorry I've encountered an error'"""
        try:
            test_messages = [
                "Hello, how are you?",
                "What's the weather like?",
                "Tell me a joke"
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
                        "encountered an error"
                    ]
                    
                    has_error = any(phrase in response_text for phrase in error_phrases)
                    
                    if has_error:
                        results.append(f"❌ '{message}': Contains error message")
                        all_passed = False
                    else:
                        results.append(f"✅ '{message}': Clean response")
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            self.log_test("Error Message Resolution", all_passed, result_summary)
            return all_passed
            
        except Exception as e:
            self.log_test("Error Message Resolution", False, f"Error: {str(e)}")
            return False

    def test_gmail_credentials_update(self):
        """Test 3: Gmail Credentials Update - New OAuth2 configuration working"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("auth_url"):
                    auth_url = data.get("auth_url")
                    
                    # Check if new client_id is in the URL
                    expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                    if expected_client_id in auth_url:
                        # Check redirect URI
                        expected_redirect = "https://395a2c43-f9bd-494c-beb2-dd30fbdf7e7e.preview.emergentagent.com/api/gmail/callback"
                        if expected_redirect in auth_url:
                            self.log_test("Gmail Credentials Update", True, "New OAuth2 credentials working with correct client_id and redirect URI")
                            return True
                        else:
                            self.log_test("Gmail Credentials Update", False, "Incorrect redirect URI in auth URL")
                            return False
                    else:
                        self.log_test("Gmail Credentials Update", False, "New client_id not found in auth URL")
                        return False
                else:
                    self.log_test("Gmail Credentials Update", False, "Failed to generate auth URL")
                    return False
            else:
                self.log_test("Gmail Credentials Update", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Credentials Update", False, f"Error: {str(e)}")
            return False

    def test_groq_api_functionality(self):
        """Test 4: Groq API Functionality - New API key working"""
        try:
            payload = {
                "message": "Create a meeting with the team for tomorrow at 3pm about the project review",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response is generated (not error)
                response_text = data.get("response", "")
                if not response_text or "sorry i've encountered an error" in response_text.lower():
                    self.log_test("Groq API Functionality", False, "Empty response or error message from Groq")
                    return False
                    
                # Check intent detection worked
                intent_data = data.get("intent_data", {})
                if intent_data.get("intent") == "create_event":
                    # Check structured data extraction
                    required_fields = ["event_title", "date", "time"]
                    missing_fields = [field for field in required_fields if not intent_data.get(field)]
                    
                    if not missing_fields:
                        self.log_test("Groq API Functionality", True, "Groq API working correctly with intent detection and structured data extraction")
                        self.message_ids.append(data["id"])
                        return True
                    else:
                        self.log_test("Groq API Functionality", False, f"Missing structured data: {missing_fields}")
                        return False
                else:
                    self.log_test("Groq API Functionality", False, f"Intent detection failed, got: {intent_data.get('intent')}")
                    return False
            else:
                self.log_test("Groq API Functionality", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Groq API Functionality", False, f"Error: {str(e)}")
            return False

    def test_health_check_integration(self):
        """Test 5: Health Check - All integrations working"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check overall status
                if data.get("status") != "healthy":
                    self.log_test("Health Check Integration", False, f"System status not healthy: {data.get('status')}")
                    return False
                
                # Check Gmail integration
                gmail_integration = data.get("gmail_api_integration", {})
                if gmail_integration.get("status") != "ready":
                    self.log_test("Health Check Integration", False, f"Gmail integration not ready: {gmail_integration.get('status')}")
                    return False
                
                # Check Groq API
                hybrid_ai = data.get("advanced_hybrid_ai_system", {})
                if hybrid_ai.get("groq_api_key") != "configured":
                    self.log_test("Health Check Integration", False, "Groq API key not configured")
                    return False
                
                # Check N8N webhook
                if data.get("n8n_webhook") != "configured":
                    self.log_test("Health Check Integration", False, "N8N webhook not configured")
                    return False
                
                self.log_test("Health Check Integration", True, "All integrations (Gmail, Groq, N8N) are healthy and configured")
                return True
            else:
                self.log_test("Health Check Integration", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Health Check Integration", False, f"Error: {str(e)}")
            return False

    def test_n8n_webhook_connectivity(self):
        """Test 6: N8N Webhook Connectivity - Updated webhook URL working"""
        if not self.message_ids:
            self.log_test("N8N Webhook Connectivity", False, "No message IDs available for approval test")
            return False
            
        try:
            # Use the last message ID (should be an action intent)
            message_id = self.message_ids[-1]
            
            approval_payload = {
                "session_id": self.session_id,
                "message_id": message_id,
                "approved": True
            }
            
            response = requests.post(f"{BACKEND_URL}/approve", json=approval_payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and "n8n_response" in data:
                    self.log_test("N8N Webhook Connectivity", True, "N8N webhook called successfully")
                    return True
                else:
                    self.log_test("N8N Webhook Connectivity", False, "No n8n_response in approval result")
                    return False
            else:
                self.log_test("N8N Webhook Connectivity", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("N8N Webhook Connectivity", False, f"Error: {str(e)}")
            return False

    def run_critical_tests(self):
        """Run all critical fixes tests"""
        print("🔧 CRITICAL FIXES TESTING FOR ELVA AI")
        print("=" * 50)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print("=" * 50)
        print()
        
        tests = [
            self.test_intent_detection_fix,
            self.test_error_message_resolution,
            self.test_gmail_credentials_update,
            self.test_groq_api_functionality,
            self.test_health_check_integration,
            self.test_n8n_webhook_connectivity
        ]
        
        passed = 0
        for test in tests:
            if test():
                passed += 1
        
        print("=" * 50)
        print(f"🔧 CRITICAL FIXES RESULTS: {passed}/{len(tests)} passed")
        
        if passed == len(tests):
            print("✅ ALL CRITICAL FIXES VERIFIED SUCCESSFULLY!")
        else:
            print("❌ SOME CRITICAL FIXES NEED ATTENTION")
        
        print("=" * 50)
        
        return passed, len(tests)

if __name__ == "__main__":
    tester = CriticalFixesTester()
    tester.run_critical_tests()