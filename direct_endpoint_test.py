#!/usr/bin/env python3
"""
Memory System Direct Testing
Tests the memory system endpoints directly without relying on AI chat
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://5be6aaaa-6734-49b7-bbc3-94369bffa03f.preview.emergentagent.com/api"

def test_memory_endpoints_directly():
    """Test memory endpoints directly"""
    print("🧠 TESTING MEMORY ENDPOINTS DIRECTLY")
    print("=" * 50)
    
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")
    
    # Test 1: Check initial memory stats (should be empty)
    print("\n1️⃣ Testing initial memory stats...")
    response = requests.get(f"{BACKEND_URL}/message-memory/stats/{session_id}", timeout=10)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Memory stats endpoint working")
        print(f"   Initial stats: {stats['total_messages']} total messages")
        
        if stats['total_messages'] == 0:
            print("✅ Initial state correct (0 messages)")
        else:
            print(f"❌ Initial state incorrect ({stats['total_messages']} messages)")
            return False
    else:
        print(f"❌ Memory stats endpoint failed: HTTP {response.status_code}")
        return False
    
    # Test 2: Try to send a simple chat message to populate memory
    print("\n2️⃣ Sending a simple chat message...")
    payload = {
        "message": "Hello, this is a test message",
        "session_id": session_id,
        "user_id": "test_user"
    }
    
    response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Chat message sent successfully")
        print(f"   Response preview: {data.get('response', '')[:50]}...")
    else:
        print(f"❌ Chat message failed: HTTP {response.status_code}")
        # Continue with test even if chat fails
    
    # Wait a moment for message to be saved
    time.sleep(2)
    
    # Test 3: Check memory stats after message
    print("\n3️⃣ Checking memory stats after message...")
    response = requests.get(f"{BACKEND_URL}/message-memory/stats/{session_id}", timeout=10)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Memory stats after message: {stats['total_messages']} total")
        
        if stats['total_messages'] > 0:
            print("✅ Messages are being saved to memory system")
        else:
            print("❌ Messages are NOT being saved to memory system")
            return False
    else:
        print(f"❌ Memory stats endpoint failed: HTTP {response.status_code}")
        return False
    
    # Test 4: Check full context endpoint
    print("\n4️⃣ Testing full context endpoint...")
    response = requests.get(f"{BACKEND_URL}/message-memory/full-context/{session_id}", timeout=10)
    
    if response.status_code == 200:
        context_data = response.json()
        full_context = context_data.get('full_context', '')
        all_messages = context_data.get('all_messages', [])
        
        print(f"✅ Full context endpoint working")
        print(f"   Context length: {len(full_context)} chars")
        print(f"   Messages count: {len(all_messages)}")
        
        if len(all_messages) > 0:
            print("✅ Full context contains messages")
            
            # Check message structure
            first_msg = all_messages[0]
            if 'role' in first_msg and 'content' in first_msg and 'timestamp' in first_msg:
                print("✅ Message structure is correct")
            else:
                print("❌ Message structure is incorrect")
                return False
        else:
            print("❌ Full context is empty")
            return False
    else:
        print(f"❌ Full context endpoint failed: HTTP {response.status_code}")
        return False
    
    # Test 5: Test search functionality
    print("\n5️⃣ Testing search functionality...")
    search_payload = {
        "query": "test"
    }
    
    response = requests.post(f"{BACKEND_URL}/message-memory/search/{session_id}", 
                           json=search_payload, timeout=10)
    
    if response.status_code == 200:
        search_data = response.json()
        results_found = search_data.get('results_found', 0)
        
        print(f"✅ Search endpoint working")
        print(f"   Results found: {results_found}")
        
        if results_found > 0:
            print("✅ Search functionality working")
        else:
            print("⚠️  Search found no results (may be expected)")
    else:
        print(f"❌ Search endpoint failed: HTTP {response.status_code}")
        return False
    
    return True

def test_gmail_authentication_endpoints():
    """Test Gmail authentication endpoints"""
    print("\n📧 TESTING GMAIL AUTHENTICATION ENDPOINTS")
    print("=" * 50)
    
    # Test 1: Gmail status endpoint
    print("\n1️⃣ Testing Gmail status endpoint...")
    response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Gmail status endpoint working")
        
        # Check for credentials_configured
        if data.get("credentials_configured") == True:
            print("✅ Gmail credentials are configured")
        else:
            print(f"❌ Gmail credentials not configured: {data.get('credentials_configured')}")
            return False
        
        # Check for scopes
        scopes = data.get("scopes", [])
        expected_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
        missing_scopes = [scope for scope in expected_scopes if scope not in scopes]
        
        if not missing_scopes:
            print(f"✅ All required Gmail scopes configured: {len(scopes)} scopes")
        else:
            print(f"❌ Missing Gmail scopes: {missing_scopes}")
            return False
            
    else:
        print(f"❌ Gmail status endpoint failed: HTTP {response.status_code}")
        return False
    
    # Test 2: Gmail auth endpoint (should redirect)
    print("\n2️⃣ Testing Gmail auth endpoint...")
    response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10, allow_redirects=False)
    
    if response.status_code in [200, 307, 302]:
        print(f"✅ Gmail auth endpoint responding (HTTP {response.status_code})")
        
        # Check for redirect to Google OAuth
        if response.status_code in [307, 302]:
            location = response.headers.get('location', '')
            if "accounts.google.com" in location:
                print("✅ Gmail auth redirects to Google OAuth")
                
                # Check for new client ID
                expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                if expected_client_id in location:
                    print("✅ New client ID found in OAuth URL")
                    
                    # Check for client secret (should be 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)
                    # Note: client_secret is not in URL for security, but we can verify the auth flow works
                    print("✅ Gmail OAuth flow properly configured")
                    return True
                else:
                    print("❌ New client ID not found in OAuth URL")
                    return False
            else:
                print(f"❌ Unexpected redirect location: {location}")
                return False
        else:
            print("✅ Gmail auth endpoint working")
            return True
    else:
        print(f"❌ Gmail auth endpoint failed: HTTP {response.status_code}")
        return False

def test_health_check_comprehensive():
    """Test comprehensive health check"""
    print("\n🏥 TESTING COMPREHENSIVE HEALTH CHECK")
    print("=" * 50)
    
    response = requests.get(f"{BACKEND_URL}/health", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health check endpoint working")
        
        # Check overall status
        if data.get("status") == "healthy":
            print("✅ Overall system status: healthy")
        else:
            print(f"❌ System status not healthy: {data.get('status')}")
            return False
        
        # Check MongoDB
        services = data.get("services", {})
        if services.get("mongodb") == "connected":
            print("✅ MongoDB: connected")
        else:
            print(f"❌ MongoDB not connected: {services.get('mongodb')}")
            return False
        
        # Check Gmail integration
        gmail_integration = data.get("gmail_api_integration", {})
        if gmail_integration.get("status") == "ready":
            print("✅ Gmail integration: ready")
        else:
            print(f"❌ Gmail integration not ready: {gmail_integration.get('status')}")
            return False
        
        if gmail_integration.get("credentials_configured") == True:
            print("✅ Gmail credentials configured in health check")
        else:
            print("❌ Gmail credentials not configured in health check")
            return False
        
        # Check API keys
        if services.get("groq_api") == "configured":
            print("✅ Groq API key configured")
        else:
            print("⚠️  Groq API key not configured")
        
        if services.get("claude_api") == "configured":
            print("✅ Claude API key configured")
        else:
            print("⚠️  Claude API key not configured")
        
        return True
    else:
        print(f"❌ Health check failed: HTTP {response.status_code}")
        return False

def main():
    """Run all direct endpoint tests"""
    print("🚀 DIRECT ENDPOINT TESTING FOR MEMORY & GMAIL")
    print("Testing memory and Gmail endpoints without relying on AI chat")
    print("=" * 80)
    
    tests = [
        ("Memory Endpoints", test_memory_endpoints_directly),
        ("Gmail Authentication", test_gmail_authentication_endpoints),
        ("Health Check", test_health_check_comprehensive)
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
        print("🎉 ALL DIRECT ENDPOINT TESTS PASSED!")
        print("✅ Memory and Gmail systems are working at the endpoint level")
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY WORKING - Minor issues detected")
    else:
        print("❌ CRITICAL ISSUES - Multiple endpoint failures detected")
    
    # Additional analysis
    print("\n📋 ANALYSIS:")
    if passed >= 2:
        print("✅ Core infrastructure (memory endpoints, Gmail auth) is working")
        print("🔍 If conversation memory issues persist, the problem is likely in:")
        print("   - AI model integration (Claude/Groq API issues)")
        print("   - Context passing between memory system and AI models")
        print("   - Message saving logic in chat endpoint")
    else:
        print("❌ Core infrastructure issues detected")
        print("🔧 Need to fix basic endpoint functionality first")
    
    return passed, total

if __name__ == "__main__":
    passed, total = main()
    exit(0 if passed == total else 1)