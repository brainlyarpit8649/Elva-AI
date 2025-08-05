#!/usr/bin/env python3
"""
Enhanced Conversation Memory System Testing
Comprehensive test suite to diagnose context retrieval issues as requested in review.

Test Focus:
1. Test Context Retrieval - Make POST to /api/chat with "My name is Arpit" and check get_context_for_ai()
2. Test Memory Flow - Send name, random messages, then ask "What is my name?"
3. Test Enhanced Memory System directly - Check /api/unified-memory/stats
4. Debug Context Passing - Check if context is properly passed to AI model
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime
import os
import sys

# Add backend directory to path for imports
sys.path.append('/app/backend')

# Test configuration
BACKEND_URL = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class EnhancedMemoryTester:
    def __init__(self):
        self.session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        self.user_id = "test_user_arpit"
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str, data: dict = None):
        """Log test result with details"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} {test_name}")
        print(f"   Details: {details}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)[:200]}...")
    
    async def test_enhanced_memory_stats(self):
        """Test 3: Test Enhanced Memory System directly - Check /api/unified-memory/stats"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{API_BASE}/unified-memory/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    self.log_result(
                        "Enhanced Memory Stats Endpoint",
                        True,
                        f"Memory system status: {stats.get('status', 'unknown')}",
                        stats
                    )
                    return stats
                else:
                    self.log_result(
                        "Enhanced Memory Stats Endpoint",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                        {"status_code": response.status_code, "response": response.text}
                    )
                    return None
                    
        except Exception as e:
            self.log_result(
                "Enhanced Memory Stats Endpoint",
                False,
                f"Exception: {str(e)}",
                {"error": str(e)}
            )
            return None
    
    async def test_context_retrieval_direct(self):
        """Test 1: Test Context Retrieval - Make POST to /api/chat and check context"""
        try:
            # First, send the name message
            async with httpx.AsyncClient(timeout=30.0) as client:
                chat_request = {
                    "message": "My name is Arpit",
                    "session_id": self.session_id,
                    "user_id": self.user_id
                }
                
                response = await client.post(f"{API_BASE}/chat", json=chat_request)
                
                if response.status_code == 200:
                    chat_response = response.json()
                    self.log_result(
                        "Context Retrieval - Name Message Sent",
                        True,
                        f"AI Response: {chat_response.get('response', '')[:100]}...",
                        {
                            "message_id": chat_response.get('id'),
                            "response_length": len(chat_response.get('response', '')),
                            "intent_data": chat_response.get('intent_data')
                        }
                    )
                    
                    # Now test if we can retrieve the context using enhanced memory directly
                    await self.test_enhanced_memory_context_direct()
                    
                    return chat_response
                else:
                    self.log_result(
                        "Context Retrieval - Name Message Sent",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                        {"status_code": response.status_code}
                    )
                    return None
                    
        except Exception as e:
            self.log_result(
                "Context Retrieval - Name Message Sent",
                False,
                f"Exception: {str(e)}",
                {"error": str(e)}
            )
            return None
    
    async def test_enhanced_memory_context_direct(self):
        """Test the enhanced memory get_context_for_ai() method directly"""
        try:
            # Import and test the enhanced memory system directly
            from enhanced_message_memory import initialize_enhanced_message_memory
            
            # Initialize enhanced memory
            enhanced_memory = await initialize_enhanced_message_memory()
            
            if enhanced_memory:
                # Get context for AI
                context = await enhanced_memory.get_context_for_ai(self.session_id)
                
                self.log_result(
                    "Enhanced Memory get_context_for_ai() Direct Test",
                    True,
                    f"Context retrieved: {len(context)} characters",
                    {
                        "context_length": len(context),
                        "context_preview": context[:500] + "..." if len(context) > 500 else context,
                        "contains_name": "Arpit" in context
                    }
                )
                
                # Also test conversation history
                history = await enhanced_memory.get_conversation_history(self.session_id)
                
                self.log_result(
                    "Enhanced Memory get_conversation_history() Direct Test",
                    True,
                    f"History retrieved: {len(history)} messages",
                    {
                        "message_count": len(history),
                        "messages": history[:3] if history else []  # Show first 3 messages
                    }
                )
                
                return context, history
            else:
                self.log_result(
                    "Enhanced Memory get_context_for_ai() Direct Test",
                    False,
                    "Enhanced memory initialization failed",
                    {}
                )
                return None, None
                
        except Exception as e:
            self.log_result(
                "Enhanced Memory get_context_for_ai() Direct Test",
                False,
                f"Exception: {str(e)}",
                {"error": str(e)}
            )
            return None, None
    
    async def test_memory_flow_complete(self):
        """Test 2: Test Memory Flow - Send name, random messages, then ask for name"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Send name
                messages_to_send = [
                    "My name is Arpit",
                    "How are you today?",
                    "What's the weather like?",
                    "Tell me a joke",
                    "What is my name?"
                ]
                
                responses = []
                
                for i, message in enumerate(messages_to_send):
                    chat_request = {
                        "message": message,
                        "session_id": self.session_id,
                        "user_id": self.user_id
                    }
                    
                    response = await client.post(f"{API_BASE}/chat", json=chat_request)
                    
                    if response.status_code == 200:
                        chat_response = response.json()
                        responses.append(chat_response)
                        
                        # Special check for the final "What is my name?" message
                        if i == len(messages_to_send) - 1:
                            ai_response = chat_response.get('response', '').lower()
                            remembers_name = 'arpit' in ai_response
                            
                            self.log_result(
                                "Memory Flow - Name Recall Test",
                                remembers_name,
                                f"AI Response to 'What is my name?': {chat_response.get('response', '')[:200]}...",
                                {
                                    "remembers_name": remembers_name,
                                    "full_response": chat_response.get('response', ''),
                                    "intent_data": chat_response.get('intent_data')
                                }
                            )
                        else:
                            self.log_result(
                                f"Memory Flow - Message {i+1}: '{message[:30]}...'",
                                True,
                                f"Response received: {chat_response.get('response', '')[:50]}...",
                                {"response_length": len(chat_response.get('response', ''))}
                            )
                    else:
                        self.log_result(
                            f"Memory Flow - Message {i+1}: '{message[:30]}...'",
                            False,
                            f"HTTP {response.status_code}: {response.text}",
                            {"status_code": response.status_code}
                        )
                        break
                    
                    # Small delay between messages
                    await asyncio.sleep(1)
                
                return responses
                
        except Exception as e:
            self.log_result(
                "Memory Flow - Complete Test",
                False,
                f"Exception: {str(e)}",
                {"error": str(e)}
            )
            return None
    
    async def test_session_memory_stats(self):
        """Test session-specific memory stats"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{API_BASE}/unified-memory/session/{self.session_id}/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    self.log_result(
                        "Session Memory Stats",
                        True,
                        f"Session stats retrieved: {stats.get('session_stats', {}).get('total_messages', 0)} messages",
                        stats
                    )
                    return stats
                else:
                    self.log_result(
                        "Session Memory Stats",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                        {"status_code": response.status_code}
                    )
                    return None
                    
        except Exception as e:
            self.log_result(
                "Session Memory Stats",
                False,
                f"Exception: {str(e)}",
                {"error": str(e)}
            )
            return None
    
    async def test_context_passing_debug(self):
        """Test 4: Debug Context Passing - Check if context is properly passed to AI"""
        try:
            # Send a message that should use context
            async with httpx.AsyncClient(timeout=30.0) as client:
                chat_request = {
                    "message": "What did I tell you about my name earlier?",
                    "session_id": self.session_id,
                    "user_id": self.user_id
                }
                
                response = await client.post(f"{API_BASE}/chat", json=chat_request)
                
                if response.status_code == 200:
                    chat_response = response.json()
                    ai_response = chat_response.get('response', '').lower()
                    
                    # Check if AI response indicates it has context
                    has_context_indicators = any(phrase in ai_response for phrase in [
                        'arpit', 'your name', 'you told me', 'you mentioned', 'earlier'
                    ])
                    
                    self.log_result(
                        "Context Passing Debug Test",
                        has_context_indicators,
                        f"AI Response: {chat_response.get('response', '')}",
                        {
                            "has_context_indicators": has_context_indicators,
                            "full_response": chat_response.get('response', ''),
                            "intent_data": chat_response.get('intent_data')
                        }
                    )
                    
                    return chat_response
                else:
                    self.log_result(
                        "Context Passing Debug Test",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                        {"status_code": response.status_code}
                    )
                    return None
                    
        except Exception as e:
            self.log_result(
                "Context Passing Debug Test",
                False,
                f"Exception: {str(e)}",
                {"error": str(e)}
            )
            return None
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print(f"🧪 Starting Enhanced Conversation Memory System Testing")
        print(f"📋 Session ID: {self.session_id}")
        print(f"👤 User ID: {self.user_id}")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        # Test 3: Enhanced Memory System Stats (first to check if system is available)
        await self.test_enhanced_memory_stats()
        
        # Test 1: Context Retrieval Direct
        await self.test_context_retrieval_direct()
        
        # Test 2: Memory Flow Complete
        await self.test_memory_flow_complete()
        
        # Test 4: Context Passing Debug
        await self.test_context_passing_debug()
        
        # Session Stats
        await self.test_session_memory_stats()
        
        # Summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🎯 ENHANCED CONVERSATION MEMORY SYSTEM TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🔍 DETAILED FINDINGS:")
        
        # Critical findings
        memory_flow_test = next((r for r in self.test_results if "Name Recall Test" in r['test']), None)
        if memory_flow_test:
            if memory_flow_test['success']:
                print("✅ CRITICAL: AI successfully remembers user's name from earlier conversation")
            else:
                print("❌ CRITICAL: AI does NOT remember user's name from earlier conversation")
                print(f"   AI Response: {memory_flow_test['data'].get('full_response', 'N/A')}")
        
        # Context retrieval findings
        context_test = next((r for r in self.test_results if "get_context_for_ai()" in r['test']), None)
        if context_test:
            if context_test['success']:
                context_data = context_test['data']
                print(f"✅ Enhanced Memory Context: {context_data.get('context_length', 0)} chars retrieved")
                print(f"   Contains name 'Arpit': {context_data.get('contains_name', False)}")
            else:
                print("❌ Enhanced Memory Context: Failed to retrieve context")
        
        # Memory system status
        stats_test = next((r for r in self.test_results if "Memory Stats Endpoint" in r['test']), None)
        if stats_test:
            if stats_test['success']:
                print(f"✅ Memory System Status: {stats_test['data'].get('status', 'unknown')}")
            else:
                print("❌ Memory System Status: Not available")
        
        print("\n🔧 DIAGNOSTIC INFORMATION:")
        for result in self.test_results:
            if not result['success']:
                print(f"❌ {result['test']}: {result['details']}")
        
        print("\n📋 ROOT CAUSE ANALYSIS:")
        
        # Analyze the core issue
        if memory_flow_test and not memory_flow_test['success']:
            print("🚨 PRIMARY ISSUE CONFIRMED: AI is NOT remembering names and earlier context")
            print("   This confirms the issue reported in the review request")
            
            if context_test and context_test['success']:
                print("🔍 DIAGNOSIS: Enhanced Memory System CAN retrieve context")
                print("   BUT context is NOT being properly passed to AI models")
                print("   ISSUE: Context passing mechanism between memory system and AI is broken")
            else:
                print("🔍 DIAGNOSIS: Enhanced Memory System CANNOT retrieve context")
                print("   ISSUE: Memory storage or retrieval mechanism is broken")
        else:
            print("✅ Memory system appears to be working correctly")
        
        print("\n💡 RECOMMENDATIONS:")
        if failed_tests > 0:
            print("1. Fix context passing mechanism between enhanced_message_memory and AI models")
            print("2. Ensure get_context_for_ai() output is properly included in AI prompts")
            print("3. Verify that conversation history is being saved correctly")
            print("4. Check if AI models are receiving and using the conversation context")
        else:
            print("1. All tests passed - memory system is working correctly")
        
        print("=" * 80)

async def main():
    """Main test execution"""
    tester = EnhancedMemoryTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
"""
Enhanced Memory System Testing for Elva AI
Tests the Redis + MongoDB hybrid memory system functionality
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api"

class EnhancedMemoryTester:
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

    def test_basic_memory_storage(self):
        """Test 1: Basic Memory Storage - Store messages in Redis and MongoDB"""
        print("🧠 Testing Basic Memory Storage...")
        
        try:
            # Test message 1: "My name is Arpit Kumar"
            payload1 = {
                "message": "My name is Arpit Kumar",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response1 = requests.post(f"{BACKEND_URL}/chat", json=payload1, timeout=15)
            
            if response1.status_code != 200:
                self.log_test("Basic Memory Storage - Message 1", False, f"HTTP {response1.status_code}", response1.text)
                return False
            
            data1 = response1.json()
            self.message_ids.append(data1["id"])
            
            # Wait a moment for storage
            time.sleep(2)
            
            # Test message 2: "I work as a software engineer"
            payload2 = {
                "message": "I work as a software engineer",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response2 = requests.post(f"{BACKEND_URL}/chat", json=payload2, timeout=15)
            
            if response2.status_code != 200:
                self.log_test("Basic Memory Storage - Message 2", False, f"HTTP {response2.status_code}", response2.text)
                return False
            
            data2 = response2.json()
            self.message_ids.append(data2["id"])
            
            # Verify messages are stored by checking chat history
            history_response = requests.get(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                messages = history_data.get("history", [])
                
                # Check if both messages are stored
                user_messages = [msg for msg in messages if msg.get("message") in ["My name is Arpit Kumar", "I work as a software engineer"]]
                
                if len(user_messages) >= 2:
                    self.log_test("Basic Memory Storage", True, f"Successfully stored {len(user_messages)} messages in memory system")
                    return True
                else:
                    self.log_test("Basic Memory Storage", False, f"Only {len(user_messages)} messages found in history")
                    return False
            else:
                self.log_test("Basic Memory Storage", False, f"Failed to retrieve history: HTTP {history_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Basic Memory Storage", False, f"Error: {str(e)}")
            return False

    def test_memory_recall(self):
        """Test 2: Memory Recall - Verify AI responds naturally with remembered information"""
        print("🔍 Testing Memory Recall...")
        
        try:
            # Ask "What is my name?" to test recall
            payload = {
                "message": "What is my name?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code != 200:
                self.log_test("Memory Recall", False, f"HTTP {response.status_code}", response.text)
                return False
            
            data = response.json()
            ai_response = data.get("response", "").lower()
            
            # Check if AI recalls the name naturally
            name_mentioned = "arpit" in ai_response or "arpit kumar" in ai_response.lower()
            
            # Check for natural response patterns (not robotic)
            natural_patterns = [
                "your name is",
                "you told me",
                "you mentioned",
                "i remember",
                "you said your name",
                "you're arpit"
            ]
            
            is_natural = any(pattern in ai_response for pattern in natural_patterns)
            
            # Check it's NOT a robotic response
            robotic_patterns = [
                "retrieved memory context",
                "memory context:",
                "context retrieved",
                "database shows"
            ]
            
            is_robotic = any(pattern in ai_response for pattern in robotic_patterns)
            
            if name_mentioned and is_natural and not is_robotic:
                self.log_test("Memory Recall", True, f"AI naturally recalled name: '{data['response'][:100]}...'")
                return True
            elif name_mentioned and not is_natural:
                self.log_test("Memory Recall", False, f"AI recalled name but response seems robotic: '{data['response'][:100]}...'")
                return False
            elif not name_mentioned:
                self.log_test("Memory Recall", False, f"AI did not recall the name. Response: '{data['response'][:100]}...'")
                return False
            else:
                self.log_test("Memory Recall", False, f"Unexpected response pattern: '{data['response'][:100]}...'")
                return False
                
        except Exception as e:
            self.log_test("Memory Recall", False, f"Error: {str(e)}")
            return False

    def test_context_persistence(self):
        """Test 3: Context Persistence - Ensure context is maintained across multiple messages"""
        print("💬 Testing Context Persistence...")
        
        try:
            # Send several dummy messages
            dummy_messages = [
                "How are you?",
                "What's the weather like?",
                "Tell me a joke",
                "What can you help me with?"
            ]
            
            for msg in dummy_messages:
                payload = {
                    "message": msg,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code != 200:
                    self.log_test("Context Persistence - Dummy Messages", False, f"Failed to send '{msg}': HTTP {response.status_code}")
                    return False
                
                # Small delay between messages
                time.sleep(1)
            
            # Now ask about work to test if earlier context is remembered
            work_payload = {
                "message": "What do I do for work?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            work_response = requests.post(f"{BACKEND_URL}/chat", json=work_payload, timeout=15)
            
            if work_response.status_code != 200:
                self.log_test("Context Persistence", False, f"HTTP {work_response.status_code}", work_response.text)
                return False
            
            work_data = work_response.json()
            ai_response = work_data.get("response", "").lower()
            
            # Check if AI recalls the work information
            work_mentioned = any(term in ai_response for term in [
                "software engineer",
                "engineer",
                "software",
                "developer",
                "programming"
            ])
            
            if work_mentioned:
                self.log_test("Context Persistence", True, f"AI recalled work context after {len(dummy_messages)} intervening messages: '{work_data['response'][:100]}...'")
                return True
            else:
                self.log_test("Context Persistence", False, f"AI did not recall work context. Response: '{work_data['response'][:100]}...'")
                return False
                
        except Exception as e:
            self.log_test("Context Persistence", False, f"Error: {str(e)}")
            return False

    def test_enhanced_memory_health_check(self):
        """Test 4: Enhanced Memory System Health Check"""
        print("🏥 Testing Enhanced Memory System Health Check...")
        
        try:
            # Test main health endpoint
            health_response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if health_response.status_code != 200:
                self.log_test("Enhanced Memory Health Check", False, f"Health endpoint failed: HTTP {health_response.status_code}")
                return False
            
            health_data = health_response.json()
            services = health_data.get("services", {})
            
            # Check enhanced memory status
            enhanced_memory_status = services.get("enhanced_memory", "unknown")
            
            if enhanced_memory_status not in ["healthy", "connected", "enabled"]:
                self.log_test("Enhanced Memory Health Check", False, f"Enhanced memory status: {enhanced_memory_status}")
                return False
            
            # Test enhanced memory stats endpoint
            stats_response = requests.get(f"{BACKEND_URL}/enhanced-memory/stats", timeout=10)
            
            if stats_response.status_code != 200:
                self.log_test("Enhanced Memory Health Check", False, f"Stats endpoint failed: HTTP {stats_response.status_code}")
                return False
            
            stats_data = stats_response.json()
            health_info = stats_data.get("health", {})
            
            # Check MongoDB and Redis connections
            mongodb_connected = health_info.get("mongodb_connected", False)
            redis_connected = health_info.get("redis_connected", False)
            
            if not mongodb_connected:
                self.log_test("Enhanced Memory Health Check", False, "MongoDB not connected")
                return False
            
            # Redis is optional but should be noted
            redis_status = "connected" if redis_connected else "not connected (fallback to MongoDB only)"
            
            self.log_test("Enhanced Memory Health Check", True, f"MongoDB: connected, Redis: {redis_status}, Enhanced memory: {enhanced_memory_status}")
            return True
            
        except Exception as e:
            self.log_test("Enhanced Memory Health Check", False, f"Error: {str(e)}")
            return False

    def test_session_memory_stats(self):
        """Test 5: Session Memory Statistics"""
        print("📊 Testing Session Memory Statistics...")
        
        try:
            # Test session stats endpoint
            stats_response = requests.get(f"{BACKEND_URL}/enhanced-memory/session/{self.session_id}/stats", timeout=10)
            
            if stats_response.status_code != 200:
                self.log_test("Session Memory Stats", False, f"Session stats endpoint failed: HTTP {stats_response.status_code}")
                return False
            
            stats_data = stats_response.json()
            session_stats = stats_data.get("session_stats", {})
            
            # Check expected fields
            required_fields = ["session_id", "total_messages", "user_messages", "assistant_messages"]
            missing_fields = [field for field in required_fields if field not in session_stats]
            
            if missing_fields:
                self.log_test("Session Memory Stats", False, f"Missing stats fields: {missing_fields}")
                return False
            
            total_messages = session_stats.get("total_messages", 0)
            user_messages = session_stats.get("user_messages", 0)
            assistant_messages = session_stats.get("assistant_messages", 0)
            
            # We should have sent several messages by now
            if total_messages < 5:
                self.log_test("Session Memory Stats", False, f"Expected more messages, got {total_messages}")
                return False
            
            if user_messages == 0 or assistant_messages == 0:
                self.log_test("Session Memory Stats", False, f"Missing user ({user_messages}) or assistant ({assistant_messages}) messages")
                return False
            
            self.log_test("Session Memory Stats", True, f"Session stats: {total_messages} total, {user_messages} user, {assistant_messages} assistant messages")
            return True
            
        except Exception as e:
            self.log_test("Session Memory Stats", False, f"Error: {str(e)}")
            return False

    def test_redis_mongodb_hybrid(self):
        """Test 6: Redis + MongoDB Hybrid System"""
        print("🔄 Testing Redis + MongoDB Hybrid System...")
        
        try:
            # First, get enhanced memory stats to check Redis status
            stats_response = requests.get(f"{BACKEND_URL}/enhanced-memory/stats", timeout=10)
            
            if stats_response.status_code != 200:
                self.log_test("Redis + MongoDB Hybrid", False, f"Stats endpoint failed: HTTP {stats_response.status_code}")
                return False
            
            stats_data = stats_response.json()
            health_info = stats_data.get("health", {})
            
            mongodb_connected = health_info.get("mongodb_connected", False)
            redis_connected = health_info.get("redis_connected", False)
            redis_cache_limit = health_info.get("redis_cache_limit", 0)
            context_memory_limit = health_info.get("context_memory_limit", 0)
            
            if not mongodb_connected:
                self.log_test("Redis + MongoDB Hybrid", False, "MongoDB not connected")
                return False
            
            # Test that the system works regardless of Redis status
            # Send a few more messages to test caching behavior
            test_messages = [
                "This is a test message for caching",
                "Another message to test the hybrid system",
                "Testing Redis cache behavior"
            ]
            
            for i, msg in enumerate(test_messages):
                payload = {
                    "message": f"{msg} #{i+1}",
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code != 200:
                    self.log_test("Redis + MongoDB Hybrid", False, f"Failed to send test message {i+1}")
                    return False
                
                time.sleep(0.5)  # Small delay
            
            # Verify messages are retrievable (tests both Redis cache and MongoDB fallback)
            history_response = requests.get(f"{BACKEND_URL}/history/{self.session_id}", timeout=10)
            
            if history_response.status_code != 200:
                self.log_test("Redis + MongoDB Hybrid", False, f"Failed to retrieve history: HTTP {history_response.status_code}")
                return False
            
            history_data = history_response.json()
            messages = history_data.get("history", [])
            
            # Check that we have a good number of messages (indicating both systems are working)
            if len(messages) < 10:  # We've sent quite a few messages by now
                self.log_test("Redis + MongoDB Hybrid", False, f"Expected more messages in history, got {len(messages)}")
                return False
            
            # Test that recent messages are accessible (Redis cache test)
            recent_test_messages = [msg for msg in messages if "test message for caching" in msg.get("message", "")]
            
            if len(recent_test_messages) == 0:
                self.log_test("Redis + MongoDB Hybrid", False, "Recent test messages not found in history")
                return False
            
            redis_status = "enabled" if redis_connected else "disabled (MongoDB fallback)"
            
            self.log_test("Redis + MongoDB Hybrid", True, 
                         f"Hybrid system working: MongoDB connected, Redis {redis_status}, "
                         f"{len(messages)} total messages, cache limit: {redis_cache_limit}, "
                         f"context limit: {context_memory_limit}")
            return True
            
        except Exception as e:
            self.log_test("Redis + MongoDB Hybrid", False, f"Error: {str(e)}")
            return False

    def test_memory_system_integration(self):
        """Test 7: Memory System Integration - End-to-end test"""
        print("🔗 Testing Memory System Integration...")
        
        try:
            # Create a new session for clean testing
            integration_session_id = str(uuid.uuid4())
            
            # Step 1: Store some personal information
            personal_info = [
                "My favorite color is blue",
                "I live in San Francisco",
                "I have a dog named Max"
            ]
            
            for info in personal_info:
                payload = {
                    "message": info,
                    "session_id": integration_session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code != 200:
                    self.log_test("Memory System Integration", False, f"Failed to store: {info}")
                    return False
                
                time.sleep(1)
            
            # Step 2: Send some unrelated messages
            unrelated_messages = [
                "What's 2 + 2?",
                "Tell me about artificial intelligence",
                "How's the weather?"
            ]
            
            for msg in unrelated_messages:
                payload = {
                    "message": msg,
                    "session_id": integration_session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code != 200:
                    self.log_test("Memory System Integration", False, f"Failed to send: {msg}")
                    return False
                
                time.sleep(1)
            
            # Step 3: Test recall of each piece of information
            recall_tests = [
                ("What's my favorite color?", "blue"),
                ("Where do I live?", "san francisco"),
                ("What's my dog's name?", "max")
            ]
            
            successful_recalls = 0
            
            for question, expected_answer in recall_tests:
                payload = {
                    "message": question,
                    "session_id": integration_session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data.get("response", "").lower()
                    
                    if expected_answer in ai_response:
                        successful_recalls += 1
                
                time.sleep(1)
            
            # Step 4: Check session statistics
            stats_response = requests.get(f"{BACKEND_URL}/enhanced-memory/session/{integration_session_id}/stats", timeout=10)
            
            stats_success = False
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                session_stats = stats_data.get("session_stats", {})
                total_messages = session_stats.get("total_messages", 0)
                
                # We sent 9 messages total (3 personal + 3 unrelated + 3 questions)
                # Plus AI responses, so should be around 18+ messages
                if total_messages >= 15:
                    stats_success = True
            
            # Evaluate overall success
            if successful_recalls >= 2 and stats_success:  # At least 2 out of 3 recalls successful
                self.log_test("Memory System Integration", True, 
                             f"Integration successful: {successful_recalls}/3 recalls, stats working, "
                             f"total messages tracked: {session_stats.get('total_messages', 'unknown')}")
                return True
            else:
                self.log_test("Memory System Integration", False, 
                             f"Integration issues: {successful_recalls}/3 recalls, stats: {stats_success}")
                return False
                
        except Exception as e:
            self.log_test("Memory System Integration", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Enhanced Memory System tests"""
        print("🚀 Starting Enhanced Memory System Testing...")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        tests = [
            self.test_basic_memory_storage,
            self.test_memory_recall,
            self.test_context_persistence,
            self.test_enhanced_memory_health_check,
            self.test_session_memory_stats,
            self.test_redis_mongodb_hybrid,
            self.test_memory_system_integration
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
        
        print("=" * 80)
        print(f"🎯 Enhanced Memory System Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ ALL TESTS PASSED - Enhanced Memory System is working correctly!")
        elif passed >= total * 0.7:  # 70% pass rate
            print("⚠️ MOSTLY WORKING - Some issues detected but core functionality works")
        else:
            print("❌ CRITICAL ISSUES - Enhanced Memory System needs attention")
        
        return passed, total, self.test_results

if __name__ == "__main__":
    tester = EnhancedMemoryTester()
    passed, total, results = tester.run_all_tests()
    
    # Print detailed results
    print("\n" + "=" * 80)
    print("📋 DETAILED TEST RESULTS:")
    print("=" * 80)
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} {result['test']}")
        if result["details"]:
            print(f"    {result['details']}")
    
    print(f"\n🏁 Final Score: {passed}/{total} tests passed")