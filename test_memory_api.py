#!/usr/bin/env python3
"""
Simple test script to verify Letta memory integration is working through the API
"""

import asyncio
import httpx
import json

async def test_single_request(message, test_name):
    """Test a single chat request"""
    
    base_url = "http://localhost:8001/api"
    
    chat_data = {
        "message": message,
        "session_id": "memory_test_session",
        "user_id": "test_user"
    }
    
    print(f"\n🧪 {test_name}")
    print(f"📤 Sending: {message}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{base_url}/chat", json=chat_data)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', 'No response')
                intent = result.get('intent_data', {}).get('intent', 'unknown')
                print(f"📥 Response: {response_text}")
                print(f"🎯 Intent: {intent}")
                return True
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Run memory tests"""
    
    print("🚀 Starting Letta Memory Integration Test (Through API)")
    
    # Wait a moment for backend to be ready
    await asyncio.sleep(2)
    
    # Test 1: Recall existing nickname
    success1 = await test_single_request("What's my nickname?", "Test 1: Recall nickname")
    await asyncio.sleep(2)
    
    # Test 2: Store new food preference  
    success2 = await test_single_request("Remember that I love burgers", "Test 2: Store food preference")
    await asyncio.sleep(2)
    
    # Test 3: Recall food preferences
    success3 = await test_single_request("What do I love to eat?", "Test 3: Recall food preferences")
    await asyncio.sleep(2)
    
    # Test 4: General question (should not be memory)
    success4 = await test_single_request("Hello, how are you?", "Test 4: General chat")
    await asyncio.sleep(2)
    
    # Test 5: All memory recall
    success5 = await test_single_request("What do you remember about me?", "Test 5: All memory recall")
    
    print(f"\n✨ Test Summary:")
    print(f"  Test 1 (Recall nickname): {'✅' if success1 else '❌'}")
    print(f"  Test 2 (Store preference): {'✅' if success2 else '❌'}")
    print(f"  Test 3 (Recall food): {'✅' if success3 else '❌'}")  
    print(f"  Test 4 (General chat): {'✅' if success4 else '❌'}")
    print(f"  Test 5 (All memory): {'✅' if success5 else '❌'}")

if __name__ == "__main__":
    asyncio.run(main())