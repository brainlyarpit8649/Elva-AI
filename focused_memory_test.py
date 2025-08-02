#!/usr/bin/env python3
"""
Focused Conversation Memory Test
Tests the specific conversation memory issue where AI forgets names
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://c20efb94-1a9f-42d9-a126-b5157ee976a4.preview.emergentagent.com/api"

def test_conversation_memory_detailed():
    """Detailed test of conversation memory system"""
    print("🧠 DETAILED CONVERSATION MEMORY TEST")
    print("=" * 60)
    
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")
    
    # Step 1: Send name introduction
    print("\n1️⃣ Introducing name...")
    payload = {
        "message": "Hi, my name is Arpit Kumar",
        "session_id": session_id,
        "user_id": "test_user"
    }
    
    response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Name introduction successful")
        print(f"   AI Response: {data.get('response', '')[:100]}...")
    else:
        print(f"❌ Name introduction failed: HTTP {response.status_code}")
        return False
    
    # Step 2: Check message memory stats immediately
    print("\n2️⃣ Checking message memory stats after name introduction...")
    response = requests.get(f"{BACKEND_URL}/message-memory/stats/{session_id}", timeout=10)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Memory stats: {stats['total_messages']} total, {stats['user_messages']} user, {stats['assistant_messages']} assistant")
        
        if stats['total_messages'] >= 2:  # Should have user + assistant message
            print("✅ Messages are being saved to memory")
        else:
            print("❌ Messages not being saved properly")
            return False
    else:
        print(f"❌ Memory stats failed: HTTP {response.status_code}")
        return False
    
    # Step 3: Check full context
    print("\n3️⃣ Checking full conversation context...")
    response = requests.get(f"{BACKEND_URL}/message-memory/full-context/{session_id}", timeout=10)
    
    if response.status_code == 200:
        context_data = response.json()
        full_context = context_data.get('full_context', '')
        
        print(f"✅ Full context retrieved ({len(full_context)} chars)")
        
        if "arpit" in full_context.lower() and "kumar" in full_context.lower():
            print("✅ Name 'Arpit Kumar' found in full context")
        else:
            print("❌ Name 'Arpit Kumar' NOT found in full context")
            print(f"   Context preview: {full_context[:200]}...")
            return False
    else:
        print(f"❌ Full context failed: HTTP {response.status_code}")
        return False
    
    # Step 4: Send a few filler messages
    print("\n4️⃣ Sending filler messages...")
    filler_messages = [
        "What's the weather like today?",
        "Tell me about artificial intelligence",
        "How do I learn Python programming?"
    ]
    
    for i, message in enumerate(filler_messages, 1):
        time.sleep(2)  # Small delay
        payload = {
            "message": message,
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Filler message {i} sent: {message[:30]}...")
        else:
            print(f"❌ Filler message {i} failed: HTTP {response.status_code}")
            return False
    
    # Step 5: Check memory stats again
    print("\n5️⃣ Checking memory stats after filler messages...")
    response = requests.get(f"{BACKEND_URL}/message-memory/stats/{session_id}", timeout=10)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Updated memory stats: {stats['total_messages']} total messages")
        
        # Should have: 1 name intro + 3 filler messages + their AI responses = 8 total
        expected_min = 6  # At least 6 messages
        if stats['total_messages'] >= expected_min:
            print(f"✅ Message count looks good (>= {expected_min})")
        else:
            print(f"❌ Message count too low: {stats['total_messages']} < {expected_min}")
            return False
    else:
        print(f"❌ Memory stats failed: HTTP {response.status_code}")
        return False
    
    # Step 6: Ask for name - THE CRITICAL TEST
    print("\n6️⃣ CRITICAL TEST: Asking for name...")
    time.sleep(3)  # Ensure some time has passed
    
    payload = {
        "message": "What is my name?",
        "session_id": session_id,
        "user_id": "test_user"
    }
    
    response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        response_text = data.get("response", "")
        
        print(f"✅ Name recall response received")
        print(f"   AI Response: {response_text}")
        
        # Check if name is remembered
        if "arpit" in response_text.lower() and "kumar" in response_text.lower():
            print("🎉 SUCCESS: AI correctly remembered the name 'Arpit Kumar'!")
            return True
        else:
            print("❌ FAILURE: AI did not remember the name 'Arpit Kumar'")
            
            # Additional debugging - check if context is being passed
            print("\n🔍 DEBUGGING: Checking if context is being passed to AI...")
            
            # Check full context again
            response = requests.get(f"{BACKEND_URL}/message-memory/full-context/{session_id}", timeout=10)
            if response.status_code == 200:
                context_data = response.json()
                full_context = context_data.get('full_context', '')
                
                if "arpit" in full_context.lower():
                    print("✅ Name is still in memory context")
                    print("❌ ISSUE: Context exists but AI is not using it properly")
                else:
                    print("❌ Name is missing from memory context")
                    print("❌ ISSUE: Memory system is not preserving the name")
            
            return False
    else:
        print(f"❌ Name recall failed: HTTP {response.status_code}")
        return False

def test_search_functionality():
    """Test the search functionality"""
    print("\n🔍 TESTING SEARCH FUNCTIONALITY")
    print("=" * 40)
    
    # Use a known session with data
    session_id = str(uuid.uuid4())
    
    # First, create some data
    payload = {
        "message": "My favorite color is blue and I love pizza",
        "session_id": session_id,
        "user_id": "test_user"
    }
    
    response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
    
    if response.status_code != 200:
        print("❌ Failed to create test data for search")
        return False
    
    time.sleep(2)
    
    # Now search for "blue"
    search_payload = {
        "query": "blue"
    }
    
    response = requests.post(f"{BACKEND_URL}/message-memory/search/{session_id}", 
                           json=search_payload, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        results_found = data.get("results_found", 0)
        
        if results_found > 0:
            print(f"✅ Search working: Found {results_found} messages containing 'blue'")
            return True
        else:
            print("❌ Search not working: No results found for 'blue'")
            return False
    else:
        print(f"❌ Search endpoint failed: HTTP {response.status_code}")
        return False

def main():
    """Run focused conversation memory tests"""
    print("🚀 FOCUSED CONVERSATION MEMORY TESTING")
    print("Testing the specific issue where AI forgets names and earlier context")
    print("=" * 80)
    
    tests = [
        ("Detailed Conversation Memory", test_conversation_memory_detailed),
        ("Search Functionality", test_search_functionality)
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
        
        print("-" * 60)
    
    print("=" * 80)
    print(f"🎯 FINAL RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL CONVERSATION MEMORY TESTS PASSED!")
        print("✅ The conversation memory system is working correctly")
    else:
        print("❌ CONVERSATION MEMORY ISSUES DETECTED")
        print("🔧 The AI is not properly remembering earlier conversation context")
    
    return passed, total

if __name__ == "__main__":
    passed, total = main()
    exit(0 if passed == total else 1)