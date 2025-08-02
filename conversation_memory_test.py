#!/usr/bin/env python3
"""
Comprehensive Conversation Memory and Gmail Authentication Testing for Elva AI
Tests the enhanced conversation memory system and Gmail authentication fixes as requested in review
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://c20efb94-1a9f-42d9-a126-b5157ee976a4.preview.emergentagent.com/api"

class ConversationMemoryTester:
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

    def test_conversation_memory_name_retention(self):
        """Test 1: Conversation Memory - Name Retention Test"""
        print("🧠 Testing Conversation Memory - Name Retention...")
        
        try:
            # Step 1: Send initial message with name
            payload = {
                "message": "Hi, my name is Arpit Kumar",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code != 200:
                self.log_test("Memory Test - Initial Name Message", False, f"HTTP {response.status_code}", response.text)
                return False
            
            data = response.json()
            self.message_ids.append(data["id"])
            self.log_test("Memory Test - Initial Name Message", True, f"Name introduction sent: '{payload['message']}'")
            
            # Step 2: Send 5-6 different messages about various topics
            diverse_messages = [
                "What's the weather like today?",
                "Can you help me with a Python programming question?",
                "Tell me about artificial intelligence",
                "What are some good restaurants in New York?",
                "How do I learn machine learning?",
                "What's the latest news in technology?"
            ]
            
            for i, message in enumerate(diverse_messages, 1):
                time.sleep(1)  # Small delay between messages
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    self.message_ids.append(data["id"])
                    self.log_test(f"Memory Test - Diverse Message {i}", True, f"Sent: '{message}'")
                else:
                    self.log_test(f"Memory Test - Diverse Message {i}", False, f"HTTP {response.status_code}")
                    return False
            
            # Step 3: Ask for the name - Primary test
            time.sleep(2)  # Ensure some time has passed
            payload = {
                "message": "What is my name?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                
                # Check if the AI remembers the name "Arpit Kumar"
                if "arpit" in response_text and "kumar" in response_text:
                    self.log_test("Memory Test - Name Recall Primary", True, f"AI correctly remembered name: '{data.get('response')}'")
                    name_recall_success = True
                else:
                    self.log_test("Memory Test - Name Recall Primary", False, f"AI did not remember name. Response: '{data.get('response')}'")
                    name_recall_success = False
                
                self.message_ids.append(data["id"])
            else:
                self.log_test("Memory Test - Name Recall Primary", False, f"HTTP {response.status_code}")
                return False
            
            # Step 4: Alternative name question
            time.sleep(1)
            payload = {
                "message": "What did I tell you my name was earlier?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                
                # Check if the AI remembers the name in alternative phrasing
                if "arpit" in response_text and "kumar" in response_text:
                    self.log_test("Memory Test - Name Recall Alternative", True, f"AI correctly remembered name with alternative question: '{data.get('response')}'")
                    alt_recall_success = True
                else:
                    self.log_test("Memory Test - Name Recall Alternative", False, f"AI did not remember name with alternative question. Response: '{data.get('response')}'")
                    alt_recall_success = False
                
                self.message_ids.append(data["id"])
            else:
                self.log_test("Memory Test - Name Recall Alternative", False, f"HTTP {response.status_code}")
                return False
            
            # Overall memory test result
            overall_success = name_recall_success and alt_recall_success
            self.log_test("Memory Test - Overall Name Retention", overall_success, 
                         f"Primary recall: {name_recall_success}, Alternative recall: {alt_recall_success}")
            
            return overall_success
            
        except Exception as e:
            self.log_test("Memory Test - Name Retention", False, f"Error: {str(e)}")
            return False

    def test_message_memory_statistics(self):
        """Test 2: Message Memory Statistics Endpoints"""
        print("📊 Testing Message Memory Statistics...")
        
        try:
            # Test message memory stats endpoint
            response = requests.get(f"{BACKEND_URL}/message-memory/stats/{self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields in stats
                required_fields = ["session_id", "total_messages", "user_messages", "assistant_messages"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Memory Stats - Structure", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check if messages are being counted
                total_messages = data.get("total_messages", 0)
                user_messages = data.get("user_messages", 0)
                assistant_messages = data.get("assistant_messages", 0)
                
                if total_messages == 0:
                    self.log_test("Memory Stats - Message Count", False, "No messages found in memory stats", data)
                    return False
                
                if user_messages == 0 or assistant_messages == 0:
                    self.log_test("Memory Stats - Message Types", False, f"Missing message types: user={user_messages}, assistant={assistant_messages}", data)
                    return False
                
                # Check for recent messages preview
                if "recent_messages_preview" in data:
                    recent_messages = data["recent_messages_preview"]
                    if isinstance(recent_messages, list) and len(recent_messages) > 0:
                        self.log_test("Memory Stats - Recent Preview", True, f"Found {len(recent_messages)} recent messages")
                    else:
                        self.log_test("Memory Stats - Recent Preview", False, "Recent messages preview is empty or invalid")
                        return False
                
                self.log_test("Memory Stats - Endpoint", True, 
                             f"Stats working: {total_messages} total, {user_messages} user, {assistant_messages} assistant")
                
            else:
                self.log_test("Memory Stats - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            # Test full context endpoint
            response = requests.get(f"{BACKEND_URL}/message-memory/full-context/{self.session_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields in full context
                required_fields = ["session_id", "total_messages", "full_context", "all_messages"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Memory Full Context - Structure", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check if full context contains conversation history
                full_context = data.get("full_context", "")
                if not full_context or len(full_context.strip()) == 0:
                    self.log_test("Memory Full Context - Content", False, "Full context is empty", data)
                    return False
                
                # Check if context contains the name we introduced
                if "arpit" in full_context.lower() and "kumar" in full_context.lower():
                    self.log_test("Memory Full Context - Name Preservation", True, "Name 'Arpit Kumar' found in full context")
                else:
                    self.log_test("Memory Full Context - Name Preservation", False, "Name 'Arpit Kumar' not found in full context")
                    return False
                
                # Check all_messages structure
                all_messages = data.get("all_messages", [])
                if not isinstance(all_messages, list) or len(all_messages) == 0:
                    self.log_test("Memory Full Context - Messages List", False, "all_messages is empty or invalid", data)
                    return False
                
                # Verify message structure
                first_message = all_messages[0]
                required_msg_fields = ["role", "content", "timestamp"]
                missing_msg_fields = [field for field in required_msg_fields if field not in first_message]
                
                if missing_msg_fields:
                    self.log_test("Memory Full Context - Message Structure", False, f"Missing message fields: {missing_msg_fields}", first_message)
                    return False
                
                self.log_test("Memory Full Context - Endpoint", True, 
                             f"Full context working: {len(all_messages)} messages, context length: {len(full_context)} chars")
                
            else:
                self.log_test("Memory Full Context - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            return True
            
        except Exception as e:
            self.log_test("Memory Statistics", False, f"Error: {str(e)}")
            return False

    def test_gmail_authentication_fix(self):
        """Test 3: Gmail Authentication Fix"""
        print("📧 Testing Gmail Authentication Fix...")
        
        try:
            # Test Gmail auth endpoint
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            
            if response.status_code == 200:
                # Check if it's a redirect response (OAuth URL)
                if response.url and "accounts.google.com" in response.url:
                    auth_url = response.url
                    
                    # Check if new client_id is in the URL
                    expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                    if expected_client_id in auth_url:
                        self.log_test("Gmail Auth - New Client ID", True, f"New OAuth2 client_id found in auth URL")
                    else:
                        self.log_test("Gmail Auth - New Client ID", False, f"New client_id not found in auth URL: {auth_url}")
                        return False
                    
                    # Check redirect URI
                    expected_redirect = "https://c20efb94-1a9f-42d9-a126-b5157ee976a4.preview.emergentagent.com/api/gmail/callback"
                    if expected_redirect in auth_url:
                        self.log_test("Gmail Auth - Redirect URI", True, "Correct redirect URI configured")
                    else:
                        self.log_test("Gmail Auth - Redirect URI", False, f"Incorrect redirect URI in auth URL")
                        return False
                    
                    # Check for client_secret parameter (should be present in OAuth flow)
                    expected_client_secret = "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"
                    # Note: client_secret is not typically in the URL for security, but we can check if auth flow works
                    self.log_test("Gmail Auth - OAuth URL Generation", True, f"Valid Google OAuth URL generated: {auth_url[:100]}...")
                    
                else:
                    self.log_test("Gmail Auth - OAuth URL", False, "No valid Google OAuth URL generated", response.url)
                    return False
                    
            else:
                self.log_test("Gmail Auth - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            # Test Gmail status endpoint
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if credentials are configured
                if data.get("credentials_configured") == True:
                    self.log_test("Gmail Status - Credentials Configured", True, "Gmail credentials properly configured")
                else:
                    self.log_test("Gmail Status - Credentials Configured", False, f"Credentials not configured: {data.get('credentials_configured')}")
                    return False
                
                # Check scopes
                scopes = data.get("scopes", [])
                expected_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
                
                if not missing_scopes:
                    self.log_test("Gmail Status - Scopes", True, f"All required scopes configured: {scopes}")
                else:
                    self.log_test("Gmail Status - Scopes", False, f"Missing scopes: {missing_scopes}")
                    return False
                
            else:
                self.log_test("Gmail Status - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            # Test health endpoint for Gmail integration
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check Gmail integration in health
                gmail_integration = data.get("gmail_api_integration", {})
                
                if gmail_integration.get("status") == "ready":
                    self.log_test("Gmail Health - Integration Status", True, "Gmail integration status: ready")
                else:
                    self.log_test("Gmail Health - Integration Status", False, f"Gmail integration status: {gmail_integration.get('status')}")
                    return False
                
                if gmail_integration.get("oauth2_flow") == "implemented":
                    self.log_test("Gmail Health - OAuth2 Flow", True, "OAuth2 flow implemented")
                else:
                    self.log_test("Gmail Health - OAuth2 Flow", False, f"OAuth2 flow: {gmail_integration.get('oauth2_flow')}")
                    return False
                
                if gmail_integration.get("credentials_configured") == True:
                    self.log_test("Gmail Health - Credentials in Health", True, "Credentials configured in health check")
                else:
                    self.log_test("Gmail Health - Credentials in Health", False, "Credentials not configured in health check")
                    return False
                
            else:
                self.log_test("Gmail Health - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            return True
            
        except Exception as e:
            self.log_test("Gmail Authentication Fix", False, f"Error: {str(e)}")
            return False

    def test_conversation_context_in_ai_responses(self):
        """Test 4: Conversation Context in AI Responses"""
        print("🤖 Testing Conversation Context in AI Responses...")
        
        try:
            # Create a new session for this test
            context_session_id = str(uuid.uuid4())
            
            # Step 1: Establish context with specific details
            initial_context = [
                "I work at TechCorp as a software engineer",
                "My favorite programming language is Python",
                "I'm working on a machine learning project about image recognition"
            ]
            
            for i, message in enumerate(initial_context, 1):
                payload = {
                    "message": message,
                    "session_id": context_session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    self.log_test(f"Context Setup - Message {i}", True, f"Context established: '{message}'")
                else:
                    self.log_test(f"Context Setup - Message {i}", False, f"HTTP {response.status_code}")
                    return False
                
                time.sleep(1)  # Small delay between messages
            
            # Step 2: Send several unrelated messages in between
            filler_messages = [
                "What's the weather like?",
                "Tell me a joke",
                "How do I cook pasta?",
                "What's the capital of France?"
            ]
            
            for i, message in enumerate(filler_messages, 1):
                payload = {
                    "message": message,
                    "session_id": context_session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    self.log_test(f"Filler Message {i}", True, f"Sent: '{message}'")
                else:
                    self.log_test(f"Filler Message {i}", False, f"HTTP {response.status_code}")
                    return False
                
                time.sleep(1)
            
            # Step 3: Ask questions that require remembering earlier context
            context_questions = [
                {
                    "question": "What company do I work for?",
                    "expected_keywords": ["techcorp"],
                    "test_name": "Company Context Recall"
                },
                {
                    "question": "What's my favorite programming language?",
                    "expected_keywords": ["python"],
                    "test_name": "Programming Language Context Recall"
                },
                {
                    "question": "What kind of project am I working on?",
                    "expected_keywords": ["machine learning", "image recognition"],
                    "test_name": "Project Context Recall"
                },
                {
                    "question": "Can you summarize what you know about my work?",
                    "expected_keywords": ["techcorp", "python", "machine learning"],
                    "test_name": "Comprehensive Context Recall"
                }
            ]
            
            context_recall_results = []
            
            for question_data in context_questions:
                time.sleep(2)  # Ensure some time between questions
                
                payload = {
                    "message": question_data["question"],
                    "session_id": context_session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").lower()
                    
                    # Check if expected keywords are in the response
                    found_keywords = [keyword for keyword in question_data["expected_keywords"] 
                                    if keyword.lower() in response_text]
                    
                    if len(found_keywords) > 0:
                        self.log_test(question_data["test_name"], True, 
                                     f"AI remembered context. Found keywords: {found_keywords}. Response: '{data.get('response')[:100]}...'")
                        context_recall_results.append(True)
                    else:
                        self.log_test(question_data["test_name"], False, 
                                     f"AI did not remember context. Expected: {question_data['expected_keywords']}. Response: '{data.get('response')}'")
                        context_recall_results.append(False)
                else:
                    self.log_test(question_data["test_name"], False, f"HTTP {response.status_code}")
                    context_recall_results.append(False)
            
            # Overall context test result
            successful_recalls = sum(context_recall_results)
            total_questions = len(context_questions)
            success_rate = successful_recalls / total_questions
            
            overall_success = success_rate >= 0.75  # At least 75% success rate
            
            self.log_test("Context Recall - Overall Performance", overall_success, 
                         f"Context recall success rate: {successful_recalls}/{total_questions} ({success_rate:.1%})")
            
            return overall_success
            
        except Exception as e:
            self.log_test("Conversation Context in AI Responses", False, f"Error: {str(e)}")
            return False

    def test_memory_system_integration(self):
        """Test 5: Memory System Integration"""
        print("🔗 Testing Memory System Integration...")
        
        try:
            # Test search functionality in message memory
            search_payload = {
                "query": "Arpit Kumar"
            }
            
            response = requests.post(f"{BACKEND_URL}/message-memory/search/{self.session_id}", 
                                   json=search_payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check search response structure
                required_fields = ["session_id", "search_query", "results_found", "matching_messages"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Memory Search - Structure", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check if search found the name
                results_found = data.get("results_found", 0)
                matching_messages = data.get("matching_messages", [])
                
                if results_found > 0 and len(matching_messages) > 0:
                    # Check if any matching message contains the name
                    name_found = False
                    for message in matching_messages:
                        content = message.get("content", "").lower()
                        if "arpit" in content and "kumar" in content:
                            name_found = True
                            break
                    
                    if name_found:
                        self.log_test("Memory Search - Name Search", True, 
                                     f"Search found {results_found} messages containing 'Arpit Kumar'")
                    else:
                        self.log_test("Memory Search - Name Search", False, 
                                     f"Search found {results_found} messages but none contain 'Arpit Kumar'")
                        return False
                else:
                    self.log_test("Memory Search - Name Search", False, 
                                 f"Search did not find any messages containing 'Arpit Kumar'")
                    return False
                
            else:
                self.log_test("Memory Search - Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            # Test compatibility between message_memory and chat_messages collections
            # Get chat history from regular endpoint
            response = requests.get(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
            
            if response.status_code == 200:
                chat_data = response.json()
                chat_messages = chat_data.get("history", [])
                
                # Get message memory stats
                response = requests.get(f"{BACKEND_URL}/message-memory/stats/{self.session_id}", timeout=10)
                
                if response.status_code == 200:
                    memory_data = response.json()
                    memory_total = memory_data.get("total_messages", 0)
                    
                    # Both systems should have messages (compatibility check)
                    if len(chat_messages) > 0 and memory_total > 0:
                        self.log_test("Memory System - Dual Storage", True, 
                                     f"Both systems have messages: chat_messages={len(chat_messages)}, message_memory={memory_total}")
                    else:
                        self.log_test("Memory System - Dual Storage", False, 
                                     f"One system missing messages: chat_messages={len(chat_messages)}, message_memory={memory_total}")
                        return False
                else:
                    self.log_test("Memory System - Compatibility Check", False, "Failed to get memory stats")
                    return False
            else:
                self.log_test("Memory System - Compatibility Check", False, "Failed to get chat history")
                return False
            
            return True
            
        except Exception as e:
            self.log_test("Memory System Integration", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all conversation memory and Gmail authentication tests"""
        print("🚀 Starting Comprehensive Conversation Memory and Gmail Authentication Testing...")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        test_methods = [
            self.test_conversation_memory_name_retention,
            self.test_message_memory_statistics,
            self.test_gmail_authentication_fix,
            self.test_conversation_context_in_ai_responses,
            self.test_memory_system_integration
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
                print("-" * 40)
            except Exception as e:
                print(f"❌ Test method {test_method.__name__} failed with exception: {e}")
                print("-" * 40)
        
        # Print summary
        print("=" * 80)
        print("🎯 CONVERSATION MEMORY & GMAIL AUTHENTICATION TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"✅ Passed: {passed_tests}/{total_tests} tests ({success_rate:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Conversation memory and Gmail authentication are working correctly.")
        elif passed_tests >= total_tests * 0.8:
            print("⚠️  MOSTLY WORKING: Most tests passed, minor issues detected.")
        else:
            print("❌ CRITICAL ISSUES: Multiple tests failed, significant problems detected.")
        
        print("\n📋 Detailed Test Results:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['details']}")
        
        return passed_tests, total_tests

if __name__ == "__main__":
    tester = ConversationMemoryTester()
    passed, total = tester.run_all_tests()
    
    if passed == total:
        exit(0)  # All tests passed
    else:
        exit(1)  # Some tests failed