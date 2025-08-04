#!/usr/bin/env python3
"""
Verbose test to understand what's happening with memory responses
"""

import asyncio
import httpx
import json
import time

async def test_verbose():
    """Test with verbose output"""
    
    base_url = "http://localhost:8001/api"
    
    test_cases = [
        "What's my nickname?",
        "Remember that I love sushi", 
        "What do you remember about me?"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {message}")
        
        chat_data = {
            "message": message,
            "session_id": f"verbose_test_{i}",
            "user_id": "test_user"
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(f"{base_url}/chat", json=chat_data)
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"⏱️  Duration: {duration:.2f}s")
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"📥 Response: {result.get('response', 'No response')}")
                    print(f"🎯 Intent: {result.get('intent_data', {}).get('intent', 'unknown')}")
                    print(f"🆔 Message ID: {result.get('id', 'unknown')}")
                else:
                    print(f"❌ Error: {response.text}")
        
        except asyncio.TimeoutError:
            print(f"⏰ Request timed out after 20s")
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        # Wait between tests
        await asyncio.sleep(2)

if __name__ == "__main__":
    print("🚀 Verbose Memory Test")
    asyncio.run(test_verbose())
    print("\n✨ Tests completed!")