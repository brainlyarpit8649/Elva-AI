#!/usr/bin/env python3
"""
Test the new semantic memory system
"""

import requests
import json
import time

# Backend URL
BACKEND_URL = "https://0b30aab1-896e-477e-822b-002edcbac2b3.preview.emergentagent.com/api"

def test_chat(message, session_id="test_semantic_memory"):
    """Send a chat message and return the response"""
    url = f"{BACKEND_URL}/chat"
    data = {
        "message": message,
        "session_id": session_id,
        "user_id": "test_user"
    }
    
    print(f"🤖 Sending: {message}")
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response: {result['response']}")
        print(f"   Intent: {result.get('intent_data', {}).get('intent', 'none')}")
        return result
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None

def test_memory_stats():
    """Get memory statistics"""
    url = f"{BACKEND_URL}/memory/stats"
    
    print(f"📊 Getting memory stats...")
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Memory Stats:")
        print(f"   Total facts: {result.get('total_facts', 0)}")
        print(f"   Category counts: {result.get('category_counts', {})}")
        return result
    else:
        print(f"❌ Error getting stats: {response.status_code} - {response.text}")
        return None

def main():
    print("🧪 Testing Semantic Memory System\n")
    
    # Test 1: Store some facts with natural commands
    print("=== Test 1: Storing Facts ===")
    test_chat("Remember that I like samosas and murmura")
    time.sleep(1)
    test_chat("My name is Arpit")
    time.sleep(1)
    test_chat("I prefer working in the morning")
    time.sleep(1)
    
    # Test 2: Check memory stats
    print("\n=== Test 2: Memory Statistics ===")
    test_memory_stats()
    
    # Test 3: Recall information
    print("\n=== Test 3: Recalling Facts ===")
    test_chat("What do I like to eat?")
    time.sleep(1)
    test_chat("What's my name?")
    time.sleep(1)
    test_chat("What are my preferences?")
    time.sleep(1)
    
    # Test 4: Test deduplication by storing similar info
    print("\n=== Test 4: Testing Deduplication ===")
    test_chat("Remember that I like samosas")  # Should deduplicate with previous
    time.sleep(1)
    
    # Test 5: Final memory stats check
    print("\n=== Test 5: Final Memory Statistics ===")
    test_memory_stats()
    
    print("\n🎉 Semantic Memory Testing Complete!")

if __name__ == "__main__":
    main()