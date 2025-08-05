#!/usr/bin/env python3
"""
Elva AI Memory Integration System Testing
Tests the updated memory integration system to ensure proper behavior as per review request
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api"

class MemoryIntegrationTester:
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

    def test_memory_trigger_fix_natural_conversation(self):
        """Test 1: Memory Trigger Fix - Natural conversation should NOT be treated as memory commands"""
        print("🧠 Testing Memory Trigger Fix - Natural Conversation Flow...")
        
        test_cases = [
            {
                "message": "Hello my name is Adam",
                "description": "Introduction with name",
                "should_be_memory_command": False
            },
            {
                "message": "I am a developer",
                "description": "Personal information sharing",
                "should_be_memory_command": False
            },
            {
                "message": "I love pizza",
                "description": "Preference sharing",
                "should_be_memory_command": False
            },
            {
                "message": "I work at Google",
                "description": "Work information sharing",
                "should_be_memory_command": False
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get("intent_data", {})
                    response_text = data.get("response", "")
                    
                    # Check if it was treated as a memory command
                    is_memory_command = intent_data.get("intent") == "memory_operation"
                    
                    if not is_memory_command and not test_case["should_be_memory_command"]:
                        # Check if response is natural and conversational
                        natural_response_indicators = [
                            "nice to meet you",
                            "hello",
                            "hi",
                            "great",
                            "awesome",
                            "cool",
                            "that's",
                            "wonderful"
                        ]
                        
                        is_natural = any(indicator in response_text.lower() for indicator in natural_response_indicators)
                        
                        # Check that it's NOT a system message
                        system_message_indicators = [
                            "retrieved memory context",
                            "stored in memory",
                            "i'll remember that",
                            "memory updated",
                            "fact stored"
                        ]
                        
                        is_system_message = any(indicator in response_text.lower() for indicator in system_message_indicators)
                        
                        if is_natural and not is_system_message:
                            results.append(f"✅ {test_case['description']}: Natural response '{response_text[:50]}...'")
                            self.message_ids.append(data["id"])
                        else:
                            results.append(f"❌ {test_case['description']}: Response not natural or contains system messages")
                            all_passed = False
                    else:
                        results.append(f"❌ {test_case['description']}: Incorrectly treated as memory command")
                        all_passed = False
                        
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Memory Trigger Fix - Natural Conversation", all_passed, result_summary)
        return all_passed

    def test_silent_auto_storage(self):
        """Test 2: Silent Auto-Storage - Personal information should be stored silently"""
        print("🤫 Testing Silent Auto-Storage...")
        
        # First, clear any existing memory for this session
        try:
            requests.delete(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
        except:
            pass
        
        test_cases = [
            {
                "message": "My name is Adam Smith",
                "info_type": "identity",
                "expected_storage": "name"
            },
            {
                "message": "I prefer working in the morning",
                "info_type": "preferences", 
                "expected_storage": "work preference"
            },
            {
                "message": "I work as a software engineer",
                "info_type": "work",
                "expected_storage": "job role"
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    
                    # Check that response is natural, not a system confirmation
                    system_confirmations = [
                        "i'll remember that",
                        "stored in memory",
                        "memory updated",
                        "fact stored",
                        "noted",
                        "got it, i'll remember"
                    ]
                    
                    is_system_confirmation = any(conf in response_text.lower() for conf in system_confirmations)
                    
                    if not is_system_confirmation:
                        results.append(f"✅ {test_case['info_type']}: Silent storage - no system confirmation message")
                        self.message_ids.append(data["id"])
                    else:
                        results.append(f"❌ {test_case['info_type']}: System confirmation detected: '{response_text[:50]}...'")
                        all_passed = False
                        
                else:
                    results.append(f"❌ {test_case['info_type']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['info_type']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Silent Auto-Storage", all_passed, result_summary)
        return all_passed

    def test_memory_context_integration(self):
        """Test 3: Memory Context Integration - Memory should be passed to hybrid AI system"""
        print("🔗 Testing Memory Context Integration...")
        
        # First store some information
        setup_messages = [
            "My name is Adam",
            "I love Italian food",
            "I work as a developer"
        ]
        
        for msg in setup_messages:
            try:
                payload = {
                    "message": msg,
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                time.sleep(1)  # Small delay between messages
            except:
                pass
        
        # Now test if memory is used in responses
        test_cases = [
            {
                "message": "What's my name?",
                "expected_info": "Adam",
                "description": "Name recall"
            },
            {
                "message": "What kind of food do I like?",
                "expected_info": "Italian",
                "description": "Food preference recall"
            },
            {
                "message": "What do I do for work?",
                "expected_info": "developer",
                "description": "Work information recall"
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").lower()
                    
                    # Check if the expected information is in the response
                    if test_case["expected_info"].lower() in response_text:
                        # Check that response is natural, not robotic
                        natural_phrases = [
                            "your name is",
                            "you are",
                            "you like",
                            "you work as",
                            "you're",
                            "you love"
                        ]
                        
                        is_natural = any(phrase in response_text for phrase in natural_phrases)
                        
                        # Check it's not a debug message
                        debug_indicators = [
                            "retrieved memory context",
                            "memory lookup",
                            "context found"
                        ]
                        
                        is_debug = any(indicator in response_text for indicator in debug_indicators)
                        
                        if is_natural and not is_debug:
                            results.append(f"✅ {test_case['description']}: Natural response with memory: '{data.get('response', '')[:50]}...'")
                        else:
                            results.append(f"❌ {test_case['description']}: Response not natural or contains debug info")
                            all_passed = False
                    else:
                        results.append(f"❌ {test_case['description']}: Expected info '{test_case['expected_info']}' not found in response")
                        all_passed = False
                        
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Memory Context Integration", all_passed, result_summary)
        return all_passed

    def test_explicit_memory_commands(self):
        """Test 4: Explicit Memory Commands - Only explicit commands should be treated as memory operations"""
        print("📝 Testing Explicit Memory Commands...")
        
        test_cases = [
            {
                "message": "Remember that I have a meeting tomorrow",
                "should_be_memory_command": True,
                "description": "Explicit remember command"
            },
            {
                "message": "What do you remember about me?",
                "should_be_memory_command": True,
                "description": "Memory query command"
            },
            {
                "message": "Forget that I mentioned the meeting",
                "should_be_memory_command": True,
                "description": "Forget command"
            },
            {
                "message": "Store this information: I live in New York",
                "should_be_memory_command": True,
                "description": "Store command"
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get("intent_data", {})
                    response_text = data.get("response", "")
                    
                    # Check if it was treated as a memory command
                    is_memory_command = intent_data.get("intent") == "memory_operation"
                    
                    if is_memory_command == test_case["should_be_memory_command"]:
                        # For explicit memory commands, check for appropriate confirmation
                        if test_case["should_be_memory_command"]:
                            memory_confirmations = [
                                "i'll remember",
                                "got it",
                                "stored",
                                "remembered",
                                "noted"
                            ]
                            
                            has_confirmation = any(conf in response_text.lower() for conf in memory_confirmations)
                            
                            if has_confirmation:
                                results.append(f"✅ {test_case['description']}: Correctly treated as memory command with confirmation")
                            else:
                                results.append(f"❌ {test_case['description']}: Memory command but no confirmation")
                                all_passed = False
                        else:
                            results.append(f"✅ {test_case['description']}: Correctly NOT treated as memory command")
                    else:
                        results.append(f"❌ {test_case['description']}: Incorrect memory command classification")
                        all_passed = False
                        
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Explicit Memory Commands", all_passed, result_summary)
        return all_passed

    def test_natural_response_generation(self):
        """Test 5: Natural Response Generation - Responses should sound natural and human-like"""
        print("🗣️ Testing Natural Response Generation...")
        
        test_cases = [
            {
                "message": "Hi there!",
                "description": "Greeting response",
                "should_be_natural": True
            },
            {
                "message": "How are you doing today?",
                "description": "Casual question response",
                "should_be_natural": True
            },
            {
                "message": "Tell me about yourself",
                "description": "Personal question response",
                "should_be_natural": True
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    
                    # Check for robotic/system-like phrases
                    robotic_phrases = [
                        "retrieved memory context",
                        "processing request",
                        "system response",
                        "debug:",
                        "error:",
                        "function executed",
                        "memory lookup complete"
                    ]
                    
                    is_robotic = any(phrase in response_text.lower() for phrase in robotic_phrases)
                    
                    # Check for natural conversational elements
                    natural_elements = [
                        "!",  # Exclamation marks
                        "?",  # Questions
                        "i'm",  # Contractions
                        "that's",
                        "i'd",
                        "you're",
                        "it's"
                    ]
                    
                    has_natural_elements = any(element in response_text.lower() for element in natural_elements)
                    
                    # Check response length (natural responses are usually not too short or too long)
                    response_length = len(response_text.strip())
                    appropriate_length = 10 <= response_length <= 500
                    
                    if not is_robotic and has_natural_elements and appropriate_length:
                        results.append(f"✅ {test_case['description']}: Natural response: '{response_text[:50]}...'")
                    else:
                        issues = []
                        if is_robotic:
                            issues.append("robotic phrases detected")
                        if not has_natural_elements:
                            issues.append("lacks natural conversational elements")
                        if not appropriate_length:
                            issues.append(f"inappropriate length ({response_length} chars)")
                        
                        results.append(f"❌ {test_case['description']}: Issues: {', '.join(issues)}")
                        all_passed = False
                        
                else:
                    results.append(f"❌ {test_case['description']}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['description']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("Natural Response Generation", all_passed, result_summary)
        return all_passed

    def test_no_debug_messages_in_responses(self):
        """Test 6: No Debug Messages - Confirm no debug messages appear in responses"""
        print("🚫 Testing No Debug Messages in Responses...")
        
        test_cases = [
            "Hello my name is Adam",
            "I love pizza",
            "What's my name?",
            "How are you?",
            "Tell me about the weather"
        ]
        
        all_passed = True
        results = []
        
        for message in test_cases:
            try:
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "adam_test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    
                    # Check for debug messages
                    debug_phrases = [
                        "retrieved memory context",
                        "memory lookup",
                        "context found",
                        "debug:",
                        "system:",
                        "processing:",
                        "function:",
                        "api call:",
                        "database query",
                        "memory search"
                    ]
                    
                    found_debug = [phrase for phrase in debug_phrases if phrase in response_text.lower()]
                    
                    if not found_debug:
                        results.append(f"✅ '{message[:30]}...': No debug messages")
                    else:
                        results.append(f"❌ '{message[:30]}...': Debug messages found: {found_debug}")
                        all_passed = False
                        
                else:
                    results.append(f"❌ '{message[:30]}...': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ '{message[:30]}...': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("No Debug Messages in Responses", all_passed, result_summary)
        return all_passed

    def test_memory_system_health(self):
        """Test 7: Memory System Health - Check if memory system is properly initialized"""
        print("🏥 Testing Memory System Health...")
        
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if semantic memory is mentioned in health check
                services = data.get("services", {})
                
                # Look for memory-related services
                memory_indicators = [
                    "semantic_memory",
                    "letta_memory", 
                    "memory_system",
                    "conversation_memory"
                ]
                
                found_memory_services = []
                for service_name, service_info in services.items():
                    if any(indicator in service_name.lower() for indicator in memory_indicators):
                        found_memory_services.append(f"{service_name}: {service_info}")
                
                if found_memory_services:
                    self.log_test("Memory System Health", True, f"Memory services found: {found_memory_services}")
                    return True
                else:
                    self.log_test("Memory System Health", False, "No memory services found in health check", data)
                    return False
                    
            else:
                self.log_test("Memory System Health", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Memory System Health", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all memory integration tests"""
        print("🚀 Starting Elva AI Memory Integration System Testing...")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        tests = [
            self.test_memory_system_health,
            self.test_memory_trigger_fix_natural_conversation,
            self.test_silent_auto_storage,
            self.test_memory_context_integration,
            self.test_explicit_memory_commands,
            self.test_natural_response_generation,
            self.test_no_debug_messages_in_responses
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
                time.sleep(2)  # Small delay between tests
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
        
        print("=" * 80)
        print(f"🏁 Memory Integration Testing Complete!")
        print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL MEMORY INTEGRATION TESTS PASSED!")
            return True
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed")
            return False

    def get_test_summary(self):
        """Get a summary of all test results"""
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        summary = {
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "test_results": self.test_results
        }
        
        return summary

if __name__ == "__main__":
    tester = MemoryIntegrationTester()
    success = tester.run_all_tests()
    
    # Print detailed summary
    summary = tester.get_test_summary()
    print(f"\n📋 Detailed Summary:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Passed: {summary['passed_tests']}")
    print(f"   Failed: {summary['failed_tests']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    
    if not success:
        print("\n❌ Failed Tests:")
        for result in summary['test_results']:
            if not result['success']:
                print(f"   - {result['test']}: {result['details']}")