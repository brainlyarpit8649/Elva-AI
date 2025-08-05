#!/usr/bin/env python3
"""
MCP Endpoint Testing for Elva AI
Tests the newly integrated MCP endpoints for Puch AI connection requests
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://5ecfe916-5a97-473e-93a6-1974a04632ff.preview.emergentagent.com/api"
MCP_TOKEN = "kumararpit9468"

class MCPEndpointTester:
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    Details: {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def test_mcp_get_connection_with_token_query(self):
        """Test 1: GET /api/mcp?token=kumararpit9468 - Connection test endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["status", "message", "service", "platform", "methods", "integrations"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("MCP GET Connection Test (Query Token)", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check status is ok
                if data.get("status") != "ok":
                    self.log_test("MCP GET Connection Test (Query Token)", False, f"Status not ok: {data.get('status')}", data)
                    return False
                
                # Check service identification
                if "WhatsApp MCP Integration" not in data.get("service", ""):
                    self.log_test("MCP GET Connection Test (Query Token)", False, "Service not properly identified", data)
                    return False
                
                # Check platform
                if data.get("platform") != "whatsapp":
                    self.log_test("MCP GET Connection Test (Query Token)", False, f"Wrong platform: {data.get('platform')}", data)
                    return False
                
                # Check methods
                methods = data.get("methods", [])
                if "GET" not in methods or "POST" not in methods:
                    self.log_test("MCP GET Connection Test (Query Token)", False, f"Missing methods: {methods}", data)
                    return False
                
                # Check integrations
                integrations = data.get("integrations", {})
                expected_integrations = ["gmail", "weather", "general_chat"]
                for integration in expected_integrations:
                    if integrations.get(integration) != "ready":
                        self.log_test("MCP GET Connection Test (Query Token)", False, f"Integration {integration} not ready: {integrations.get(integration)}", data)
                        return False
                
                self.log_test("MCP GET Connection Test (Query Token)", True, "Connection test successful with all required fields")
                return True
            else:
                self.log_test("MCP GET Connection Test (Query Token)", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP GET Connection Test (Query Token)", False, f"Error: {str(e)}")
            return False

    def test_mcp_get_connection_with_auth_header(self):
        """Test 2: GET /api/mcp with Authorization header"""
        try:
            headers = {"Authorization": f"Bearer {MCP_TOKEN}"}
            response = requests.get(f"{BACKEND_URL}/mcp", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check status is ok
                if data.get("status") != "ok":
                    self.log_test("MCP GET Connection Test (Auth Header)", False, f"Status not ok: {data.get('status')}", data)
                    return False
                
                # Check service identification
                if "WhatsApp MCP Integration" not in data.get("service", ""):
                    self.log_test("MCP GET Connection Test (Auth Header)", False, "Service not properly identified", data)
                    return False
                
                self.log_test("MCP GET Connection Test (Auth Header)", True, "Connection test successful with Authorization header")
                return True
            else:
                self.log_test("MCP GET Connection Test (Auth Header)", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP GET Connection Test (Auth Header)", False, f"Error: {str(e)}")
            return False

    def test_mcp_post_empty_payload(self):
        """Test 3: POST /api/mcp?token=kumararpit9468 with empty payload: {}"""
        try:
            response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json={}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["status", "message", "service", "platform"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("MCP POST Empty Payload", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check status is ok
                if data.get("status") != "ok":
                    self.log_test("MCP POST Empty Payload", False, f"Status not ok: {data.get('status')}", data)
                    return False
                
                # Check message indicates connection success
                message = data.get("message", "").lower()
                if "connection successful" not in message:
                    self.log_test("MCP POST Empty Payload", False, f"Message doesn't indicate success: {data.get('message')}", data)
                    return False
                
                self.log_test("MCP POST Empty Payload", True, "Empty payload handled correctly as connection test")
                return True
            else:
                self.log_test("MCP POST Empty Payload", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP POST Empty Payload", False, f"Error: {str(e)}")
            return False

    def test_mcp_post_connection_test(self):
        """Test 4: POST /api/mcp with connection test payload"""
        try:
            payload = {"session_id": "test-connection", "message": "hello"}
            response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["success", "session_id", "message", "intent", "platform"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("MCP POST Connection Test", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check success flag
                if not data.get("success"):
                    self.log_test("MCP POST Connection Test", False, "Success flag not set", data)
                    return False
                
                # Check session_id matches
                if data.get("session_id") != "test-connection":
                    self.log_test("MCP POST Connection Test", False, f"Session ID mismatch: {data.get('session_id')}", data)
                    return False
                
                # Check platform
                if data.get("platform") != "whatsapp":
                    self.log_test("MCP POST Connection Test", False, f"Wrong platform: {data.get('platform')}", data)
                    return False
                
                # Check message response is not empty
                if not data.get("message") or len(data.get("message", "").strip()) == 0:
                    self.log_test("MCP POST Connection Test", False, "Empty message response", data)
                    return False
                
                self.log_test("MCP POST Connection Test", True, f"Connection test processed successfully, response: {data.get('message')[:100]}...")
                return True
            else:
                self.log_test("MCP POST Connection Test", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP POST Connection Test", False, f"Error: {str(e)}")
            return False

    def test_mcp_post_real_message(self):
        """Test 5: POST /api/mcp with real message payload"""
        try:
            payload = {"session_id": "real-test", "message": "What's the weather like today?"}
            response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["success", "session_id", "message", "intent", "platform"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("MCP POST Real Message", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check success flag
                if not data.get("success"):
                    self.log_test("MCP POST Real Message", False, "Success flag not set", data)
                    return False
                
                # Check session_id matches
                if data.get("session_id") != "real-test":
                    self.log_test("MCP POST Real Message", False, f"Session ID mismatch: {data.get('session_id')}", data)
                    return False
                
                # Check intent is detected (should be weather-related or general_chat)
                intent = data.get("intent", "")
                if not intent:
                    self.log_test("MCP POST Real Message", False, "No intent detected", data)
                    return False
                
                # Check message response is meaningful
                message_response = data.get("message", "")
                if not message_response or len(message_response.strip()) < 10:
                    self.log_test("MCP POST Real Message", False, "Response too short or empty", data)
                    return False
                
                # Check for error messages
                if "sorry i've encountered an error" in message_response.lower():
                    self.log_test("MCP POST Real Message", False, "Error message in response", data)
                    return False
                
                self.log_test("MCP POST Real Message", True, f"Real message processed successfully, intent: {intent}, response length: {len(message_response)}")
                return True
            else:
                self.log_test("MCP POST Real Message", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP POST Real Message", False, f"Error: {str(e)}")
            return False

    def test_mcp_post_different_field_names(self):
        """Test 6: POST /api/mcp with different field names (text, query)"""
        test_cases = [
            {"session_id": "test", "text": "hello"},
            {"session_id": "test", "query": "hello"},
            {"session_id": "test", "content": "hello"}
        ]
        
        all_passed = True
        results = []
        
        for i, payload in enumerate(test_cases):
            try:
                response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success") and data.get("message"):
                        field_name = list(payload.keys())[1]  # Get the message field name
                        results.append(f"✅ Field '{field_name}': Processed successfully")
                    else:
                        results.append(f"❌ Field '{field_name}': Failed to process")
                        all_passed = False
                else:
                    field_name = list(payload.keys())[1]
                    results.append(f"❌ Field '{field_name}': HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                field_name = list(payload.keys())[1] if payload else "unknown"
                results.append(f"❌ Field '{field_name}': Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("MCP POST Different Field Names", all_passed, result_summary)
        return all_passed

    def test_mcp_auth_invalid_token(self):
        """Test 7: Invalid token authentication"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp?token=invalid_token", timeout=10)
            
            if response.status_code == 401:
                data = response.json()
                
                # Check error structure
                if "error" in data and "invalid_token" in data.get("error", ""):
                    self.log_test("MCP Auth Invalid Token", True, "Correctly returned 401 for invalid token")
                    return True
                else:
                    self.log_test("MCP Auth Invalid Token", False, "Wrong error structure", data)
                    return False
            else:
                self.log_test("MCP Auth Invalid Token", False, f"Expected 401, got {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP Auth Invalid Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_auth_missing_token(self):
        """Test 8: Missing token authentication"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp", timeout=10)
            
            if response.status_code == 401:
                data = response.json()
                
                # Check error structure
                if "error" in data and ("invalid_token" in data.get("error", "") or "missing" in data.get("message", "").lower()):
                    self.log_test("MCP Auth Missing Token", True, "Correctly returned 401 for missing token")
                    return True
                else:
                    self.log_test("MCP Auth Missing Token", False, "Wrong error structure", data)
                    return False
            else:
                self.log_test("MCP Auth Missing Token", False, f"Expected 401, got {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP Auth Missing Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_post_invalid_payload(self):
        """Test 9: Invalid payload handling"""
        test_cases = [
            {
                "name": "String payload instead of JSON",
                "payload": "invalid string payload",
                "expected_status": 400
            },
            {
                "name": "Array payload instead of object",
                "payload": ["invalid", "array"],
                "expected_status": 400
            }
        ]
        
        all_passed = True
        results = []
        
        for test_case in test_cases:
            try:
                # For string payload, send as text
                if isinstance(test_case["payload"], str):
                    response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", 
                                           data=test_case["payload"], 
                                           headers={"Content-Type": "text/plain"},
                                           timeout=10)
                else:
                    response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", 
                                           json=test_case["payload"], 
                                           timeout=10)
                
                # For MCP endpoint, it should handle various payloads gracefully
                # String payloads might be converted to message format
                if response.status_code in [200, 400]:
                    if response.status_code == 200:
                        # Check if it was handled as a message
                        data = response.json()
                        if data.get("success"):
                            results.append(f"✅ {test_case['name']}: Handled gracefully as message")
                        else:
                            results.append(f"❌ {test_case['name']}: Not handled properly")
                            all_passed = False
                    else:
                        results.append(f"✅ {test_case['name']}: Correctly returned 400")
                else:
                    results.append(f"❌ {test_case['name']}: Unexpected status {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                results.append(f"❌ {test_case['name']}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("MCP POST Invalid Payload", all_passed, result_summary)
        return all_passed

    def test_mcp_health_endpoint(self):
        """Test 10: GET /api/mcp/health"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["status", "service", "version", "platform", "mcp_service", "database", "integrations"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("MCP Health Endpoint", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check status is healthy
                if data.get("status") != "healthy":
                    self.log_test("MCP Health Endpoint", False, f"Status not healthy: {data.get('status')}", data)
                    return False
                
                # Check service identification
                if data.get("service") != "WhatsApp MCP Integration":
                    self.log_test("MCP Health Endpoint", False, f"Wrong service: {data.get('service')}", data)
                    return False
                
                # Check platform
                if data.get("platform") != "whatsapp":
                    self.log_test("MCP Health Endpoint", False, f"Wrong platform: {data.get('platform')}", data)
                    return False
                
                # Check database connection
                if data.get("database") != "connected":
                    self.log_test("MCP Health Endpoint", False, f"Database not connected: {data.get('database')}", data)
                    return False
                
                # Check integrations
                integrations = data.get("integrations", {})
                expected_integrations = ["gmail", "weather", "hybrid_ai"]
                for integration in expected_integrations:
                    if integrations.get(integration) != "ready":
                        self.log_test("MCP Health Endpoint", False, f"Integration {integration} not ready: {integrations.get(integration)}", data)
                        return False
                
                # Check endpoints list
                endpoints = data.get("endpoints", [])
                expected_endpoints = ["POST /api/mcp", "GET /api/mcp/health"]
                for endpoint in expected_endpoints:
                    if endpoint not in endpoints:
                        self.log_test("MCP Health Endpoint", False, f"Missing endpoint: {endpoint}", data)
                        return False
                
                # Check authentication info
                authentication = data.get("authentication", {})
                if not authentication.get("token_configured"):
                    self.log_test("MCP Health Endpoint", False, "Token not configured", data)
                    return False
                
                methods = authentication.get("methods", [])
                if "query_parameter" not in methods or "authorization_header" not in methods:
                    self.log_test("MCP Health Endpoint", False, f"Missing auth methods: {methods}", data)
                    return False
                
                self.log_test("MCP Health Endpoint", True, "Health check passed with all required components")
                return True
            else:
                self.log_test("MCP Health Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("MCP Health Endpoint", False, f"Error: {str(e)}")
            return False

    def test_mcp_session_memory(self):
        """Test 11: Shared MongoDB/Redis session memory"""
        try:
            session_id = f"memory_test_{int(time.time())}"
            
            # Send first message
            payload1 = {"session_id": session_id, "message": "Hi, my name is John"}
            response1 = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json=payload1, timeout=15)
            
            if response1.status_code != 200:
                self.log_test("MCP Session Memory", False, "First message failed", response1.text)
                return False
            
            # Wait a moment for processing
            time.sleep(2)
            
            # Send second message asking about name
            payload2 = {"session_id": session_id, "message": "What is my name?"}
            response2 = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json=payload2, timeout=15)
            
            if response2.status_code != 200:
                self.log_test("MCP Session Memory", False, "Second message failed", response2.text)
                return False
            
            data2 = response2.json()
            response_text = data2.get("message", "").lower()
            
            # Check if the AI remembers the name
            if "john" in response_text:
                self.log_test("MCP Session Memory", True, "Session memory working - AI remembered the name 'John'")
                return True
            else:
                # This might be expected if memory system needs improvement
                self.log_test("MCP Session Memory", False, f"AI did not remember name. Response: {data2.get('message', '')[:200]}...")
                return False
                
        except Exception as e:
            self.log_test("MCP Session Memory", False, f"Error: {str(e)}")
            return False

    def test_mcp_no_422_errors(self):
        """Test 12: Verify no 422 Unprocessable Entity errors occur"""
        test_payloads = [
            {},
            {"session_id": "test"},
            {"message": "hello"},
            {"session_id": "test", "message": "hello"},
            {"session_id": "test", "text": "hello"},
            {"session_id": "test", "query": "hello"},
            {"invalid_field": "test"}
        ]
        
        all_passed = True
        results = []
        
        for i, payload in enumerate(test_payloads):
            try:
                response = requests.post(f"{BACKEND_URL}/mcp?token={MCP_TOKEN}", json=payload, timeout=15)
                
                if response.status_code == 422:
                    results.append(f"❌ Payload {i+1}: Returned 422 (Unprocessable Entity)")
                    all_passed = False
                elif response.status_code in [200, 400, 401]:
                    results.append(f"✅ Payload {i+1}: Returned {response.status_code} (No 422)")
                else:
                    results.append(f"⚠️ Payload {i+1}: Returned {response.status_code} (Unexpected but not 422)")
                    
            except Exception as e:
                results.append(f"❌ Payload {i+1}: Error {str(e)}")
                all_passed = False
        
        result_summary = "\n    ".join(results)
        self.log_test("MCP No 422 Errors", all_passed, result_summary)
        return all_passed

    def run_all_tests(self):
        """Run all MCP endpoint tests"""
        print("🚀 Starting MCP Endpoint Testing for Puch AI Integration...")
        print("=" * 80)
        
        tests = [
            self.test_mcp_get_connection_with_token_query,
            self.test_mcp_get_connection_with_auth_header,
            self.test_mcp_post_empty_payload,
            self.test_mcp_post_connection_test,
            self.test_mcp_post_real_message,
            self.test_mcp_post_different_field_names,
            self.test_mcp_auth_invalid_token,
            self.test_mcp_auth_missing_token,
            self.test_mcp_post_invalid_payload,
            self.test_mcp_health_endpoint,
            self.test_mcp_session_memory,
            self.test_mcp_no_422_errors
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("=" * 80)
        print(f"🎯 MCP ENDPOINT TESTING SUMMARY")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL MCP ENDPOINT TESTS PASSED!")
        else:
            print("⚠️ Some tests failed. Check details above.")
        
        return passed == total

if __name__ == "__main__":
    tester = MCPEndpointTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)