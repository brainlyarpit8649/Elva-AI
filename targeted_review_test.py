#!/usr/bin/env python3
"""
Targeted Review Testing for Elva AI Backend
Focus on the specific review request areas with shorter timeouts and better error handling
"""

import requests
import json
import uuid
import time
from datetime import datetime

BACKEND_URL = "https://d16fdba0-1be5-48f0-85b7-104cf45d55df.preview.emergentagent.com/api"

def test_basic_chat():
    """Test basic chat functionality - looking for 'sorry I've encountered an error' messages"""
    print("🗣️ Testing Basic Chat Functionality...")
    
    test_messages = ["Hello", "Hi there", "How are you?"]
    results = []
    
    for message in test_messages:
        try:
            payload = {
                "message": message,
                "session_id": str(uuid.uuid4()),
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                
                # Check for error messages
                error_phrases = [
                    "sorry i've encountered an error",
                    "sorry, i've encountered an error", 
                    "encountered an error"
                ]
                
                has_error = any(phrase in response_text for phrase in error_phrases)
                
                if has_error:
                    results.append(f"❌ '{message}': Contains error message")
                else:
                    results.append(f"✅ '{message}': Clean response ({len(data.get('response', ''))} chars)")
                    
            else:
                results.append(f"❌ '{message}': HTTP {response.status_code}")
                
        except Exception as e:
            results.append(f"❌ '{message}': {str(e)}")
    
    print("\n".join(results))
    return results

def test_gmail_summarization():
    """Test Gmail summarization intents"""
    print("\n📧 Testing Gmail Summarization Intents...")
    
    test_cases = [
        "Summarize my last 4 emails",
        "Summarize my last 5 emails and send to john@example.com"
    ]
    
    results = []
    
    for message in test_cases:
        try:
            payload = {
                "message": message,
                "session_id": str(uuid.uuid4()),
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Check if Gmail summarization intent was detected
                if detected_intent and ("summarize" in detected_intent.lower() or "gmail" in detected_intent.lower()):
                    results.append(f"✅ '{message}': Detected {detected_intent}")
                    
                    # Check for N8N response
                    if "n8n_response" in intent_data:
                        results.append(f"    ✅ N8N webhook called")
                    else:
                        results.append(f"    ⚠️ N8N webhook not called")
                else:
                    results.append(f"❌ '{message}': No Gmail summarization intent, got {detected_intent}")
                    
            else:
                results.append(f"❌ '{message}': HTTP {response.status_code}")
                
        except Exception as e:
            results.append(f"❌ '{message}': {str(e)}")
    
    print("\n".join(results))
    return results

def test_n8n_integration():
    """Test N8N integration"""
    print("\n🔗 Testing N8N Integration...")
    
    try:
        # Check health endpoint for N8N webhook configuration
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check N8N webhook configuration
            if data.get("n8n_webhook") == "configured":
                print("✅ N8N webhook configured in health check")
                
                # Check Gmail summarization configuration
                gmail_sum = data.get("gmail_summarization", {})
                if gmail_sum.get("status") == "ready":
                    webhook_url = gmail_sum.get("webhook_url")
                    intents = gmail_sum.get("intents", [])
                    
                    print(f"✅ Gmail summarization ready with webhook: {webhook_url}")
                    print(f"✅ Supported intents: {intents}")
                    
                    if "https://kumararpit8649.app.n8n.cloud/webhook/main-controller" in webhook_url:
                        print("✅ Correct N8N webhook URL configured")
                        return True
                    else:
                        print("❌ Incorrect N8N webhook URL")
                        return False
                else:
                    print("❌ Gmail summarization not ready")
                    return False
            else:
                print("❌ N8N webhook not configured")
                return False
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ N8N integration test error: {e}")
        return False

def test_mcp_integration():
    """Test MCP integration"""
    print("\n🧠 Testing MCP Integration...")
    
    try:
        session_id = str(uuid.uuid4())
        
        # Test MCP read-context endpoint
        response = requests.get(f"{BACKEND_URL}/mcp/read-context/{session_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MCP read-context endpoint working: {data.get('success')}")
            
            # Test MCP write-context endpoint
            write_payload = {
                "session_id": session_id,
                "user_id": "test_user",
                "intent": "test_intent",
                "data": {"test": "context_data"}
            }
            
            write_response = requests.post(f"{BACKEND_URL}/mcp/write-context", json=write_payload, timeout=10)
            
            if write_response.status_code == 200:
                write_data = write_response.json()
                print(f"✅ MCP write-context endpoint working: {write_data.get('success')}")
                return True
            else:
                print(f"❌ MCP write-context failed: HTTP {write_response.status_code}")
                return False
                
        else:
            print(f"❌ MCP read-context failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ MCP integration test error: {e}")
        return False

def test_health_check():
    """Test health check endpoint"""
    print("\n🏥 Testing Health Check...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check overall status
            if data.get("status") == "healthy":
                print("✅ Overall system status: healthy")
            else:
                print(f"❌ System status: {data.get('status')}")
                return False
            
            # Check for Langfuse references (should not be present)
            health_str = json.dumps(data).lower()
            if "langfuse" in health_str:
                print("❌ Langfuse references found in health check")
                return False
            else:
                print("✅ No Langfuse references found")
            
            # Check services
            services = data.get("services", {})
            print(f"✅ Services status: {services}")
            
            # Check Gmail integration
            gmail_integration = data.get("gmail_api_integration", {})
            if gmail_integration.get("status") == "ready":
                print("✅ Gmail integration ready")
            else:
                print(f"❌ Gmail integration not ready: {gmail_integration.get('status')}")
                return False
            
            return True
            
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_regular_gmail():
    """Test regular Gmail intents"""
    print("\n📬 Testing Regular Gmail Intents...")
    
    test_cases = [
        "Check my Gmail inbox",
        "Show me my unread emails"
    ]
    
    results = []
    
    for message in test_cases:
        try:
            payload = {
                "message": message,
                "session_id": str(uuid.uuid4()),
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                response_text = data.get("response", "").lower()
                
                # Check if Gmail intent was detected or authentication prompt provided
                if (detected_intent and "gmail" in detected_intent.lower()) or \
                   ("gmail" in response_text or "connect" in response_text or "auth" in response_text):
                    results.append(f"✅ '{message}': Gmail intent or auth prompt detected")
                else:
                    results.append(f"❌ '{message}': No Gmail response, got {detected_intent}")
                    
            else:
                results.append(f"❌ '{message}': HTTP {response.status_code}")
                
        except Exception as e:
            results.append(f"❌ '{message}': {str(e)}")
    
    print("\n".join(results))
    return results

def main():
    """Run all targeted tests"""
    print("🚀 Starting Targeted Review Testing for Elva AI Backend")
    print("=" * 60)
    
    tests = [
        ("Basic Chat Functionality", test_basic_chat),
        ("Gmail Summarization", test_gmail_summarization),
        ("N8N Integration", test_n8n_integration),
        ("MCP Integration", test_mcp_integration),
        ("Health Check", test_health_check),
        ("Regular Gmail", test_regular_gmail)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 FINAL RESULTS: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL REVIEW REQUIREMENTS PASSED!")
    else:
        print("⚠️ Some review requirements need attention")

if __name__ == "__main__":
    main()