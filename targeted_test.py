#!/usr/bin/env python3
"""
Targeted Backend Testing for Review Request Issues
Focus on the specific problems mentioned:
1. Chat returning "sorry I've encountered an error" messages
2. Gmail button functionality not working
3. Authentication/credential issues
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://62aee014-87df-4846-a0fa-78e485afb511.preview.emergentagent.com/api"

def test_chat_error_messages():
    """Test if chat is returning 'sorry I've encountered an error' messages"""
    print("🔍 Testing Chat Error Messages...")
    
    session_id = str(uuid.uuid4())
    test_messages = ["Hello", "Hi", "How are you?"]
    
    for message in test_messages:
        try:
            payload = {
                "message": message,
                "session_id": session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                
                if "sorry i've encountered an error" in response_text:
                    print(f"❌ ISSUE FOUND: '{message}' returns error message: {response_text}")
                    return False
                else:
                    print(f"✅ '{message}': Normal response ({len(response_text)} chars)")
            else:
                print(f"❌ HTTP Error for '{message}': {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout for '{message}' - server may be slow but not returning error messages")
        except Exception as e:
            print(f"❌ Error testing '{message}': {str(e)}")
            return False
    
    print("✅ No 'sorry I've encountered an error' messages found")
    return True

def test_gmail_button_functionality():
    """Test Gmail button functionality - OAuth URL generation"""
    print("🔍 Testing Gmail Button Functionality...")
    
    try:
        # Test Gmail auth endpoint (what the Gmail button calls)
        response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success") and data.get("auth_url"):
                auth_url = data.get("auth_url")
                
                # Check if it's a proper Google OAuth URL
                if "accounts.google.com/o/oauth2/auth" in auth_url:
                    print("✅ Gmail button functionality working - OAuth URL generated correctly")
                    print(f"   Auth URL: {auth_url[:100]}...")
                    return True
                else:
                    print(f"❌ Invalid OAuth URL generated: {auth_url}")
                    return False
            else:
                print(f"❌ Gmail auth failed: {data}")
                return False
        else:
            print(f"❌ Gmail auth endpoint error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Gmail button test error: {str(e)}")
        return False

def test_credentials_and_auth():
    """Test authentication and credential issues"""
    print("🔍 Testing Credentials and Authentication...")
    
    try:
        # Test Gmail status to check credentials
        response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            credentials_configured = data.get("credentials_configured")
            if credentials_configured == True:
                print("✅ Gmail credentials properly configured")
            else:
                print(f"❌ Gmail credentials issue: {credentials_configured}")
                return False
            
            # Check scopes
            scopes = data.get("scopes", [])
            if len(scopes) >= 4:
                print(f"✅ Gmail scopes configured: {len(scopes)} scopes")
            else:
                print(f"❌ Insufficient Gmail scopes: {len(scopes)}")
                return False
            
            return True
        else:
            print(f"❌ Gmail status endpoint error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Credentials test error: {str(e)}")
        return False

def test_health_check():
    """Test overall system health"""
    print("🔍 Testing System Health...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check overall status
            if data.get("status") == "healthy":
                print("✅ System status: healthy")
            else:
                print(f"❌ System not healthy: {data.get('status')}")
                return False
            
            # Check key integrations
            mongodb = data.get("mongodb")
            if mongodb == "connected":
                print("✅ MongoDB: connected")
            else:
                print(f"❌ MongoDB issue: {mongodb}")
                return False
            
            # Check Gmail integration
            gmail_integration = data.get("gmail_api_integration", {})
            if gmail_integration.get("status") == "ready":
                print("✅ Gmail integration: ready")
            else:
                print(f"❌ Gmail integration issue: {gmail_integration.get('status')}")
                return False
            
            # Check Groq API
            hybrid_ai = data.get("advanced_hybrid_ai_system", {})
            if hybrid_ai.get("groq_api_key") == "configured":
                print("✅ Groq API: configured")
            else:
                print(f"❌ Groq API issue: {hybrid_ai.get('groq_api_key')}")
                return False
            
            return True
        else:
            print(f"❌ Health endpoint error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def main():
    print("🚀 Targeted Backend Testing for Review Request Issues")
    print("=" * 60)
    
    tests = [
        ("Chat Error Messages", test_chat_error_messages),
        ("Gmail Button Functionality", test_gmail_button_functionality), 
        ("Credentials and Authentication", test_credentials_and_auth),
        ("System Health Check", test_health_check)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 TARGETED TEST RESULTS")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TARGETED TESTS PASSED!")
        print("✅ No issues found with the specific problems mentioned in review")
    else:
        print("⚠️  Some issues found - see details above")
    
    return passed, total

if __name__ == "__main__":
    main()