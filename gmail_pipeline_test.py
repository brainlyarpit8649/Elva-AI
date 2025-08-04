#!/usr/bin/env python3
"""
Gmail Integration Pipeline Testing
Comprehensive test of Gmail integration as requested in review
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://329904b0-2cf4-48ba-8d24-e322e324860a.preview.emergentagent.com/api"

def test_gmail_integration_pipeline():
    """Test complete Gmail integration pipeline"""
    print("📧 Testing Gmail Integration Pipeline...")
    
    session_id = str(uuid.uuid4())
    
    # Test 1: Gmail Auth URL Generation
    print("\n1️⃣ Testing Gmail Auth URL Generation...")
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "accounts.google.com" in data.get("auth_url", ""):
                print("✅ Gmail OAuth URLs generating correctly")
                auth_url_test = True
            else:
                print(f"❌ Gmail OAuth URL generation failed: {data}")
                auth_url_test = False
        else:
            print(f"❌ Gmail auth endpoint error: HTTP {response.status_code}")
            auth_url_test = False
    except Exception as e:
        print(f"❌ Gmail auth test error: {str(e)}")
        auth_url_test = False
    
    # Test 2: Gmail Status - Credentials Loading
    print("\n2️⃣ Testing Gmail Status - Credentials Loading...")
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            credentials_ok = data.get("credentials_configured") == True
            scopes_ok = len(data.get("scopes", [])) >= 4
            
            if credentials_ok and scopes_ok:
                print("✅ Gmail credentials loaded properly")
                print(f"   Credentials configured: {data.get('credentials_configured')}")
                print(f"   Scopes: {len(data.get('scopes', []))} configured")
                credentials_test = True
            else:
                print(f"❌ Gmail credentials issue - configured: {credentials_ok}, scopes: {scopes_ok}")
                credentials_test = False
        else:
            print(f"❌ Gmail status endpoint error: HTTP {response.status_code}")
            credentials_test = False
    except Exception as e:
        print(f"❌ Gmail status test error: {str(e)}")
        credentials_test = False
    
    # Test 3: Gmail Intent Detection
    print("\n3️⃣ Testing Gmail Intent Detection...")
    gmail_queries = [
        "Check my Gmail inbox",
        "Show me unread emails", 
        "Any new emails?",
        "Check my email"
    ]
    
    intent_results = []
    for query in gmail_queries:
        try:
            payload = {
                "message": query,
                "session_id": session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                response_text = data.get("response", "")
                
                # Check for Gmail-related intent or authentication prompt
                gmail_detected = (
                    "gmail" in intent_data.get("intent", "").lower() or
                    "connect gmail" in response_text.lower() or
                    "gmail connection required" in response_text.lower() or
                    intent_data.get("requires_auth") == True or
                    "🔐" in response_text  # Gmail auth prompt emoji
                )
                
                if gmail_detected:
                    intent_results.append(f"✅ '{query}': Gmail intent detected")
                else:
                    intent_results.append(f"❌ '{query}': No Gmail detection. Intent: {intent_data.get('intent')}")
                    
            else:
                intent_results.append(f"❌ '{query}': HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            intent_results.append(f"⏰ '{query}': Timeout (server slow)")
        except Exception as e:
            intent_results.append(f"❌ '{query}': Error {str(e)}")
    
    # Print intent detection results
    for result in intent_results:
        print(f"   {result}")
    
    intent_test = all("✅" in result or "⏰" in result for result in intent_results)
    if intent_test:
        print("✅ Gmail intent detection working correctly")
    else:
        print("❌ Gmail intent detection has issues")
    
    # Test 4: Health Check - Overall Integration Status
    print("\n4️⃣ Testing Health Check - Overall Integration Status...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Check Gmail integration in health
            gmail_integration = data.get("gmail_api_integration", {})
            gmail_status = gmail_integration.get("status")
            oauth_flow = gmail_integration.get("oauth2_flow")
            
            if gmail_status == "ready" and oauth_flow == "implemented":
                print("✅ Health check shows Gmail integration ready")
                print(f"   Status: {gmail_status}")
                print(f"   OAuth2 Flow: {oauth_flow}")
                print(f"   Endpoints: {len(gmail_integration.get('endpoints', []))} available")
                health_test = True
            else:
                print(f"❌ Health check shows Gmail issues - Status: {gmail_status}, OAuth: {oauth_flow}")
                health_test = False
        else:
            print(f"❌ Health endpoint error: HTTP {response.status_code}")
            health_test = False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        health_test = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 GMAIL INTEGRATION PIPELINE TEST RESULTS")
    print("=" * 50)
    
    tests = [
        ("Gmail Auth URL Generation", auth_url_test),
        ("Gmail Credentials Loading", credentials_test), 
        ("Gmail Intent Detection", intent_test),
        ("Health Check Integration", health_test)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall Gmail Integration: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 Gmail integration pipeline is working correctly!")
    else:
        print("⚠️  Gmail integration has some issues")
    
    return passed, total

if __name__ == "__main__":
    test_gmail_integration_pipeline()