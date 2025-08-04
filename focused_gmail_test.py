#!/usr/bin/env python3
"""
Focused Gmail Integration Debugging
Testing the specific issues mentioned by the user
"""

import requests
import json
import uuid
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://f5c2c367-6cff-43f3-900f-2f2a9f7fba8e.preview.emergentagent.com/api"

def test_gmail_integration_issues():
    """Test the specific Gmail integration issues mentioned by the user"""
    session_id = str(uuid.uuid4())
    results = []
    
    print("🎯 FOCUSED GMAIL INTEGRATION DEBUGGING")
    print("=" * 60)
    
    # Test 1: Gmail Authentication Flow
    print("\n1️⃣ Testing Gmail Authentication Flow...")
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
        if response.status_code == 200:
            data = response.json()
            auth_url = data.get("auth_url", "")
            client_id = "191070483179-5ldsbkb4fl76at31kbldgj24org21hpl.apps.googleusercontent.com"
            
            if client_id in auth_url:
                print("✅ OAuth URLs generated correctly with new client_id")
                results.append(("Gmail Auth Flow", True, "OAuth URLs generated correctly"))
            else:
                print("❌ Client ID not found in OAuth URL")
                results.append(("Gmail Auth Flow", False, "Client ID not found"))
        else:
            print(f"❌ Gmail auth endpoint failed: HTTP {response.status_code}")
            results.append(("Gmail Auth Flow", False, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ Gmail auth test failed: {e}")
        results.append(("Gmail Auth Flow", False, str(e)))
    
    # Test 2: Gmail Status Check
    print("\n2️⃣ Testing Gmail Status...")
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("credentials_configured"):
                print("✅ Gmail status shows credentials configured")
                results.append(("Gmail Status", True, "Credentials configured"))
            else:
                print("❌ Gmail credentials not configured")
                results.append(("Gmail Status", False, "Credentials not configured"))
        else:
            print(f"❌ Gmail status failed: HTTP {response.status_code}")
            results.append(("Gmail Status", False, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ Gmail status test failed: {e}")
        results.append(("Gmail Status", False, str(e)))
    
    # Test 3: Chat Error Investigation
    print("\n3️⃣ Testing Chat for 'sorry I've encountered an error'...")
    try:
        payload = {"message": "Hello", "session_id": session_id, "user_id": "test_user"}
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "").lower()
            
            if "sorry i've encountered an error" in response_text:
                print("❌ Chat still responding with error message")
                results.append(("Chat Error Fix", False, "Still showing error messages"))
            else:
                print("✅ Chat responding normally without error messages")
                results.append(("Chat Error Fix", True, "No error messages"))
        else:
            print(f"❌ Chat endpoint failed: HTTP {response.status_code}")
            results.append(("Chat Error Fix", False, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        results.append(("Chat Error Fix", False, str(e)))
    
    # Test 4: Gmail Intent Detection
    print("\n4️⃣ Testing Gmail Intent Detection...")
    try:
        payload = {"message": "Check my inbox", "session_id": session_id, "user_id": "test_user"}
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            intent_data = data.get("intent_data", {})
            detected_intent = intent_data.get("intent", "")
            response_text = data.get("response", "")
            
            if "gmail" in detected_intent.lower():
                print(f"✅ Gmail intent detected correctly: {detected_intent}")
                
                # Check if it's asking for authentication
                if "connect gmail" in response_text.lower() or "authentication" in response_text.lower():
                    print("✅ Properly requesting Gmail authentication")
                    results.append(("Gmail Intent Detection", True, f"Intent: {detected_intent}, Auth required"))
                else:
                    print(f"⚠️  Gmail intent detected but response: {response_text[:100]}...")
                    results.append(("Gmail Intent Detection", True, f"Intent detected but unclear response"))
            else:
                print(f"❌ Gmail intent not detected. Got: {detected_intent}")
                results.append(("Gmail Intent Detection", False, f"Wrong intent: {detected_intent}"))
        else:
            print(f"❌ Gmail intent test failed: HTTP {response.status_code}")
            results.append(("Gmail Intent Detection", False, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ Gmail intent test failed: {e}")
        results.append(("Gmail Intent Detection", False, str(e)))
    
    # Test 5: Gmail API Execution
    print("\n5️⃣ Testing Gmail API Execution...")
    try:
        response = requests.get(f"{BACKEND_URL}/gmail/inbox?session_id={session_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("requires_auth"):
                print("✅ Gmail API correctly requires authentication")
                results.append(("Gmail API Execution", True, "Requires auth as expected"))
            elif data.get("success"):
                print("✅ Gmail API executed successfully")
                results.append(("Gmail API Execution", True, "API executed successfully"))
            else:
                print(f"❌ Gmail API returned unexpected response: {data}")
                results.append(("Gmail API Execution", False, "Unexpected response"))
        else:
            print(f"❌ Gmail API failed: HTTP {response.status_code}")
            results.append(("Gmail API Execution", False, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ Gmail API test failed: {e}")
        results.append(("Gmail API Execution", False, str(e)))
    
    # Test 6: Health Endpoint
    print("\n6️⃣ Testing Health Endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            gmail_integration = data.get("gmail_api_integration", {})
            
            if gmail_integration.get("status") == "ready":
                print("✅ Health endpoint shows Gmail integration ready")
                results.append(("Health Check", True, "Gmail integration ready"))
            else:
                print(f"❌ Gmail integration status: {gmail_integration.get('status')}")
                results.append(("Health Check", False, f"Status: {gmail_integration.get('status')}"))
        else:
            print(f"❌ Health endpoint failed: HTTP {response.status_code}")
            results.append(("Health Check", False, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ Health test failed: {e}")
        results.append(("Health Check", False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 GMAIL INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    for test_name, success, details in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {details}")
    
    print(f"\n🎯 RESULTS: {passed}/{len(results)} tests passed ({passed/len(results)*100:.1f}%)")
    
    if failed == 0:
        print("🎉 ALL GMAIL INTEGRATION TESTS PASSED!")
    else:
        print(f"⚠️  {failed} issues found that need attention")
    
    return results

if __name__ == "__main__":
    test_gmail_integration_issues()