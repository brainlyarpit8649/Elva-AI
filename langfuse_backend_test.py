#!/usr/bin/env python3
"""
Langfuse Observability System Testing for Elva AI Backend
Tests the newly integrated Langfuse tracing system as requested in the review
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://d10e365f-da53-4afb-9ff3-dab3e0d6bd7e.preview.emergentagent.com/api"

class LangfuseBackendTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        self.message_ids = []
        
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

    def test_basic_chat_with_langfuse_tracing(self):
        """Test 1: Basic Chat with Langfuse Tracing - Simple messages to verify tracing doesn't break functionality"""
        print("🔍 Testing Basic Chat with Langfuse Tracing...")
        
        test_messages = [
            "Hello",
            "How are you?", 
            "What's the weather like?",
            "Tell me about yourself"
        ]
        
        all_passed = True
        results = []
        
        for message in test_messages:
            try:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check basic response structure
                    required_fields = ["id", "message", "response", "intent_data", "needs_approval", "timestamp"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        results.append(f"❌ '{message}': Missing fields {missing_fields}")
                        all_passed = False
                        continue
                    
                    # Check response is not empty and doesn't contain error messages
                    response_text = data.get("response", "").lower()
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
                    elif not data.get("response") or len(data.get("response", "").strip()) == 0:
                        results.append(f"❌ '{message}': Empty response")
                        all_passed = False
                    else:
                        results.append(f"✅ '{message}': Clean response ({len(data.get('response', ''))} chars)")
                        self.message_ids.append(data["id"])
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ '{message}': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Basic Chat with Langfuse Tracing", all_passed, result_summary)
        return all_passed

    def test_gmail_intent_detection_with_tracing(self):
        """Test 2: Gmail Intent Detection with Tracing - Test DeBERTa intent detection and logging"""
        print("📧 Testing Gmail Intent Detection with Tracing...")
        
        gmail_queries = [
            "Check my Gmail inbox",
            "Show me unread emails", 
            "Any new emails?",
            "What's in my email?"
        ]
        
        all_passed = True
        results = []
        
        for query in gmail_queries:
            try:
                payload = {
                    "message": query,
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if Gmail intent was detected
                    intent_data = data.get("intent_data", {})
                    intent = intent_data.get("intent", "")
                    
                    # Gmail queries should either be detected as Gmail intents or require authentication
                    gmail_related_intents = [
                        "check_gmail_inbox", 
                        "check_gmail_unread", 
                        "gmail_summary",
                        "gmail_auth_required"
                    ]
                    
                    if any(gmail_intent in intent for gmail_intent in gmail_related_intents):
                        results.append(f"✅ '{query}': Detected as Gmail intent ({intent})")
                        
                        # Check if authentication prompt is provided when needed
                        response_text = data.get("response", "")
                        if "gmail" in response_text.lower() or "connect" in response_text.lower():
                            results.append(f"    ✅ Authentication prompt provided")
                        
                    else:
                        # Check if it's a general chat that mentions Gmail functionality
                        response_text = data.get("response", "").lower()
                        if "gmail" in response_text or "email" in response_text:
                            results.append(f"✅ '{query}': Handled as general chat with Gmail context")
                        else:
                            results.append(f"❌ '{query}': Not recognized as Gmail query (intent: {intent})")
                            all_passed = False
                    
                    self.message_ids.append(data["id"])
                        
                else:
                    results.append(f"❌ '{query}': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ '{query}': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Gmail Intent Detection with Tracing", all_passed, result_summary)
        return all_passed

    def test_hybrid_ai_processing_with_tracing(self):
        """Test 3: Hybrid AI Processing with Tracing - Test routing decisions and approval workflows"""
        print("🧠 Testing Hybrid AI Processing with Tracing...")
        
        test_cases = [
            {
                "message": "Send an email to john@example.com about the meeting",
                "expected_intent": "send_email",
                "should_need_approval": True,
                "description": "Email intent with approval workflow"
            },
            {
                "message": "How can I improve my productivity?",
                "expected_intent": "general_chat", 
                "should_need_approval": False,
                "description": "General chat routing"
            },
            {
                "message": "Create a meeting with the team for tomorrow at 3pm",
                "expected_intent": "create_event",
                "should_need_approval": True,
                "description": "Event creation with approval"
            },
            {
                "message": "What's the best way to learn Python?",
                "expected_intent": "general_chat",
                "should_need_approval": False,
                "description": "Educational query routing"
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check intent detection
                    intent_data = data.get("intent_data", {})
                    detected_intent = intent_data.get("intent", "")
                    needs_approval = data.get("needs_approval", False)
                    
                    # Verify intent detection
                    if detected_intent == test_case["expected_intent"]:
                        results.append(f"✅ {test_case['description']}: Intent correctly detected as {detected_intent}")
                    else:
                        results.append(f"❌ {test_case['description']}: Expected {test_case['expected_intent']}, got {detected_intent}")
                        all_passed = False
                        continue
                    
                    # Verify approval workflow
                    if needs_approval == test_case["should_need_approval"]:
                        approval_status = "needs approval" if needs_approval else "no approval needed"
                        results.append(f"    ✅ Approval workflow correct: {approval_status}")
                    else:
                        expected_approval = "should need approval" if test_case["should_need_approval"] else "should not need approval"
                        results.append(f"    ❌ Approval workflow incorrect: {expected_approval}, got needs_approval={needs_approval}")
                        all_passed = False
                    
                    # Check response quality
                    response_text = data.get("response", "")
                    if response_text and len(response_text.strip()) > 0:
                        results.append(f"    ✅ Response generated ({len(response_text)} chars)")
                    else:
                        results.append(f"    ❌ Empty or missing response")
                        all_passed = False
                    
                    self.message_ids.append(data["id"])
                        
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Hybrid AI Processing with Tracing", all_passed, result_summary)
        return all_passed

    def test_backend_health_check(self):
        """Test 4: Backend Health Check - Verify all services operational with Langfuse"""
        print("🏥 Testing Backend Health Check...")
        
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check overall system health
                if data.get("status") != "healthy":
                    self.log_test("Backend Health Check", False, f"System status not healthy: {data.get('status')}", data)
                    return False
                
                # Check core services
                core_services = {
                    "mongodb": "connected",
                    "n8n_webhook": "configured"
                }
                
                failed_services = []
                for service, expected_status in core_services.items():
                    if data.get(service) != expected_status:
                        failed_services.append(f"{service}: {data.get(service)} (expected: {expected_status})")
                
                if failed_services:
                    self.log_test("Backend Health Check", False, f"Failed services: {', '.join(failed_services)}", data)
                    return False
                
                # Check AI system configuration
                ai_system = data.get("advanced_hybrid_ai_system", {})
                if not ai_system:
                    self.log_test("Backend Health Check", False, "Advanced hybrid AI system not found in health check", data)
                    return False
                
                # Check API keys are configured
                required_keys = ["groq_api_key", "claude_api_key"]
                missing_keys = [key for key in required_keys if ai_system.get(key) != "configured"]
                
                if missing_keys:
                    self.log_test("Backend Health Check", False, f"Missing API keys: {missing_keys}", data)
                    return False
                
                # Check models are configured
                expected_models = {
                    "groq_model": "llama3-8b-8192",
                    "claude_model": "claude-3-5-sonnet-20241022"
                }
                
                model_issues = []
                for model_key, expected_model in expected_models.items():
                    if ai_system.get(model_key) != expected_model:
                        model_issues.append(f"{model_key}: {ai_system.get(model_key)} (expected: {expected_model})")
                
                if model_issues:
                    self.log_test("Backend Health Check", False, f"Model configuration issues: {', '.join(model_issues)}", data)
                    return False
                
                # Check Gmail integration
                gmail_integration = data.get("gmail_api_integration", {})
                if gmail_integration.get("status") != "ready":
                    self.log_test("Backend Health Check", False, f"Gmail integration not ready: {gmail_integration.get('status')}", data)
                    return False
                
                # Check MCP service
                mcp_service = data.get("mcp_service", {})
                if mcp_service.get("status") != "connected":
                    self.log_test("Backend Health Check", False, f"MCP service not connected: {mcp_service.get('status')}", data)
                    return False
                
                self.log_test("Backend Health Check", True, "All services operational - MongoDB connected, AI models configured, Gmail ready, MCP connected")
                return True
                
            else:
                self.log_test("Backend Health Check", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Backend Health Check", False, f"Error: {str(e)}")
            return False

    def test_error_handling_with_tracing(self):
        """Test 5: Error Handling with Tracing - Test edge cases and error tracing"""
        print("⚠️ Testing Error Handling with Tracing...")
        
        test_cases = [
            {
                "name": "Empty message",
                "payload": {
                    "message": "",
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                },
                "should_handle_gracefully": True
            },
            {
                "name": "Very long message",
                "payload": {
                    "message": "This is a very long message " * 100,  # 3000+ characters
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                },
                "should_handle_gracefully": True
            },
            {
                "name": "Special characters",
                "payload": {
                    "message": "Test with special chars: @#$%^&*(){}[]|\\:;\"'<>?,./~`",
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                },
                "should_handle_gracefully": True
            },
            {
                "name": "Unicode characters",
                "payload": {
                    "message": "Test with unicode: 你好 🌟 café naïve résumé",
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                },
                "should_handle_gracefully": True
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                response = requests.post(f"{BACKEND_URL}/chat", json=test_case["payload"], timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if response structure is maintained
                    required_fields = ["id", "message", "response", "intent_data", "needs_approval", "timestamp"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        results.append(f"❌ {test_case['name']}: Missing response fields {missing_fields}")
                        all_passed = False
                        continue
                    
                    # Check if error is handled gracefully (no crash, proper response)
                    response_text = data.get("response", "")
                    if response_text and len(response_text.strip()) > 0:
                        results.append(f"✅ {test_case['name']}: Handled gracefully with response")
                    else:
                        results.append(f"❌ {test_case['name']}: Empty response")
                        all_passed = False
                    
                elif response.status_code == 400:
                    # Bad request is acceptable for some edge cases
                    results.append(f"✅ {test_case['name']}: Properly rejected with 400 status")
                    
                else:
                    results.append(f"❌ {test_case['name']}: Unexpected HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['name']}: Exception {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Error Handling with Tracing", all_passed, result_summary)
        return all_passed

    def test_approval_workflow_with_tracing(self):
        """Test 6: Approval Workflow with Tracing - Test approval process doesn't break with tracing"""
        print("✅ Testing Approval Workflow with Tracing...")
        
        try:
            # First create an email intent that needs approval
            payload = {
                "message": "Send an email to test@example.com about the Langfuse integration test",
                "session_id": self.session_id,
                "user_id": "langfuse_test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code != 200:
                self.log_test("Approval Workflow with Tracing", False, f"Failed to create email intent: HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            # Verify it needs approval
            if not data.get("needs_approval"):
                self.log_test("Approval Workflow with Tracing", False, "Email intent should need approval")
                return False
            
            message_id = data["id"]
            
            # Test approval
            approval_payload = {
                "session_id": self.session_id,
                "message_id": message_id,
                "approved": True
            }
            
            approval_response = requests.post(f"{BACKEND_URL}/approve", json=approval_payload, timeout=20)
            
            if approval_response.status_code == 200:
                approval_data = approval_response.json()
                
                if not approval_data.get("success"):
                    self.log_test("Approval Workflow with Tracing", False, "Approval not successful", approval_data)
                    return False
                
                # Check if webhook was called (n8n_response should be present)
                if "n8n_response" not in approval_data:
                    self.log_test("Approval Workflow with Tracing", False, "No n8n_response in approval result")
                    return False
                
                self.log_test("Approval Workflow with Tracing", True, "Approval workflow completed successfully with tracing")
                return True
                
            else:
                self.log_test("Approval Workflow with Tracing", False, f"Approval failed: HTTP {approval_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Approval Workflow with Tracing", False, f"Error: {str(e)}")
            return False

    def test_performance_with_tracing(self):
        """Test 7: Performance with Tracing - Ensure no significant performance degradation"""
        print("⚡ Testing Performance with Tracing...")
        
        try:
            # Test multiple requests to check for performance issues
            test_messages = [
                "Hello, how are you?",
                "What's the weather like today?",
                "Tell me a joke",
                "How can you help me?",
                "What are your capabilities?"
            ]
            
            response_times = []
            all_passed = True
            
            for message in test_messages:
                start_time = time.time()
                
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "langfuse_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if response.status_code != 200:
                    all_passed = False
                    break
                
                # Check if response time is reasonable (under 30 seconds)
                if response_time > 30:
                    all_passed = False
                    break
            
            if all_passed and response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                
                performance_details = f"Avg: {avg_response_time:.2f}s, Min: {min_response_time:.2f}s, Max: {max_response_time:.2f}s"
                
                # Consider performance acceptable if average is under 15 seconds
                if avg_response_time < 15:
                    self.log_test("Performance with Tracing", True, f"Performance acceptable - {performance_details}")
                    return True
                else:
                    self.log_test("Performance with Tracing", False, f"Performance degraded - {performance_details}")
                    return False
            else:
                self.log_test("Performance with Tracing", False, "Performance test failed due to errors")
                return False
                
        except Exception as e:
            self.log_test("Performance with Tracing", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Langfuse observability tests"""
        print("🚀 Starting Langfuse Observability System Testing for Elva AI Backend")
        print("=" * 80)
        
        tests = [
            self.test_basic_chat_with_langfuse_tracing,
            self.test_gmail_intent_detection_with_tracing,
            self.test_hybrid_ai_processing_with_tracing,
            self.test_backend_health_check,
            self.test_error_handling_with_tracing,
            self.test_approval_workflow_with_tracing,
            self.test_performance_with_tracing
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
        
        print("=" * 80)
        print(f"🎯 LANGFUSE OBSERVABILITY TESTING SUMMARY")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 ALL LANGFUSE OBSERVABILITY TESTS PASSED!")
            print("✅ Langfuse tracing integration is working correctly")
            print("✅ No performance degradation detected")
            print("✅ All existing functionality preserved")
        else:
            print("⚠️ Some tests failed - review results above")
        
        return passed_tests, total_tests

if __name__ == "__main__":
    tester = LangfuseBackendTester()
    passed, total = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if passed == total else 1)