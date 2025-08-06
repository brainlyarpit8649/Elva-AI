#!/usr/bin/env python3
"""
Simple Enhanced Memory Test - Direct API Testing
Focus on diagnosing the context retrieval issue with simpler approach
"""

import requests
import json
import uuid
import time

# Test configuration
BACKEND_URL = "https://ed44aeba-7cef-4fcd-8d35-8bddafadc1d4.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def test_memory_system():
    """Test the enhanced memory system step by step"""
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    
    print(f"🧪 Testing Enhanced Conversation Memory System")
    print(f"📋 Session ID: {session_id}")
    print("=" * 60)
    
    # Test 1: Check unified memory stats
    print("\n1️⃣ Testing Unified Memory Stats Endpoint")
    try:
        response = requests.get(f"{API_BASE}/unified-memory/stats", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Memory Status: {stats.get('status', 'unknown')}")
            print(f"   📊 Health: {stats.get('health', {})}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Send name message
    print("\n2️⃣ Sending Name Message")
    try:
        chat_request = {
            "message": "My name is Arpit",
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{API_BASE}/chat", json=chat_request, timeout=30)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            chat_response = response.json()
            print(f"   ✅ AI Response: {chat_response.get('response', '')[:100]}...")
            print(f"   📝 Message ID: {chat_response.get('id')}")
        else:
            print(f"   ❌ Error: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return
    
    # Wait a moment for message to be processed
    time.sleep(2)
    
    # Test 3: Check session stats
    print("\n3️⃣ Checking Session Memory Stats")
    try:
        response = requests.get(f"{API_BASE}/unified-memory/session/{session_id}/stats", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            session_stats = stats.get('session_stats', {})
            print(f"   ✅ Total Messages: {session_stats.get('total_messages', 0)}")
            print(f"   👤 User Messages: {session_stats.get('user_messages', 0)}")
            print(f"   🤖 Assistant Messages: {session_stats.get('assistant_messages', 0)}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 4: Send a few more messages
    print("\n4️⃣ Sending Additional Messages")
    additional_messages = [
        "How are you today?",
        "What's the weather like?"
    ]
    
    for i, message in enumerate(additional_messages):
        try:
            chat_request = {
                "message": message,
                "session_id": session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{API_BASE}/chat", json=chat_request, timeout=30)
            print(f"   Message {i+1}: {response.status_code} - {message}")
            if response.status_code == 200:
                chat_response = response.json()
                print(f"      Response: {chat_response.get('response', '')[:50]}...")
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ Exception on message {i+1}: {e}")
    
    # Test 5: Ask for name recall
    print("\n5️⃣ Testing Name Recall")
    try:
        chat_request = {
            "message": "What is my name?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{API_BASE}/chat", json=chat_request, timeout=30)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            chat_response = response.json()
            ai_response = chat_response.get('response', '')
            print(f"   🤖 AI Response: {ai_response}")
            
            # Check if AI remembers the name
            remembers_name = 'arpit' in ai_response.lower()
            if remembers_name:
                print("   ✅ SUCCESS: AI remembers the name!")
            else:
                print("   ❌ FAILURE: AI does NOT remember the name")
                print("   🚨 This confirms the context retrieval issue")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 6: Final session stats
    print("\n6️⃣ Final Session Stats")
    try:
        response = requests.get(f"{API_BASE}/unified-memory/session/{session_id}/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            session_stats = stats.get('session_stats', {})
            print(f"   ✅ Final Total Messages: {session_stats.get('total_messages', 0)}")
            print(f"   📊 User/Assistant: {session_stats.get('user_messages', 0)}/{session_stats.get('assistant_messages', 0)}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS SUMMARY:")
    print("If AI does NOT remember the name 'Arpit', then:")
    print("1. Enhanced Memory System may not be storing messages correctly")
    print("2. Context retrieval (get_context_for_ai) may be broken")
    print("3. Context may not be passed to AI models properly")
    print("4. This confirms the issue reported in the review request")
    print("=" * 60)

if __name__ == "__main__":
    test_memory_system()
"""
Simple Backend Testing for Conversation Memory and Gmail Authentication
Focused tests with shorter timeouts and better error handling
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://ed44aeba-7cef-4fcd-8d35-8bddafadc1d4.preview.emergentagent.com/api"

def test_basic_chat():
    """Test basic chat functionality"""
    print("🔍 Testing Basic Chat Functionality...")
    
    session_id = str(uuid.uuid4())
    
    try:
        payload = {
            "message": "Hello, how are you?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Basic chat working: {data.get('response', '')[:100]}...")
            return True, session_id
        else:
            print(f"❌ Basic chat failed: HTTP {response.status_code}")
            return False, session_id
            
    except Exception as e:
        print(f"❌ Basic chat error: {str(e)}")
        return False, session_id

def test_name_memory():
    """Test name memory functionality"""
    print("🧠 Testing Name Memory...")
    
    session_id = str(uuid.uuid4())
    
    try:
        # Step 1: Introduce name
        payload = {
            "message": "Hi, my name is Arpit Kumar",
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Name introduction failed: HTTP {response.status_code}")
            return False
        
        print("✅ Name introduced successfully")
        
        # Step 2: Send a few messages
        messages = ["What's the weather?", "Tell me about AI"]
        
        for msg in messages:
            time.sleep(2)
            payload = {
                "message": msg,
                "session_id": session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
            if response.status_code == 200:
                print(f"✅ Sent: {msg}")
            else:
                print(f"❌ Failed to send: {msg}")
        
        # Step 3: Ask for name
        time.sleep(3)
        payload = {
            "message": "What is my name?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "").lower()
            
            if "arpit" in response_text and "kumar" in response_text:
                print(f"✅ Name memory working: {data.get('response')}")
                return True
            else:
                print(f"❌ Name not remembered: {data.get('response')}")
                return False
        else:
            print(f"❌ Name recall failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Name memory error: {str(e)}")
        return False

def test_gmail_auth():
    """Test Gmail authentication"""
    print("📧 Testing Gmail Authentication...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10, allow_redirects=False)
        
        if response.status_code in [200, 307, 302]:
            # Check if it's a redirect to Google OAuth
            if response.status_code in [307, 302]:
                location = response.headers.get('location', '')
                if "accounts.google.com" in location:
                    print("✅ Gmail auth redirects to Google OAuth")
                    
                    # Check for new client ID
                    expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                    if expected_client_id in location:
                        print("✅ New client ID found in OAuth URL")
                        return True
                    else:
                        print("❌ New client ID not found in OAuth URL")
                        return False
                else:
                    print(f"❌ Unexpected redirect location: {location}")
                    return False
            else:
                print("✅ Gmail auth endpoint responding")
                return True
        else:
            print(f"❌ Gmail auth failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Gmail auth error: {str(e)}")
        return False

def test_gmail_status():
    """Test Gmail status endpoint"""
    print("📊 Testing Gmail Status...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("credentials_configured") == True:
                print("✅ Gmail credentials configured")
                return True
            else:
                print(f"❌ Gmail credentials not configured: {data.get('credentials_configured')}")
                return False
        else:
            print(f"❌ Gmail status failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Gmail status error: {str(e)}")
        return False

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing Health Check...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check key components
            status = data.get("status")
            mongodb = data.get("services", {}).get("mongodb")
            gmail_integration = data.get("gmail_api_integration", {})
            
            print(f"✅ Health check: status={status}, mongodb={mongodb}")
            print(f"✅ Gmail integration: {gmail_integration.get('status', 'unknown')}")
            
            return status == "healthy"
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def main():
    """Run all simple tests"""
    print("🚀 Starting Simple Backend Tests for Conversation Memory & Gmail Auth")
    print("=" * 70)
    
    tests = [
        ("Health Check", test_health_check),
        ("Basic Chat", lambda: test_basic_chat()[0]),
        ("Name Memory", test_name_memory),
        ("Gmail Auth", test_gmail_auth),
        ("Gmail Status", test_gmail_status)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
        
        print("-" * 40)
    
    print("=" * 70)
    print(f"🎯 SUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY WORKING - Minor issues detected")
    else:
        print("❌ CRITICAL ISSUES - Multiple failures detected")
    
    return passed, total

if __name__ == "__main__":
    passed, total = main()
    exit(0 if passed == total else 1)