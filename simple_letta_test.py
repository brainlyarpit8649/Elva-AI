#!/usr/bin/env python3
"""
Simple test script to verify Letta memory integration is working
"""

import asyncio
import httpx
import json

async def test_letta_memory():
    """Test Letta memory system with the backend"""
    
    base_url = "http://localhost:8001/api"
    
    # Test 1: Ask what the AI remembers (recall)
    print("🧪 Test 1: Recall existing memory")
    chat_data = {
        "message": "What's my nickname?",
        "session_id": "test_session_123",
        "user_id": "test_user"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{base_url}/chat", json=chat_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Response: {result.get('response', 'No response')}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test 2: Store a new fact
    print("\n🧪 Test 2: Store new memory")
    chat_data2 = {
        "message": "Remember that I love samosas",
        "session_id": "test_session_123", 
        "user_id": "test_user"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{base_url}/chat", json=chat_data2)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Storage response: {result.get('response', 'No response')}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        
    await asyncio.sleep(2)
    
    # Test 3: Recall the new fact
    print("\n🧪 Test 3: Recall new fact")
    chat_data3 = {
        "message": "What do I love to eat?",
        "session_id": "test_session_123",
        "user_id": "test_user"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{base_url}/chat", json=chat_data3)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Recall response: {result.get('response', 'No response')}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")

    # Test 4: Check health endpoint
    print("\n🧪 Test 4: Health check")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health status: {result.get('status', 'unknown')}")
                print(f"✅ Memory enabled: {result.get('services', {}).get('semantic_memory', 'unknown')}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Letta Memory Integration Test")
    asyncio.run(test_letta_memory())
    print("\n✨ Test completed!")