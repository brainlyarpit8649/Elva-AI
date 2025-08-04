#!/usr/bin/env python3
"""
MCP Puch AI Integration Testing
Tests the newly implemented MCP validate endpoint for Puch AI integration
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://395a2c43-f9bd-494c-beb2-dd30fbdf7e7e.preview.emergentagent.com/api"

class MCPPuchAITester:
    def __init__(self):
        self.test_results = []
        self.valid_token = "kumararpit9468"
        self.invalid_token = "wrongtoken"
        
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

    def test_mcp_validate_post_valid_token(self):
        """Test 1: POST /api/mcp/validate with valid Bearer token"""
        try:
            headers = {
                "Authorization": f"Bearer {self.valid_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected response format
                if "number" in data and data["number"] == "919654030351":
                    self.log_test("MCP Validate POST - Valid Token", True, f"Correct response: {data}")
                    return True
                else:
                    self.log_test("MCP Validate POST - Valid Token", False, f"Unexpected response format: {data}")
                    return False
            else:
                self.log_test("MCP Validate POST - Valid Token", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate POST - Valid Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_get_valid_token(self):
        """Test 2: GET /api/mcp/validate with valid Bearer token"""
        try:
            headers = {
                "Authorization": f"Bearer {self.valid_token}"
            }
            
            response = requests.get(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected response format
                if "number" in data and data["number"] == "919654030351":
                    self.log_test("MCP Validate GET - Valid Token", True, f"Correct response: {data}")
                    return True
                else:
                    self.log_test("MCP Validate GET - Valid Token", False, f"Unexpected response format: {data}")
                    return False
            else:
                self.log_test("MCP Validate GET - Valid Token", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate GET - Valid Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_root_endpoint_valid_token(self):
        """Test 3: GET /api/mcp with valid Bearer token"""
        try:
            headers = {
                "Authorization": f"Bearer {self.valid_token}"
            }
            
            response = requests.get(f"{BACKEND_URL}/mcp", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected response format for root MCP endpoint
                expected_fields = ["status", "message"]
                if all(field in data for field in expected_fields):
                    if data.get("status") == "ok" and "MCP" in data.get("message", ""):
                        self.log_test("MCP Root GET - Valid Token", True, f"Correct response: {data}")
                        return True
                    else:
                        self.log_test("MCP Root GET - Valid Token", False, f"Unexpected status/message: {data}")
                        return False
                else:
                    self.log_test("MCP Root GET - Valid Token", False, f"Missing expected fields: {data}")
                    return False
            else:
                self.log_test("MCP Root GET - Valid Token", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Root GET - Valid Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_post_invalid_token(self):
        """Test 4: POST /api/mcp/validate with invalid Bearer token"""
        try:
            headers = {
                "Authorization": f"Bearer {self.invalid_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if response.status_code == 401:
                self.log_test("MCP Validate POST - Invalid Token", True, "Correctly returned 401 for invalid token")
                return True
            else:
                self.log_test("MCP Validate POST - Invalid Token", False, f"Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate POST - Invalid Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_get_invalid_token(self):
        """Test 5: GET /api/mcp/validate with invalid Bearer token"""
        try:
            headers = {
                "Authorization": f"Bearer {self.invalid_token}"
            }
            
            response = requests.get(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if response.status_code == 401:
                self.log_test("MCP Validate GET - Invalid Token", True, "Correctly returned 401 for invalid token")
                return True
            else:
                self.log_test("MCP Validate GET - Invalid Token", False, f"Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate GET - Invalid Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_post_missing_token(self):
        """Test 6: POST /api/mcp/validate with missing Authorization header"""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if response.status_code == 401:
                self.log_test("MCP Validate POST - Missing Token", True, "Correctly returned 401 for missing token")
                return True
            else:
                self.log_test("MCP Validate POST - Missing Token", False, f"Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate POST - Missing Token", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_post_wrong_format(self):
        """Test 7: POST /api/mcp/validate with wrong Authorization format (without Bearer)"""
        try:
            headers = {
                "Authorization": self.valid_token,  # Missing "Bearer " prefix
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if response.status_code == 401:
                self.log_test("MCP Validate POST - Wrong Format", True, "Correctly returned 401 for wrong format")
                return True
            else:
                self.log_test("MCP Validate POST - Wrong Format", False, f"Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate POST - Wrong Format", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_query_parameter(self):
        """Test 8: POST /api/mcp/validate with token as query parameter"""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp/validate?token={self.valid_token}", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected response format
                if "number" in data and data["number"] == "919654030351":
                    self.log_test("MCP Validate POST - Query Parameter", True, f"Token via query parameter works: {data}")
                    return True
                else:
                    self.log_test("MCP Validate POST - Query Parameter", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("MCP Validate POST - Query Parameter", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate POST - Query Parameter", False, f"Error: {str(e)}")
            return False

    def test_mcp_health_endpoint(self):
        """Test 9: MCP Health Check Endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/mcp/health", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected health response fields
                expected_fields = ["status", "service", "platform"]
                if all(field in data for field in expected_fields):
                    if data.get("status") == "healthy" and data.get("platform") == "whatsapp":
                        self.log_test("MCP Health Check", True, f"Health check passed: {data.get('status')}")
                        return True
                    else:
                        self.log_test("MCP Health Check", False, f"Unexpected health status: {data}")
                        return False
                else:
                    self.log_test("MCP Health Check", False, f"Missing expected fields: {data}")
                    return False
            else:
                self.log_test("MCP Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("MCP Health Check", False, f"Error: {str(e)}")
            return False

    def test_puch_ai_integration_readiness(self):
        """Test 10: Integration Readiness Check for Puch AI"""
        try:
            # Test the exact command that Puch AI will use
            # /mcp connect https://elva-mcp-service.onrender.com/api/mcp kumararpit9468
            
            # First test the main MCP endpoint with POST (simulating Puch AI connection)
            headers = {
                "Authorization": f"Bearer {self.valid_token}",
                "Content-Type": "application/json"
            }
            
            test_payload = {
                "session_id": "puch_ai_test_session",
                "message": "Hello, connection test"
            }
            
            response = requests.post(f"{BACKEND_URL}/mcp", json=test_payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response indicates successful connection
                if data.get("success") and "session_id" in data:
                    self.log_test("Puch AI Integration Readiness", True, f"MCP service ready for Puch AI connection: {data.get('message', '')}")
                    return True
                else:
                    self.log_test("Puch AI Integration Readiness", False, f"Unexpected response structure: {data}")
                    return False
            else:
                self.log_test("Puch AI Integration Readiness", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Puch AI Integration Readiness", False, f"Error: {str(e)}")
            return False

    def test_mcp_validate_response_format(self):
        """Test 11: Validate Response Format Consistency"""
        try:
            # Test both GET and POST endpoints return the same format
            headers = {
                "Authorization": f"Bearer {self.valid_token}",
                "Content-Type": "application/json"
            }
            
            # Test POST
            post_response = requests.post(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            # Test GET
            get_response = requests.get(f"{BACKEND_URL}/mcp/validate", headers=headers, timeout=30)
            
            if post_response.status_code == 200 and get_response.status_code == 200:
                post_data = post_response.json()
                get_data = get_response.json()
                
                # Both should return the same format
                if post_data == get_data and post_data.get("number") == "919654030351":
                    self.log_test("MCP Validate Response Format", True, f"Both GET and POST return consistent format: {post_data}")
                    return True
                else:
                    self.log_test("MCP Validate Response Format", False, f"Inconsistent responses - POST: {post_data}, GET: {get_data}")
                    return False
            else:
                self.log_test("MCP Validate Response Format", False, f"HTTP errors - POST: {post_response.status_code}, GET: {get_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("MCP Validate Response Format", False, f"Error: {str(e)}")
            return False

    def test_mcp_endpoint_availability(self):
        """Test 12: Check if MCP endpoints are available in main server"""
        try:
            # Test if the validate endpoints are actually available
            # This test checks if the endpoints exist (even with wrong auth)
            
            endpoints_to_test = [
                ("POST", "/mcp/validate"),
                ("GET", "/mcp/validate"),
                ("GET", "/mcp"),
                ("GET", "/mcp/health")
            ]
            
            results = []
            all_available = True
            
            for method, endpoint in endpoints_to_test:
                try:
                    if method == "POST":
                        response = requests.post(f"{BACKEND_URL}{endpoint}", timeout=30)
                    else:
                        response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=30)
                    
                    # We expect 401 (unauthorized) or 200 (success), not 404 (not found)
                    if response.status_code in [200, 401, 400]:
                        results.append(f"✅ {method} {endpoint}: Available (HTTP {response.status_code})")
                    elif response.status_code == 404:
                        results.append(f"❌ {method} {endpoint}: Not Found (HTTP 404)")
                        all_available = False
                    else:
                        results.append(f"⚠️ {method} {endpoint}: Unexpected status (HTTP {response.status_code})")
                        
                except Exception as e:
                    results.append(f"❌ {method} {endpoint}: Error - {str(e)}")
                    all_available = False
            
            result_summary = "\n    ".join(results)
            self.log_test("MCP Endpoint Availability", all_available, result_summary)
            return all_available
                
        except Exception as e:
            self.log_test("MCP Endpoint Availability", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all MCP Puch AI integration tests"""
        print("🚀 Starting MCP Puch AI Integration Tests...")
        print("=" * 60)
        
        tests = [
            self.test_mcp_endpoint_availability,
            self.test_mcp_validate_post_valid_token,
            self.test_mcp_validate_get_valid_token,
            self.test_mcp_root_endpoint_valid_token,
            self.test_mcp_validate_post_invalid_token,
            self.test_mcp_validate_get_invalid_token,
            self.test_mcp_validate_post_missing_token,
            self.test_mcp_validate_post_wrong_format,
            self.test_mcp_validate_query_parameter,
            self.test_mcp_health_endpoint,
            self.test_puch_ai_integration_readiness,
            self.test_mcp_validate_response_format
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ FAIL - {test.__name__}: Unexpected error - {str(e)}")
                failed += 1
        
        print("=" * 60)
        print(f"🎯 MCP PUCH AI INTEGRATION TEST RESULTS:")
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📊 SUCCESS RATE: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! MCP service is ready for Puch AI integration!")
            print("🔗 Puch AI can connect using: /mcp connect https://395a2c43-f9bd-494c-beb2-dd30fbdf7e7e.preview.emergentagent.com/api/mcp kumararpit9468")
        else:
            print("⚠️ Some tests failed. Please check the implementation.")
        
        return failed == 0

if __name__ == "__main__":
    tester = MCPPuchAITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)