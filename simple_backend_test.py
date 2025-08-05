#!/usr/bin/env python3
"""
Simple Backend Health Test for Elva AI
"""

import requests
import json

# Backend URL from frontend/.env
BACKEND_URL = "https://ee5e777b-dc22-480e-8057-5ec09c03a73c.preview.emergentagent.com/api"

def test_health_endpoint():
    """Test health endpoint"""
    try:
        print("🔍 Testing Health Endpoint...")
        response = requests.get(f"{BACKEND_URL}/health", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health endpoint working")
            
            # Check Gmail integration
            gmail_integration = data.get("gmail_api_integration", {})
            if gmail_integration:
                print(f"📧 Gmail Integration Status: {gmail_integration.get('status')}")
                print(f"📧 OAuth2 Flow: {gmail_integration.get('oauth2_flow')}")
                print(f"📧 Credentials Configured: {gmail_integration.get('credentials_configured')}")
                print(f"📧 Endpoints: {len(gmail_integration.get('endpoints', []))}")
            
            # Check Groq API
            hybrid_ai = data.get("advanced_hybrid_ai_system", {})
            if hybrid_ai:
                print(f"🤖 Groq API Key: {hybrid_ai.get('groq_api_key')}")
                print(f"🤖 Claude API Key: {hybrid_ai.get('claude_api_key')}")
                print(f"🤖 Groq Model: {hybrid_ai.get('groq_model')}")
                print(f"🤖 Claude Model: {hybrid_ai.get('claude_model')}")
            
            # Check N8N webhook
            print(f"🔗 N8N Webhook: {data.get('n8n_webhook')}")
            
            return True
        else:
            print(f"❌ Health endpoint failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint error: {str(e)}")
        return False

def test_gmail_auth():
    """Test Gmail auth endpoint"""
    try:
        print("\n🔍 Testing Gmail Auth Endpoint...")
        response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("auth_url"):
                auth_url = data.get("auth_url")
                
                # Check if new client_id is in the URL
                expected_client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
                if expected_client_id in auth_url:
                    print("✅ Gmail auth working with new client_id")
                    return True
                else:
                    print("❌ New client_id not found in auth URL")
                    return False
            else:
                print("❌ Failed to generate auth URL")
                return False
        else:
            print(f"❌ Gmail auth failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Gmail auth error: {str(e)}")
        return False

def test_simple_chat():
    """Test simple chat without complex intents"""
    try:
        print("\n🔍 Testing Simple Chat...")
        payload = {
            "message": "Hello",
            "session_id": "test-session",
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "")
            
            # Check for error messages
            if "sorry i've encountered an error" in response_text.lower():
                print("❌ Chat contains error message")
                return False
            elif response_text:
                print("✅ Chat working - no error messages")
                return True
            else:
                print("❌ Empty chat response")
                return False
        else:
            print(f"❌ Chat failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 SIMPLE BACKEND TESTING FOR ELVA AI")
    print("=" * 50)
    
    tests = [
        test_health_endpoint,
        test_gmail_auth,
        test_simple_chat
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ BACKEND IS WORKING!")
    else:
        print("❌ SOME ISSUES DETECTED")