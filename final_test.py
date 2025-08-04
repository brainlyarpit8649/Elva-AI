#!/usr/bin/env python3
"""
Final comprehensive test to verify the timeout issue is resolved
"""

import asyncio
import httpx
import json
import time

async def test_comprehensive():
    """Comprehensive test with various scenarios"""
    
    base_url = "http://localhost:8001/api"
    
    test_cases = [
        {"message": "Hello, I'm testing the system", "expected_type": "normal"},
        {"message": "Remember my favorite color is blue", "expected_type": "memory_store"},
        {"message": "What's my favorite color?", "expected_type": "memory_recall"},
        {"message": "Send an email to john@example.com about the meeting", "expected_type": "intent_action"},
        {"message": "How are you today?", "expected_type": "general_chat"}
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['message']}")
        
        chat_data = {
            "message": test_case["message"],
            "session_id": f"final_test_{i}",
            "user_id": "test_user"
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{base_url}/chat", json=chat_data)
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"⏱️  Duration: {duration:.2f}s")
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', 'No response')
                    intent = result.get('intent_data', {}).get('intent', 'unknown')
                    
                    print(f"📥 Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                    print(f"🎯 Intent: {intent}")
                    
                    # Check if we got an emergency fallback response
                    emergency_responses = [
                        "I'm ready to assist you! How can I help?",
                        "I'm here to help! What would you like to know?",
                        "Sorry, I've encountered an error"
                    ]
                    
                    is_emergency = any(emergency in response_text for emergency in emergency_responses)
                    if is_emergency:
                        print("❌ EMERGENCY FALLBACK DETECTED - This indicates the original timeout issue")
                    else:
                        print("✅ Normal response received - Timeout issue resolved")
                        success_count += 1
                        
                else:
                    print(f"❌ Error: {response.text}")
        
        except asyncio.TimeoutError:
            print(f"⏰ Request timed out after 30s")
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        # Wait between tests
        await asyncio.sleep(1)
    
    print(f"\n📈 Final Results: {success_count}/{total_tests} tests passed")
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED - Timeout issue completely resolved!")
    else:
        print(f"⚠️ {total_tests - success_count} tests still showing issues")

if __name__ == "__main__":
    print("🚀 Final Comprehensive Test")
    asyncio.run(test_comprehensive())
    print("\n✨ Testing completed!")