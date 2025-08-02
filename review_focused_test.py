#!/usr/bin/env python3
"""
Review-Focused Backend Testing for Elva AI
Tests the specific areas mentioned in the review request:
1. Basic Chat Functionality - Test /api/chat endpoint with simple messages
2. Gmail Integration Pipeline - Test OAuth URLs, status, and intent detection  
3. Health Check - Test /api/health endpoint
4. Core Backend Services - Verify all integrations are working
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://19b8d7ed-69d2-4a9e-b891-59d19f96fbc4.preview.emergentagent.com/api"

class ReviewFocusedTester:
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

    def test_basic_chat_functionality(self):
        """Test 1: Basic Chat Functionality - Test /api/chat with simple messages"""
        print("💬 Testing Basic Chat Functionality...")
        
        test_messages = [
            "Hello",
            "Hi there",
            "How are you?",
            "What can you help me with?"
        ]
        
        all_passed = True
        results = []
        
        for message in test_messages:
            try:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").lower()
                    
                    # Check for the specific error message mentioned in review
                    if "sorry i've encountered an error" in response_text:
                        results.append(f"❌ '{message}': Returns 'sorry I've encountered an error'")
                        all_passed = False
                    elif not response_text or len(response_text.strip()) == 0:
                        results.append(f"❌ '{message}': Empty response")
                        all_passed = False
                    else:
                        results.append(f"✅ '{message}': Valid response ({len(response_text)} chars)")
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ '{message}': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Basic Chat Functionality", all_passed, result_summary)
        return all_passed

    def test_gmail_oauth_url_generation(self):
        """Test 2: Gmail OAuth URL Generation"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("auth_url"):
                    auth_url = data.get("auth_url")
                    
                    # Check if it's a valid Google OAuth URL
                    if "accounts.google.com/o/oauth2/auth" in auth_url:
                        # Check for required OAuth parameters
                        required_params = ["client_id", "redirect_uri", "scope", "response_type"]
                        missing_params = [param for param in required_params if param not in auth_url]
                        
                        if not missing_params:
                            self.log_test("Gmail OAuth URL Generation", True, f"Valid OAuth URL generated with all required parameters")
                            return True
                        else:
                            self.log_test("Gmail OAuth URL Generation", False, f"Missing OAuth parameters: {missing_params}")
                            return False
                    else:
                        self.log_test("Gmail OAuth URL Generation", False, f"Invalid OAuth URL: {auth_url}")
                        return False
                else:
                    self.log_test("Gmail OAuth URL Generation", False, "Failed to generate auth URL", data)
                    return False
            else:
                self.log_test("Gmail OAuth URL Generation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail OAuth URL Generation", False, f"Error: {str(e)}")
            return False

    def test_gmail_status_endpoint(self):
        """Test 3: Gmail Status Endpoint - Verify credentials are loaded properly"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if credentials are configured
                if data.get("credentials_configured") == True:
                    self.log_test("Gmail Status - Credentials", True, "Gmail credentials properly configured")
                else:
                    self.log_test("Gmail Status - Credentials", False, f"Credentials not configured: {data.get('credentials_configured')}")
                    return False
                
                # Check authentication status (should be false for new session)
                auth_status = data.get("authenticated")
                if auth_status == False:
                    self.log_test("Gmail Status - Authentication", True, "Authentication status correctly shows false for new session")
                else:
                    self.log_test("Gmail Status - Authentication", True, f"Authentication status: {auth_status}")
                
                # Check scopes configuration
                scopes = data.get("scopes", [])
                if len(scopes) > 0:
                    self.log_test("Gmail Status - Scopes", True, f"Gmail scopes configured: {len(scopes)} scopes")
                else:
                    self.log_test("Gmail Status - Scopes", False, "No Gmail scopes configured")
                    return False
                
                return True
            else:
                self.log_test("Gmail Status Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Status Endpoint", False, f"Error: {str(e)}")
            return False

    def test_gmail_intent_detection(self):
        """Test 4: Gmail Intent Detection with queries like 'Check my Gmail inbox'"""
        gmail_queries = [
            "Check my Gmail inbox",
            "Show me my unread emails", 
            "Any new emails?",
            "Check my email"
        ]
        
        all_passed = True
        results = []
        
        for query in gmail_queries:
            try:
                payload = {
                    "message": query,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get("intent_data", {})
                    response_text = data.get("response", "")
                    
                    # Check if Gmail intent is detected or proper authentication prompt is shown
                    gmail_intent_detected = (
                        "gmail" in intent_data.get("intent", "").lower() or
                        "connect gmail" in response_text.lower() or
                        "gmail connection required" in response_text.lower() or
                        intent_data.get("requires_auth") == True
                    )
                    
                    if gmail_intent_detected:
                        results.append(f"✅ '{query}': Gmail intent detected or auth prompt shown")
                    else:
                        results.append(f"❌ '{query}': No Gmail intent detection. Intent: {intent_data.get('intent')}")
                        all_passed = False
                        
                else:
                    results.append(f"❌ '{query}': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ '{query}': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Gmail Intent Detection", all_passed, result_summary)
        return all_passed

    def test_health_endpoint(self):
        """Test 5: Health Check - Test /api/health endpoint for overall system status"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check overall status
                if data.get("status") != "healthy":
                    self.log_test("Health Check - Overall Status", False, f"System not healthy: {data.get('status')}")
                    return False
                
                # Check MongoDB connection
                mongodb_status = data.get("mongodb")
                if mongodb_status != "connected":
                    self.log_test("Health Check - MongoDB", False, f"MongoDB not connected: {mongodb_status}")
                    return False
                else:
                    self.log_test("Health Check - MongoDB", True, "MongoDB connected")
                
                # Check Groq API configuration
                hybrid_ai = data.get("advanced_hybrid_ai_system", {})
                if hybrid_ai.get("groq_api_key") != "configured":
                    self.log_test("Health Check - Groq API", False, "Groq API key not configured")
                    return False
                else:
                    self.log_test("Health Check - Groq API", True, "Groq API configured")
                
                # Check Gmail integration
                gmail_integration = data.get("gmail_api_integration", {})
                if gmail_integration.get("status") == "ready":
                    self.log_test("Health Check - Gmail Integration", True, "Gmail integration ready")
                else:
                    self.log_test("Health Check - Gmail Integration", False, f"Gmail integration not ready: {gmail_integration.get('status')}")
                    return False
                
                # Check N8N webhook
                n8n_status = data.get("n8n_webhook")
                if n8n_status == "configured":
                    self.log_test("Health Check - N8N Webhook", True, "N8N webhook configured")
                else:
                    self.log_test("Health Check - N8N Webhook", False, f"N8N webhook not configured: {n8n_status}")
                    return False
                
                # Check MCP service if available
                mcp_service = data.get("mcp_service", {})
                if mcp_service:
                    if mcp_service.get("status") == "connected":
                        self.log_test("Health Check - MCP Service", True, "MCP service connected")
                    else:
                        self.log_test("Health Check - MCP Service", False, f"MCP service not connected: {mcp_service.get('status')}")
                        return False
                
                self.log_test("Health Check - Overall", True, "All core backend services are healthy")
                return True
            else:
                self.log_test("Health Check Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Health Check Endpoint", False, f"Error: {str(e)}")
            return False

    def test_core_backend_services(self):
        """Test 6: Core Backend Services - Verify all integrations are working"""
        try:
            # Test server connectivity first
            response = requests.get(f"{BACKEND_URL}/", timeout=10)
            if response.status_code != 200:
                self.log_test("Core Services - Server Connectivity", False, f"Server not accessible: HTTP {response.status_code}")
                return False
            
            # Test chat endpoint with a simple message
            chat_payload = {
                "message": "Test message for backend verification",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            chat_response = requests.post(f"{BACKEND_URL}/chat", json=chat_payload, timeout=15)
            if chat_response.status_code != 200:
                self.log_test("Core Services - Chat API", False, f"Chat API not working: HTTP {chat_response.status_code}")
                return False
            
            chat_data = chat_response.json()
            if not chat_data.get("response"):
                self.log_test("Core Services - Chat API", False, "Chat API returns empty response")
                return False
            
            # Test history endpoint
            history_response = requests.get(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
            if history_response.status_code != 200:
                self.log_test("Core Services - History API", False, f"History API not working: HTTP {history_response.status_code}")
                return False
            
            # Test Gmail auth endpoint
            gmail_response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            if gmail_response.status_code != 200:
                self.log_test("Core Services - Gmail API", False, f"Gmail API not working: HTTP {gmail_response.status_code}")
                return False
            
            self.log_test("Core Backend Services", True, "All core backend services (Chat, History, Gmail) are operational")
            return True
            
        except Exception as e:
            self.log_test("Core Backend Services", False, f"Error: {str(e)}")
            return False

    def run_review_focused_tests(self):
        """Run all review-focused tests"""
        print("🚀 Starting Review-Focused Backend Testing for Elva AI")
        print("=" * 60)
        
        test_methods = [
            self.test_basic_chat_functionality,
            self.test_gmail_oauth_url_generation,
            self.test_gmail_status_endpoint,
            self.test_gmail_intent_detection,
            self.test_health_endpoint,
            self.test_core_backend_services
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ Test {test_method.__name__} failed with exception: {e}")
        
        print("=" * 60)
        print(f"📊 REVIEW-FOCUSED TEST SUMMARY")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 ALL REVIEW-FOCUSED TESTS PASSED!")
        else:
            print("⚠️  Some tests failed - check details above")
        
        return passed_tests, total_tests, self.test_results

if __name__ == "__main__":
    tester = ReviewFocusedTester()
    passed, total, results = tester.run_review_focused_tests()
    
    # Save detailed results to file
    with open("/app/review_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": total - passed,
                "success_rate": (passed/total)*100,
                "timestamp": datetime.now().isoformat()
            },
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to /app/review_test_results.json")