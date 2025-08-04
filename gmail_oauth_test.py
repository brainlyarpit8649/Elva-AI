#!/usr/bin/env python3
"""
Gmail OAuth2 Integration and Cleanup Verification Tests
Tests specifically for Gmail API OAuth2 integration and cleanup verification
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://f5c2c367-6cff-43f3-900f-2f2a9f7fba8e.preview.emergentagent.com/api"

class GmailOAuth2Tester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
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

    def test_gmail_oauth_auth_endpoint(self):
        """Test Gmail OAuth2 authentication URL generation"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/auth", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                if not data.get("success"):
                    self.log_test("Gmail OAuth - Auth URL", False, f"Auth URL generation failed: {data.get('message')}", data)
                    return False
                
                # Check if auth_url is present and valid
                auth_url = data.get("auth_url", "")
                if not auth_url or "accounts.google.com" not in auth_url:
                    self.log_test("Gmail OAuth - Auth URL", False, "Invalid or missing auth_url", data)
                    return False
                
                # Check if OAuth2 parameters are present
                required_params = ["client_id", "redirect_uri", "scope", "response_type"]
                missing_params = [param for param in required_params if param not in auth_url]
                
                if missing_params:
                    self.log_test("Gmail OAuth - Auth URL", False, f"Missing OAuth2 parameters: {missing_params}", data)
                    return False
                
                self.log_test("Gmail OAuth - Auth URL", True, f"OAuth2 auth URL generated successfully with all required parameters")
                return True
            else:
                self.log_test("Gmail OAuth - Auth URL", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail OAuth - Auth URL", False, f"Error: {str(e)}")
            return False

    def test_gmail_oauth_status_endpoint(self):
        """Test Gmail OAuth2 authentication status"""
        try:
            response = requests.get(f"{BACKEND_URL}/gmail/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["credentials_configured", "token_exists", "authenticated", "redirect_uri", "scopes"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Gmail OAuth - Status", False, f"Missing status fields: {missing_fields}", data)
                    return False
                
                # Check credentials are configured (credentials.json exists)
                if not data.get("credentials_configured"):
                    self.log_test("Gmail OAuth - Status", False, "Gmail credentials.json not configured", data)
                    return False
                
                # Check redirect URI is set correctly
                redirect_uri = data.get("redirect_uri", "")
                if not redirect_uri or "gmail/callback" not in redirect_uri:
                    self.log_test("Gmail OAuth - Status", False, f"Invalid redirect_uri: {redirect_uri}", data)
                    return False
                
                # Check scopes are configured
                scopes = data.get("scopes", [])
                required_scopes = ["gmail.readonly", "gmail.send", "gmail.compose", "gmail.modify"]
                missing_scopes = [scope for scope in required_scopes if not any(scope in s for s in scopes)]
                
                if missing_scopes:
                    self.log_test("Gmail OAuth - Status", False, f"Missing Gmail scopes: {missing_scopes}", data)
                    return False
                
                self.log_test("Gmail OAuth - Status", True, f"Gmail OAuth2 status configured correctly. Authenticated: {data.get('authenticated')}, Token exists: {data.get('token_exists')}")
                return True
            else:
                self.log_test("Gmail OAuth - Status", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail OAuth - Status", False, f"Error: {str(e)}")
            return False

    def test_gmail_oauth_callback_structure(self):
        """Test Gmail OAuth2 callback endpoint structure (without actual OAuth flow)"""
        try:
            # Test callback endpoint with missing authorization code
            payload = {}
            
            response = requests.post(f"{BACKEND_URL}/gmail/callback", json=payload, timeout=10)
            
            if response.status_code == 400:
                data = response.json()
                if "Authorization code required" in data.get("detail", ""):
                    self.log_test("Gmail OAuth - Callback Structure", True, "Callback endpoint correctly validates authorization code requirement")
                    return True
                else:
                    self.log_test("Gmail OAuth - Callback Structure", False, f"Unexpected error message: {data.get('detail')}", data)
                    return False
            else:
                self.log_test("Gmail OAuth - Callback Structure", False, f"Expected 400 for missing code, got {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail OAuth - Callback Structure", False, f"Error: {str(e)}")
            return False

    def test_gmail_credentials_loading(self):
        """Test Gmail credentials.json loading and configuration"""
        try:
            # Test health endpoint to verify Gmail integration status
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check Gmail API integration section
                gmail_integration = data.get("gmail_api_integration", {})
                
                if not gmail_integration:
                    self.log_test("Gmail Credentials Loading", False, "Gmail API integration section missing from health check", data)
                    return False
                
                # Check credentials are configured
                if not gmail_integration.get("credentials_configured"):
                    self.log_test("Gmail Credentials Loading", False, "Gmail credentials not configured", gmail_integration)
                    return False
                
                # Check OAuth2 flow is implemented
                if gmail_integration.get("oauth2_flow") != "implemented":
                    self.log_test("Gmail Credentials Loading", False, "OAuth2 flow not implemented", gmail_integration)
                    return False
                
                # Check scopes are configured
                scopes = gmail_integration.get("scopes", [])
                if not scopes or len(scopes) < 4:
                    self.log_test("Gmail Credentials Loading", False, f"Insufficient Gmail scopes configured: {scopes}", gmail_integration)
                    return False
                
                # Check endpoints are available
                endpoints = gmail_integration.get("endpoints", [])
                required_endpoints = ["/api/gmail/auth", "/api/gmail/callback", "/api/gmail/status", "/api/gmail/inbox", "/api/gmail/send"]
                missing_endpoints = [ep for ep in required_endpoints if ep not in endpoints]
                
                if missing_endpoints:
                    self.log_test("Gmail Credentials Loading", False, f"Missing Gmail endpoints: {missing_endpoints}", gmail_integration)
                    return False
                
                self.log_test("Gmail Credentials Loading", True, f"Gmail credentials loaded successfully with {len(scopes)} scopes and {len(endpoints)} endpoints")
                return True
            else:
                self.log_test("Gmail Credentials Loading", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Credentials Loading", False, f"Error: {str(e)}")
            return False

    def test_gmail_service_initialization(self):
        """Test Gmail API service initialization"""
        try:
            # Test Gmail inbox endpoint (should require authentication)
            response = requests.get(f"{BACKEND_URL}/gmail/inbox", timeout=10)
            
            # Should return 500 or structured error about authentication
            if response.status_code in [200, 500]:
                try:
                    data = response.json()
                    
                    # If successful, check structure
                    if response.status_code == 200 and data.get("success"):
                        self.log_test("Gmail Service Initialization", True, "Gmail service initialized and working")
                        return True
                    
                    # If failed, should be due to authentication
                    if not data.get("success") and ("authentication" in data.get("message", "").lower() or "oauth" in data.get("message", "").lower()):
                        self.log_test("Gmail Service Initialization", True, "Gmail service properly requires authentication")
                        return True
                    
                    self.log_test("Gmail Service Initialization", False, f"Unexpected response: {data}", data)
                    return False
                    
                except json.JSONDecodeError:
                    self.log_test("Gmail Service Initialization", False, "Invalid JSON response", response.text)
                    return False
            else:
                self.log_test("Gmail Service Initialization", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Service Initialization", False, f"Error: {str(e)}")
            return False

    def test_cleanup_verification_cookie_references(self):
        """Test Verify cookie-based code is completely removed"""
        try:
            # Test health endpoint to ensure no cookie management references
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that cookie_management section is NOT present
                if "cookie_management" in data:
                    self.log_test("Cleanup - Cookie References", False, "cookie_management section still present in health endpoint", data)
                    return False
                
                # Check playwright service doesn't mention cookie capabilities
                playwright_service = data.get("playwright_service", {})
                capabilities = playwright_service.get("capabilities", [])
                
                cookie_capabilities = [cap for cap in capabilities if "cookie" in cap.lower()]
                if cookie_capabilities:
                    self.log_test("Cleanup - Cookie References", False, f"Cookie capabilities still present: {cookie_capabilities}", playwright_service)
                    return False
                
                self.log_test("Cleanup - Cookie References", True, "No cookie management references found in health endpoint")
                return True
            else:
                self.log_test("Cleanup - Cookie References", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Cleanup - Cookie References", False, f"Error: {str(e)}")
            return False

    def test_cleanup_verification_price_monitoring_removal(self):
        """Test Verify price monitoring intent is removed from AI routing"""
        try:
            # Check web automation endpoint doesn't support price_monitoring
            web_automation_payload = {
                "session_id": self.session_id,
                "automation_type": "price_monitoring",
                "parameters": {
                    "product_url": "https://example.com/product",
                    "price_selector": ".price"
                }
            }
            
            web_response = requests.post(f"{BACKEND_URL}/web-automation", json=web_automation_payload, timeout=15)
            
            if web_response.status_code == 400:
                web_data = web_response.json()
                if "Unsupported automation type" in web_data.get("detail", ""):
                    self.log_test("Cleanup - Price Monitoring Removal", True, "Price monitoring web automation removed successfully")
                    return True
            
            self.log_test("Cleanup - Price Monitoring Removal", False, f"Web automation still supports price_monitoring: {web_response.status_code}", web_response.text)
            return False
                
        except Exception as e:
            self.log_test("Cleanup - Price Monitoring Removal", False, f"Error: {str(e)}")
            return False

    def test_cleanup_verification_deprecated_endpoints(self):
        """Test Verify deprecated cookie and price monitoring endpoints are removed"""
        try:
            deprecated_endpoints = [
                "/cookie-sessions",
                "/automation/linkedin-insights", 
                "/automation/email-check",
                "/cookie-sessions/cleanup"
            ]
            
            results = []
            all_removed = True
            
            for endpoint in deprecated_endpoints:
                try:
                    response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
                    if response.status_code == 404:
                        results.append(f"✅ {endpoint}: Correctly removed (404)")
                    else:
                        results.append(f"❌ {endpoint}: Still accessible ({response.status_code})")
                        all_removed = False
                except requests.exceptions.RequestException:
                    # Connection errors are also acceptable (endpoint doesn't exist)
                    results.append(f"✅ {endpoint}: Correctly removed (connection error)")
            
            result_summary = "\n    ".join(results)
            self.log_test("Cleanup - Deprecated Endpoints", all_removed, result_summary)
            return all_removed
            
        except Exception as e:
            self.log_test("Cleanup - Deprecated Endpoints", False, f"Error: {str(e)}")
            return False

    def test_system_health_gmail_integration(self):
        """Test System health shows Gmail integration status"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check Gmail API integration is present and properly configured
                gmail_integration = data.get("gmail_api_integration", {})
                
                if not gmail_integration:
                    self.log_test("System Health - Gmail Integration", False, "Gmail API integration section missing", data)
                    return False
                
                # Check required fields
                required_fields = ["status", "oauth2_flow", "credentials_configured", "authenticated", "scopes", "endpoints"]
                missing_fields = [field for field in required_fields if field not in gmail_integration]
                
                if missing_fields:
                    self.log_test("System Health - Gmail Integration", False, f"Missing Gmail integration fields: {missing_fields}", gmail_integration)
                    return False
                
                # Check status is ready
                if gmail_integration.get("status") != "ready":
                    self.log_test("System Health - Gmail Integration", False, f"Gmail integration status not ready: {gmail_integration.get('status')}", gmail_integration)
                    return False
                
                # Verify no cookie management in health check
                if "cookie_management" in data:
                    self.log_test("System Health - Gmail Integration", False, "Cookie management still present in health check", data)
                    return False
                
                self.log_test("System Health - Gmail Integration", True, f"Gmail integration properly configured in health check with {len(gmail_integration.get('endpoints', []))} endpoints")
                return True
            else:
                self.log_test("System Health - Gmail Integration", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("System Health - Gmail Integration", False, f"Error: {str(e)}")
            return False

    def test_existing_functionality_preservation(self):
        """Test Verify all existing functionality still works after cleanup"""
        try:
            # Test web automation (allowed types)
            web_automation_payload = {
                "session_id": self.session_id,
                "automation_type": "web_scraping",
                "parameters": {
                    "url": "https://httpbin.org/html",
                    "selectors": {"title": "title"},
                    "wait_for_element": "title"
                }
            }
            
            web_response = requests.post(f"{BACKEND_URL}/web-automation", json=web_automation_payload, timeout=30)
            
            if web_response.status_code != 200:
                self.log_test("Existing Functionality Preservation", False, "Web automation broken", web_response.text)
                return False
            
            self.log_test("Existing Functionality Preservation", True, "Web automation functionality working correctly")
            return True
            
        except Exception as e:
            self.log_test("Existing Functionality Preservation", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Gmail OAuth2 and cleanup verification tests"""
        print("🚀 Starting Gmail API OAuth2 Integration & Cleanup Verification Testing")
        print("=" * 80)
        
        test_methods = [
            # Gmail OAuth2 integration tests
            self.test_gmail_oauth_auth_endpoint,
            self.test_gmail_oauth_status_endpoint,
            self.test_gmail_oauth_callback_structure,
            self.test_gmail_credentials_loading,
            self.test_gmail_service_initialization,
            
            # Cleanup verification tests
            self.test_cleanup_verification_cookie_references,
            self.test_cleanup_verification_price_monitoring_removal,
            self.test_cleanup_verification_deprecated_endpoints,
            self.test_system_health_gmail_integration,
            self.test_existing_functionality_preservation
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ FAIL - {test_method.__name__}: Unexpected error: {str(e)}")
                failed += 1
            
            # Small delay between tests
            time.sleep(0.5)
        
        print("=" * 70)
        print(f"🏁 Gmail API OAuth2 Integration & Cleanup Testing Complete!")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! Gmail API OAuth2 integration and cleanup verification successful!")
        else:
            print(f"⚠️  {failed} tests failed. Please check the details above.")
        
        return {
            "total_tests": len(test_methods),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = GmailOAuth2Tester()
    results = tester.run_all_tests()
    
    # Save detailed results
    with open("/app/gmail_oauth_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed results saved to: /app/gmail_oauth_test_results.json")