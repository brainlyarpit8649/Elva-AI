#!/usr/bin/env python3
"""
Focused MCP Integration Testing for Elva AI Backend
Tests the specific MCP integration requirements from the review request
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://c20efb94-1a9f-42d9-a126-b5157ee976a4.preview.emergentagent.com/api"

class MCPFocusedTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data=None):
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
        print()

    def test_health_check(self):
        """Test basic health check"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check MCP integration status
                mcp_integration = data.get("mcp_integration", {})
                if mcp_integration.get("status") == "enabled":
                    self.log_test("Health Check - MCP Integration", True, f"MCP service enabled at {mcp_integration.get('service_url')}")
                    return True
                else:
                    self.log_test("Health Check - MCP Integration", False, "MCP integration not enabled", data)
                    return False
            else:
                self.log_test("Health Check - MCP Integration", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Health Check - MCP Integration", False, f"Error: {str(e)}")
            return False

    def test_mcp_write_context_direct(self):
        """Test MCP write context endpoint directly"""
        try:
            payload = {
                "session_id": self.session_id,
                "user_id": "test_user",
                "intent": "test_intent",
                "data": {
                    "user_message": "Test message for MCP context",
                    "ai_response": "Test AI response",
                    "intent_data": {"intent": "test_intent", "test_field": "test_value"},
                    "routing_info": {
                        "model": "claude",
                        "confidence": 0.95,
                        "reasoning": "Test routing decision"
                    }
                }
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/write-context", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    self.log_test("MCP Write Context Direct", True, "Context written successfully to MCP service")
                    return True
                else:
                    self.log_test("MCP Write Context Direct", False, f"Write failed: {data.get('message')}", data)
                    return False
            else:
                self.log_test("MCP Write Context Direct", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP Write Context Direct", False, f"Error: {str(e)}")
            return False

    def test_mcp_read_context(self):
        """Test MCP read context endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp/read-context/{self.session_id}", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if context was found and has expected structure
                if "context" in data and data["context"]:
                    context = data["context"]
                    if "user_message" in context.get("data", {}) and "ai_response" in context.get("data", {}):
                        self.log_test("MCP Read Context", True, "Context retrieved successfully from MCP service")
                        return True
                    else:
                        self.log_test("MCP Read Context", False, "Context missing expected fields", data)
                        return False
                elif data.get("success") == False and "not found" in data.get("message", "").lower():
                    self.log_test("MCP Read Context", True, "No context found (expected for new session)")
                    return True
                else:
                    self.log_test("MCP Read Context", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("MCP Read Context", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP Read Context", False, f"Error: {str(e)}")
            return False

    def test_mcp_append_context(self):
        """Test MCP append context endpoint"""
        try:
            payload = {
                "session_id": self.session_id,
                "output": {
                    "action": "test_append_action",
                    "result": "Test append result",
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                },
                "source": "elva_test"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/append-context", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    self.log_test("MCP Append Context", True, "Context appended successfully to MCP service")
                    return True
                else:
                    self.log_test("MCP Append Context", False, f"Append failed: {data.get('message')}", data)
                    return False
            else:
                self.log_test("MCP Append Context", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP Append Context", False, f"Error: {str(e)}")
            return False

    def test_chat_with_mcp_integration(self):
        """Test chat endpoint with MCP context writing"""
        try:
            # Send a message that should trigger MCP context writing
            payload = {
                "message": "Hello, this is a test message for MCP integration testing",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response is valid (AI not giving error messages)
                response_text = data.get("response", "").lower()
                error_indicators = [
                    "sorry i've encountered an error",
                    "sorry, i've encountered an error", 
                    "encountered an error",
                    "something went wrong",
                    "error occurred"
                ]
                
                if any(indicator in response_text for indicator in error_indicators):
                    self.log_test("Chat with MCP Integration", False, "AI giving error response", data)
                    return False
                
                if not data.get("response") or len(data.get("response", "").strip()) == 0:
                    self.log_test("Chat with MCP Integration", False, "Empty AI response", data)
                    return False
                
                # Give MCP time to process
                time.sleep(3)
                
                # Now check if context was written to MCP
                context_response = requests.get(f"{BACKEND_URL}/mcp/read-context/{self.session_id}", timeout=30)
                
                if context_response.status_code == 200:
                    context_data = context_response.json()
                    
                    # Check if our message context was stored
                    if ("context" in context_data and 
                        context_data["context"] and
                        payload["message"] in str(context_data)):
                        self.log_test("Chat with MCP Integration", True, "Chat message successfully stored in MCP context")
                        return True
                    else:
                        self.log_test("Chat with MCP Integration", False, "Context not properly stored in MCP", context_data)
                        return False
                else:
                    self.log_test("Chat with MCP Integration", False, f"Failed to read context: HTTP {context_response.status_code}")
                    return False
            else:
                self.log_test("Chat with MCP Integration", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Chat with MCP Integration", False, f"Error: {str(e)}")
            return False

    def test_ai_response_quality(self):
        """Test that AI responses are working properly"""
        try:
            test_messages = [
                "How are you doing today?",
                "What can you help me with?",
                "Tell me about artificial intelligence"
            ]
            
            successful_responses = 0
            error_responses = 0
            
            for message in test_messages:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=45)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").lower()
                    
                    # Check for error messages
                    error_indicators = [
                        "sorry i've encountered an error",
                        "sorry, i've encountered an error", 
                        "encountered an error",
                        "something went wrong",
                        "error occurred"
                    ]
                    
                    if any(indicator in response_text for indicator in error_indicators):
                        error_responses += 1
                    elif len(response_text.strip()) > 10:  # Valid response
                        successful_responses += 1
                
                time.sleep(2)  # Small delay between requests
            
            if error_responses == 0 and successful_responses >= 2:
                self.log_test("AI Response Quality", True, f"AI responses working correctly: {successful_responses}/3 successful, 0 errors")
                return True
            else:
                self.log_test("AI Response Quality", False, f"AI response issues: {successful_responses} successful, {error_responses} errors out of 3 messages")
                return False
                
        except Exception as e:
            self.log_test("AI Response Quality", False, f"Error: {str(e)}")
            return False

    def test_gmail_integration_status(self):
        """Test Gmail integration status"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("credentials_configured"):
                    self.log_test("Gmail Integration Status", True, "Gmail credentials configured correctly")
                    return True
                else:
                    self.log_test("Gmail Integration Status", False, "Gmail credentials not configured", data)
                    return False
            else:
                self.log_test("Gmail Integration Status", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Integration Status", False, f"Error: {str(e)}")
            return False

    def test_gmail_auth_url_generation(self):
        """Test Gmail OAuth URL generation"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("auth_url"):
                    auth_url = data["auth_url"]
                    if "accounts.google.com" in auth_url and "oauth2" in auth_url:
                        self.log_test("Gmail Auth URL Generation", True, "Valid Gmail OAuth URL generated")
                        return True
                    else:
                        self.log_test("Gmail Auth URL Generation", False, "Invalid OAuth URL format", data)
                        return False
                else:
                    self.log_test("Gmail Auth URL Generation", False, "Failed to generate auth URL", data)
                    return False
            else:
                self.log_test("Gmail Auth URL Generation", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Auth URL Generation", False, f"Error: {str(e)}")
            return False

    def test_intent_detection_and_approval(self):
        """Test intent detection and approval workflow"""
        try:
            # Test email intent detection
            payload = {
                "message": "Send an email to Sarah about the quarterly report",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                
                # Check intent detection
                if intent_data.get("intent") == "send_email":
                    # Check needs approval
                    if data.get("needs_approval") == True:
                        # Check pre-filled data
                        if (intent_data.get("recipient_name") and 
                            intent_data.get("subject") and 
                            intent_data.get("body")):
                            self.log_test("Intent Detection and Approval", True, f"Email intent detected with pre-filled data: recipient={intent_data.get('recipient_name')}")
                            return True
                        else:
                            self.log_test("Intent Detection and Approval", False, "Missing pre-filled data in intent", intent_data)
                            return False
                    else:
                        self.log_test("Intent Detection and Approval", False, "Email intent should need approval", data)
                        return False
                else:
                    self.log_test("Intent Detection and Approval", False, f"Wrong intent detected: {intent_data.get('intent')}", data)
                    return False
            else:
                self.log_test("Intent Detection and Approval", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Intent Detection and Approval", False, f"Error: {str(e)}")
            return False

    def run_focused_tests(self):
        """Run focused MCP integration tests"""
        print("🎯 FOCUSED MCP INTEGRATION TESTING FOR ELVA AI BACKEND")
        print("=" * 70)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print()
        
        tests = [
            ("Health Check", self.test_health_check),
            ("MCP Write Context Direct", self.test_mcp_write_context_direct),
            ("MCP Read Context", self.test_mcp_read_context),
            ("MCP Append Context", self.test_mcp_append_context),
            ("Chat with MCP Integration", self.test_chat_with_mcp_integration),
            ("AI Response Quality", self.test_ai_response_quality),
            ("Gmail Integration Status", self.test_gmail_integration_status),
            ("Gmail Auth URL Generation", self.test_gmail_auth_url_generation),
            ("Intent Detection and Approval", self.test_intent_detection_and_approval),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"🔍 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ EXCEPTION in {test_name}: {str(e)}")
                failed += 1
            
            time.sleep(1)  # Small delay between tests
        
        print("=" * 70)
        print(f"🎯 FOCUSED MCP INTEGRATION TESTING COMPLETED!")
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📊 SUCCESS RATE: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! MCP Integration is working perfectly!")
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
    tester = MCPFocusedTester()
    results = tester.run_focused_tests()
    
    # Save results
    with open("/app/mcp_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/mcp_test_results.json")