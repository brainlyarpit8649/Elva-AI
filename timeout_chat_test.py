#!/usr/bin/env python3
"""
Timeout-Protected Chat System Testing for Elva AI
Tests the newly implemented timeout protection with specific scenarios from review request
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL - using localhost for testing
BACKEND_URL = "http://localhost:8001/api"

class TimeoutChatTester:
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

    def test_basic_chat_functionality(self):
        """Test 1: Basic Chat Functionality - Simple messages under 10 seconds"""
        print("🔧 Testing Basic Chat Functionality...")
        
        test_messages = [
            "Hello",
            "How are you?", 
            "What can you help me with?"
        ]
        
        all_passed = True
        results = []
        
        for message in test_messages:
            try:
                start_time = time.time()
                
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                end_time = time.time()
                response_time = end_time - start_time
                
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
                    elif response_time > 10.0:
                        results.append(f"❌ '{message}': Response took {response_time:.2f}s (>10s)")
                        all_passed = False
                    else:
                        results.append(f"✅ '{message}': Clean response in {response_time:.2f}s")
                        self.message_ids.append(data["id"])
                        
                else:
                    results.append(f"❌ '{message}': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ '{message}': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Basic Chat Functionality Test", all_passed, result_summary)
        return all_passed

    def test_timeout_protection(self):
        """Test 2: Timeout Protection - Verify 50 second global timeout"""
        print("⏱️ Testing Timeout Protection...")
        
        try:
            start_time = time.time()
            
            # Test with a complex message that might take longer to process
            payload = {
                "message": "Create a detailed project plan for developing a machine learning application with multiple phases including data collection, preprocessing, model training, validation, deployment, and monitoring, and also send emails to all stakeholders about the timeline and schedule meetings with the development team for each phase",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=60)  # Allow 60s to test 50s timeout
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Check if response completed within 50 seconds
                if response_time <= 50.0:
                    self.log_test("Timeout Protection Test", True, f"Response completed in {response_time:.2f}s (within 50s timeout)")
                    self.message_ids.append(data["id"])
                    return True
                else:
                    self.log_test("Timeout Protection Test", False, f"Response took {response_time:.2f}s (exceeded 50s timeout)")
                    return False
            else:
                self.log_test("Timeout Protection Test", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except requests.exceptions.Timeout:
            self.log_test("Timeout Protection Test", False, "Request timed out at client level")
            return False
        except Exception as e:
            self.log_test("Timeout Protection Test", False, f"Error: {str(e)}")
            return False

    def test_fallback_system(self):
        """Test 3: Fallback System - Groq+Letta → Groq only → Simple response"""
        print("🔄 Testing Fallback System...")
        
        try:
            # Test multiple messages to potentially trigger different fallback levels
            test_cases = [
                {
                    "message": "Tell me about artificial intelligence and machine learning",
                    "description": "General knowledge query"
                },
                {
                    "message": "What's the weather like today?",
                    "description": "Simple question"
                },
                {
                    "message": "Help me understand quantum computing",
                    "description": "Complex topic"
                }
            ]
            
            all_passed = True
            results = []
            
            for test_case in test_cases:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    intent_data = data.get("intent_data", {})
                    
                    # Check for degraded mode messages (natural fallback indicators)
                    degraded_indicators = [
                        "got it! let's keep chatting while i catch up",
                        "i'm with you! processing your request now",
                        "on it! give me just a moment",
                        "got it! working on your request"
                    ]
                    
                    has_degraded_message = any(indicator in response_text.lower() for indicator in degraded_indicators)
                    fallback_mode = intent_data.get("fallback_mode")
                    
                    if response_text and len(response_text.strip()) > 0:
                        fallback_info = f"Fallback mode: {fallback_mode}" if fallback_mode else "Normal processing"
                        degraded_info = " (with degraded message)" if has_degraded_message else ""
                        results.append(f"✅ {test_case['description']}: Response received - {fallback_info}{degraded_info}")
                        self.message_ids.append(data["id"])
                    else:
                        results.append(f"❌ {test_case['description']}: Empty response")
                        all_passed = False
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            self.log_test("Fallback System Test", all_passed, result_summary)
            return all_passed
            
        except Exception as e:
            self.log_test("Fallback System Test", False, f"Error: {str(e)}")
            return False

    def test_letta_memory_functionality(self):
        """Test 4: Re-enabled Letta Memory Test"""
        print("🧠 Testing Re-enabled Letta Memory...")
        
        try:
            # Test memory storage
            memory_store_payload = {
                "message": "Remember that my name is John and I work at Google",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            store_response = requests.post(f"{BACKEND_URL}/chat", json=memory_store_payload, timeout=20)
            
            if store_response.status_code != 200:
                self.log_test("Letta Memory Test - Storage", False, f"Memory storage failed: HTTP {store_response.status_code}")
                return False
            
            store_data = store_response.json()
            store_response_text = store_data.get("response", "").lower()
            
            # Check for memory confirmation
            memory_confirmations = [
                "i'll remember",
                "got it",
                "noted",
                "stored",
                "remembered"
            ]
            
            has_confirmation = any(conf in store_response_text for conf in memory_confirmations)
            
            if not has_confirmation:
                self.log_test("Letta Memory Test - Storage", False, f"No memory confirmation in response: {store_response_text}")
                return False
            
            # Wait a moment for memory to be processed
            time.sleep(2)
            
            # Test memory retrieval
            memory_recall_payload = {
                "message": "What do you remember about me?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            recall_response = requests.post(f"{BACKEND_URL}/chat", json=memory_recall_payload, timeout=20)
            
            if recall_response.status_code != 200:
                self.log_test("Letta Memory Test - Retrieval", False, f"Memory retrieval failed: HTTP {recall_response.status_code}")
                return False
            
            recall_data = recall_response.json()
            recall_response_text = recall_data.get("response", "").lower()
            
            # Check if memory was recalled
            memory_indicators = ["john", "google", "name", "work"]
            recalled_info = [indicator for indicator in memory_indicators if indicator in recall_response_text]
            
            if len(recalled_info) >= 2:  # Should recall at least name and work info
                self.log_test("Letta Memory Test", True, f"Memory working correctly - stored and recalled: {recalled_info}")
                self.message_ids.extend([store_data["id"], recall_data["id"]])
                return True
            else:
                self.log_test("Letta Memory Test", False, f"Memory recall incomplete. Found: {recalled_info}, Response: {recall_response_text}")
                return False
                
        except Exception as e:
            self.log_test("Letta Memory Test", False, f"Error: {str(e)}")
            return False

    def test_database_optimization(self):
        """Test 5: Database Optimization - Fast conversation history loading"""
        print("💾 Testing Database Optimization...")
        
        try:
            # Test conversation history loading speed
            start_time = time.time()
            
            response = requests.get(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
            
            end_time = time.time()
            load_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                history = data.get("history", [])
                
                # Check if history loads quickly (under 5 seconds)
                if load_time <= 5.0:
                    self.log_test("Database Optimization - History Loading", True, f"History loaded in {load_time:.2f}s with {len(history)} messages")
                else:
                    self.log_test("Database Optimization - History Loading", False, f"History loading took {load_time:.2f}s (>5s)")
                    return False
                
                # Test message saving speed by sending a quick message
                start_time = time.time()
                
                save_payload = {
                    "message": "Test message for database optimization",
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                save_response = requests.post(f"{BACKEND_URL}/chat", json=save_payload, timeout=15)
                
                end_time = time.time()
                save_time = end_time - start_time
                
                if save_response.status_code == 200:
                    if save_time <= 10.0:  # Should save quickly
                        self.log_test("Database Optimization - Message Saving", True, f"Message saved in {save_time:.2f}s")
                        return True
                    else:
                        self.log_test("Database Optimization - Message Saving", False, f"Message saving took {save_time:.2f}s (>10s)")
                        return False
                else:
                    self.log_test("Database Optimization - Message Saving", False, f"Message save failed: HTTP {save_response.status_code}")
                    return False
            else:
                self.log_test("Database Optimization - History Loading", False, f"History loading failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Database Optimization Test", False, f"Error: {str(e)}")
            return False

    def test_health_check_timeout_config(self):
        """Test 6: Health Check - Proper timeout configuration"""
        print("🏥 Testing Health Check Timeout Configuration...")
        
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for timeout configuration
                timeout_config = data.get("timeout_config", {})
                
                if not timeout_config:
                    self.log_test("Health Check - Timeout Config", False, "No timeout_config in health response")
                    return False
                
                # Check required timeout settings
                required_timeouts = {
                    "global_chat_timeout": 50.0,
                    "memory_operation_timeout": 15.0,
                    "database_operation_timeout": 10.0,
                    "ai_response_timeout": 30.0
                }
                
                missing_timeouts = []
                incorrect_timeouts = []
                
                for timeout_name, expected_value in required_timeouts.items():
                    if timeout_name not in timeout_config:
                        missing_timeouts.append(timeout_name)
                    elif timeout_config[timeout_name] != expected_value:
                        incorrect_timeouts.append(f"{timeout_name}: expected {expected_value}, got {timeout_config[timeout_name]}")
                
                if missing_timeouts:
                    self.log_test("Health Check - Timeout Config", False, f"Missing timeout configs: {missing_timeouts}")
                    return False
                
                if incorrect_timeouts:
                    self.log_test("Health Check - Timeout Config", False, f"Incorrect timeout values: {incorrect_timeouts}")
                    return False
                
                # Check semantic memory status
                services = data.get("services", {})
                memory_status = services.get("semantic_memory", "unknown")
                
                if memory_status == "enabled":
                    self.log_test("Health Check - Semantic Memory", True, "Semantic memory is enabled")
                else:
                    self.log_test("Health Check - Semantic Memory", False, f"Semantic memory status: {memory_status}")
                
                # Check overall health
                if data.get("status") == "healthy":
                    self.log_test("Health Check - Timeout Config", True, f"All timeout configurations correct: {timeout_config}")
                    return True
                else:
                    self.log_test("Health Check - Timeout Config", False, f"System not healthy: {data.get('status')}")
                    return False
            else:
                self.log_test("Health Check - Timeout Config", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Health Check - Timeout Config", False, f"Error: {str(e)}")
            return False

    def test_degraded_mode_graceful_handling(self):
        """Test 7: Degraded Mode - Natural conversation continuation"""
        print("🛡️ Testing Degraded Mode Graceful Handling...")
        
        try:
            # Send multiple messages to potentially trigger degraded mode
            test_messages = [
                "Tell me about the latest developments in AI",
                "What are your capabilities?",
                "How can you help me with my work?",
                "Explain machine learning to me"
            ]
            
            all_passed = True
            results = []
            degraded_mode_detected = False
            
            for message in test_messages:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=25)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    
                    # Check for natural degraded mode messages
                    degraded_messages = [
                        "got it! let's keep chatting while i catch up on memory",
                        "i'm with you! processing your request now",
                        "on it! give me just a moment",
                        "got it! working on your request"
                    ]
                    
                    has_degraded_message = any(deg_msg in response_text.lower() for deg_msg in degraded_messages)
                    
                    if has_degraded_message:
                        degraded_mode_detected = True
                        results.append(f"✅ '{message[:30]}...': Natural degraded mode message detected")
                    else:
                        results.append(f"✅ '{message[:30]}...': Normal response received")
                    
                    # Ensure no error messages
                    error_phrases = [
                        "sorry i've encountered an error",
                        "sorry, i've encountered an error"
                    ]
                    
                    has_error = any(phrase in response_text.lower() for phrase in error_phrases)
                    
                    if has_error:
                        results.append(f"❌ '{message[:30]}...': Contains error message")
                        all_passed = False
                    
                    self.message_ids.append(data["id"])
                else:
                    results.append(f"❌ '{message[:30]}...': HTTP {response.status_code}")
                    all_passed = False
            
            result_summary = "\n    ".join(results)
            
            if degraded_mode_detected:
                self.log_test("Degraded Mode Test", all_passed, f"Degraded mode detected and handled gracefully:\n    {result_summary}")
            else:
                self.log_test("Degraded Mode Test", all_passed, f"No degraded mode triggered, all responses normal:\n    {result_summary}")
            
            return all_passed
            
        except Exception as e:
            self.log_test("Degraded Mode Test", False, f"Error: {str(e)}")
            return False

    def test_session_management(self):
        """Test 8: Session Management - New chat and clear history"""
        print("📝 Testing Session Management...")
        
        try:
            # Test clearing chat history
            clear_response = requests.delete(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
            
            if clear_response.status_code == 200:
                clear_data = clear_response.json()
                
                if clear_data.get("success"):
                    # Verify history is cleared
                    verify_response = requests.get(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        history = verify_data.get("history", [])
                        
                        if len(history) == 0:
                            self.log_test("Session Management - Clear History", True, "Chat history successfully cleared")
                            
                            # Test new session functionality
                            new_session_id = str(uuid.uuid4())
                            
                            new_session_payload = {
                                "message": "Hello, this is a new session",
                                "session_id": new_session_id,
                                "user_id": "test_user"
                            }
                            
                            new_session_response = requests.post(f"{BACKEND_URL}/chat", json=new_session_payload, timeout=15)
                            
                            if new_session_response.status_code == 200:
                                self.log_test("Session Management - New Session", True, "New session created successfully")
                                return True
                            else:
                                self.log_test("Session Management - New Session", False, f"New session failed: HTTP {new_session_response.status_code}")
                                return False
                        else:
                            self.log_test("Session Management - Clear History", False, f"History not cleared, still has {len(history)} messages")
                            return False
                    else:
                        self.log_test("Session Management - Clear History", False, f"History verification failed: HTTP {verify_response.status_code}")
                        return False
                else:
                    self.log_test("Session Management - Clear History", False, "Clear history success flag not set")
                    return False
            else:
                self.log_test("Session Management - Clear History", False, f"Clear history failed: HTTP {clear_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Session Management Test", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all timeout-protected chat system tests"""
        print("🚀 Starting Timeout-Protected Chat System Testing...")
        print("=" * 80)
        
        test_methods = [
            self.test_basic_chat_functionality,
            self.test_timeout_protection,
            self.test_fallback_system,
            self.test_letta_memory_functionality,
            self.test_database_optimization,
            self.test_health_check_timeout_config,
            self.test_degraded_mode_graceful_handling,
            self.test_session_management
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ CRITICAL ERROR in {test_method.__name__}: {str(e)}")
        
        print("=" * 80)
        print(f"🎯 TIMEOUT-PROTECTED CHAT SYSTEM TEST RESULTS:")
        print(f"   Passed: {passed_tests}/{total_tests} tests")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 ALL TIMEOUT PROTECTION TESTS PASSED!")
            return True
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed")
            return False

    def generate_summary(self):
        """Generate test summary"""
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print("\n" + "="*80)
        print("📊 DETAILED TEST SUMMARY")
        print("="*80)
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} - {result['test']}")
            if result["details"]:
                print(f"    {result['details']}")
        
        print(f"\n🎯 FINAL RESULTS: {passed}/{total} tests passed ({(passed/total)*100:.1f}% success rate)")
        
        return passed == total

if __name__ == "__main__":
    tester = TimeoutChatTester()
    success = tester.run_all_tests()
    tester.generate_summary()
    
    if success:
        print("\n🎉 TIMEOUT-PROTECTED CHAT SYSTEM IS WORKING PERFECTLY!")
    else:
        print("\n⚠️  SOME TIMEOUT PROTECTION FEATURES NEED ATTENTION")