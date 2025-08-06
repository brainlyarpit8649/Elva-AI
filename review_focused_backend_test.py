#!/usr/bin/env python3
"""
Review-Focused Backend Testing for Elva AI
Tests specific areas mentioned in the review request:
1. Chat Error Investigation - Test for "sorry I've encountered an error" responses
2. Gmail Authentication Flow - Test Gmail endpoints
3. API Health Check - Test /api/health endpoint
4. MCP Integration - Test MCP endpoints
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://ed44aeba-7cef-4fcd-8d35-8bddafadc1d4.preview.emergentagent.com/api"

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

    def test_chat_error_investigation(self):
        """Test 1: Chat Error Investigation - Send various messages to check for error responses"""
        print("🔍 Testing Chat Error Investigation...")
        
        test_messages = [
            # Simple greetings
            "Hello",
            "Hi there",
            "Good morning",
            
            # Gmail-related queries
            "Check my Gmail inbox",
            "Show me my unread emails",
            "Any new emails in Gmail?",
            
            # General questions
            "What can you do?",
            "How can you help me?",
            "Tell me about yourself",
            
            # Complex requests
            "Send an email to test@example.com about the project update",
            "Create a meeting for tomorrow at 3pm",
            "Add finish the report to my todo list"
        ]
        
        all_passed = True
        results = []
        error_responses = []
        
        for message in test_messages:
            try:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").lower()
                    
                    # Check for various error message patterns
                    error_phrases = [
                        "sorry i've encountered an error",
                        "sorry, i've encountered an error", 
                        "encountered an error",
                        "error processing your request",
                        "something went wrong",
                        "internal server error",
                        "failed to process"
                    ]
                    
                    has_error = any(phrase in response_text for phrase in error_phrases)
                    
                    if has_error:
                        results.append(f"❌ '{message}': Contains error message - '{response_text[:100]}...'")
                        error_responses.append({
                            "message": message,
                            "response": response_text,
                            "full_data": data
                        })
                        all_passed = False
                    else:
                        results.append(f"✅ '{message}': Clean response ({len(data.get('response', ''))} chars)")
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
                    
                # Small delay between requests
                time.sleep(0.5)
                    
            except Exception as e:
                results.append(f"❌ '{message}': Exception - {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        
        if error_responses:
            error_details = f"\n    ERROR RESPONSES FOUND:\n    " + "\n    ".join([
                f"Message: '{err['message']}' -> Response: '{err['response'][:150]}...'" 
                for err in error_responses
            ])
            result_summary += error_details
        
        self.log_test("Chat Error Investigation", all_passed, result_summary)
        return all_passed, error_responses

    def test_gmail_authentication_flow(self):
        """Test 2: Gmail Authentication Flow - Test Gmail endpoints"""
        print("📧 Testing Gmail Authentication Flow...")
        
        all_tests_passed = True
        
        # Test 2.1: Gmail Status Endpoint
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if credentials are configured
                if data.get("credentials_configured") == True:
                    self.log_test("Gmail Status Check", True, "Gmail credentials properly configured")
                else:
                    self.log_test("Gmail Status Check", False, f"Gmail credentials not configured: {data}")
                    all_tests_passed = False
                    
            else:
                self.log_test("Gmail Status Check", False, f"HTTP {response.status_code}: {response.text}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("Gmail Status Check", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        # Test 2.2: Gmail Auth URL Generation
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("auth_url"):
                    auth_url = data.get("auth_url")
                    
                    # Check if it's a valid Google OAuth URL
                    if "accounts.google.com/o/oauth2/auth" in auth_url:
                        # Check for expected client_id
                        expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                        if expected_client_id in auth_url:
                            self.log_test("Gmail Auth URL Generation", True, f"Valid OAuth URL generated with correct client_id")
                        else:
                            self.log_test("Gmail Auth URL Generation", False, f"Client ID not found in auth URL")
                            all_tests_passed = False
                    else:
                        self.log_test("Gmail Auth URL Generation", False, f"Invalid OAuth URL: {auth_url}")
                        all_tests_passed = False
                else:
                    self.log_test("Gmail Auth URL Generation", False, f"Failed to generate auth URL: {data}")
                    all_tests_passed = False
                    
            else:
                self.log_test("Gmail Auth URL Generation", False, f"HTTP {response.status_code}: {response.text}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("Gmail Auth URL Generation", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        # Test 2.3: Gmail Integration Health
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Look for Gmail integration status in health check
                gmail_integration = None
                
                # Check different possible locations for Gmail status
                if "gmail_api_integration" in data:
                    gmail_integration = data["gmail_api_integration"]
                elif "gmail_integration" in data:
                    gmail_integration = data["gmail_integration"]
                elif "services" in data and "gmail" in data["services"]:
                    gmail_integration = data["services"]["gmail"]
                
                if gmail_integration:
                    if gmail_integration.get("status") == "ready":
                        self.log_test("Gmail Integration Health", True, "Gmail integration status: ready")
                    else:
                        self.log_test("Gmail Integration Health", False, f"Gmail integration status: {gmail_integration.get('status')}")
                        all_tests_passed = False
                else:
                    self.log_test("Gmail Integration Health", False, "Gmail integration status not found in health check")
                    all_tests_passed = False
                    
            else:
                self.log_test("Gmail Integration Health", False, f"HTTP {response.status_code}: {response.text}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("Gmail Integration Health", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        return all_tests_passed

    def test_api_health_check(self):
        """Test 3: API Health Check - Verify /api/health endpoint shows all services running"""
        print("🏥 Testing API Health Check...")
        
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check overall status
                if data.get("status") != "healthy":
                    self.log_test("API Health Check", False, f"Overall status not healthy: {data.get('status')}")
                    return False
                
                # Check for required services
                services_to_check = []
                
                # Check database connection
                if "database" in data:
                    if data["database"] == "connected":
                        services_to_check.append("✅ Database: connected")
                    else:
                        services_to_check.append(f"❌ Database: {data['database']}")
                elif "mongodb" in data:
                    if data["mongodb"] == "connected":
                        services_to_check.append("✅ MongoDB: connected")
                    else:
                        services_to_check.append(f"❌ MongoDB: {data['mongodb']}")
                
                # Check services section if available
                if "services" in data:
                    services = data["services"]
                    for service_name, service_status in services.items():
                        if service_status in ["connected", "ready", "enabled", "configured"]:
                            services_to_check.append(f"✅ {service_name}: {service_status}")
                        else:
                            services_to_check.append(f"❌ {service_name}: {service_status}")
                
                # Check timeout configuration if available
                timeout_info = ""
                if "timeout_config" in data:
                    timeout_config = data["timeout_config"]
                    timeout_info = f"\n    Timeout Configuration: {timeout_config}"
                
                services_summary = "\n    ".join(services_to_check)
                self.log_test("API Health Check", True, f"Health check passed:\n    {services_summary}{timeout_info}")
                return True
                
            else:
                self.log_test("API Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("API Health Check", False, f"Error: {str(e)}")
            return False

    def test_mcp_integration(self):
        """Test 4: MCP Integration - Quick test of MCP endpoints"""
        print("🔗 Testing MCP Integration...")
        
        all_tests_passed = True
        
        # Test 4.1: MCP Root Endpoint
        try:
            # Test with Bearer token authentication
            headers = {"Authorization": "Bearer kumararpit9468"}
            response = requests.get(f"{BACKEND_URL}/mcp", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "ok":
                    self.log_test("MCP Root Endpoint", True, f"MCP connection successful: {data.get('message')}")
                else:
                    self.log_test("MCP Root Endpoint", False, f"Unexpected MCP response: {data}")
                    all_tests_passed = False
                    
            else:
                self.log_test("MCP Root Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("MCP Root Endpoint", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        # Test 4.2: MCP Validate Endpoint (GET)
        try:
            headers = {"Authorization": "Bearer kumararpit9468"}
            response = requests.get(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected WhatsApp number format
                if data.get("number") == "919654030351":
                    self.log_test("MCP Validate GET", True, f"Correct WhatsApp number returned: {data.get('number')}")
                else:
                    self.log_test("MCP Validate GET", False, f"Unexpected number format: {data}")
                    all_tests_passed = False
                    
            else:
                self.log_test("MCP Validate GET", False, f"HTTP {response.status_code}: {response.text}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("MCP Validate GET", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        # Test 4.3: MCP Validate Endpoint (POST)
        try:
            headers = {"Authorization": "Bearer kumararpit9468"}
            response = requests.post(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected WhatsApp number format
                if data.get("number") == "919654030351":
                    self.log_test("MCP Validate POST", True, f"Correct WhatsApp number returned: {data.get('number')}")
                else:
                    self.log_test("MCP Validate POST", False, f"Unexpected number format: {data}")
                    all_tests_passed = False
                    
            else:
                self.log_test("MCP Validate POST", False, f"HTTP {response.status_code}: {response.text}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("MCP Validate POST", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        # Test 4.4: MCP Authentication Test (Invalid Token)
        try:
            headers = {"Authorization": "Bearer invalid_token"}
            response = requests.get(f"{BACKEND_URL}/mcp", headers=headers, timeout=10)
            
            if response.status_code == 401:
                self.log_test("MCP Authentication Test", True, "Correctly rejected invalid token with 401")
            else:
                self.log_test("MCP Authentication Test", False, f"Expected 401 for invalid token, got {response.status_code}")
                all_tests_passed = False
                
        except Exception as e:
            self.log_test("MCP Authentication Test", False, f"Error: {str(e)}")
            all_tests_passed = False
        
        return all_tests_passed

    def run_all_tests(self):
        """Run all review-focused tests"""
        print("🚀 Starting Review-Focused Backend Testing...")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        # Run all tests
        chat_error_passed, error_responses = self.test_chat_error_investigation()
        gmail_auth_passed = self.test_gmail_authentication_flow()
        health_check_passed = self.test_api_health_check()
        mcp_integration_passed = self.test_mcp_integration()
        
        # Summary
        print("=" * 80)
        print("📊 REVIEW-FOCUSED TEST SUMMARY")
        print("=" * 80)
        
        total_tests = 4
        passed_tests = sum([chat_error_passed, gmail_auth_passed, health_check_passed, mcp_integration_passed])
        
        print(f"✅ Chat Error Investigation: {'PASS' if chat_error_passed else 'FAIL'}")
        if not chat_error_passed and error_responses:
            print(f"   🚨 Found {len(error_responses)} error responses!")
            for err in error_responses[:3]:  # Show first 3 errors
                print(f"   - '{err['message']}' -> '{err['response'][:100]}...'")
        
        print(f"✅ Gmail Authentication Flow: {'PASS' if gmail_auth_passed else 'FAIL'}")
        print(f"✅ API Health Check: {'PASS' if health_check_passed else 'FAIL'}")
        print(f"✅ MCP Integration: {'PASS' if mcp_integration_passed else 'FAIL'}")
        
        print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 All review-focused tests PASSED!")
        else:
            print("⚠️  Some tests FAILED - see details above")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "chat_error_investigation": chat_error_passed,
            "gmail_authentication_flow": gmail_auth_passed,
            "api_health_check": health_check_passed,
            "mcp_integration": mcp_integration_passed,
            "error_responses": error_responses
        }

if __name__ == "__main__":
    tester = ReviewFocusedTester()
    results = tester.run_all_tests()