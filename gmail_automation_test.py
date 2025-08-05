#!/usr/bin/env python3
"""
Gmail Automation Testing for brainlyarpit8649@gmail.com
Tests the specific Gmail automation functionality requested in the review
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://ab5f30cf-28b7-448e-92ee-50cd74c372d1.preview.emergentagent.com/api"

class GmailAutomationTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data = None):
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

    def test_cookie_detection_for_gmail_user(self):
        """Test 1: Cookie detection for brainlyarpit8649@gmail.com"""
        try:
            response = requests.get(f"{BACKEND_URL}/cookie-sessions/gmail/brainlyarpit8649@gmail.com/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["has_valid_cookies", "cookie_count", "message"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Cookie Detection - Gmail User", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                has_valid_cookies = data.get("has_valid_cookies")
                cookie_count = data.get("cookie_count", 0)
                message = data.get("message", "")
                
                if has_valid_cookies:
                    self.log_test("Cookie Detection - Gmail User", True, f"Valid Gmail cookies found for brainlyarpit8649@gmail.com. Cookie count: {cookie_count}")
                    return True
                else:
                    self.log_test("Cookie Detection - Gmail User", False, f"No valid Gmail cookies found for brainlyarpit8649@gmail.com. Message: {message}")
                    return False
            else:
                self.log_test("Cookie Detection - Gmail User", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Cookie Detection - Gmail User", False, f"Error: {str(e)}")
            return False

    def test_gmail_automation_check_inbox_brainlyarpit(self):
        """Test 2: Gmail automation - Check inbox for brainlyarpit8649@gmail.com"""
        try:
            payload = {
                "user_email": "brainlyarpit8649@gmail.com",
                "provider": "gmail",
                "action": "check_inbox"
            }
            
            response = requests.post(f"{BACKEND_URL}/automation/email-check", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["success", "message"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                success = data.get("success")
                message = data.get("message", "")
                
                if success:
                    # Check if actual email data is returned
                    email_data = data.get("data", {})
                    execution_time = data.get("execution_time", 0)
                    
                    if not email_data:
                        self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, "No email data returned despite success=True", data)
                        return False
                    
                    # Check if execution time is reasonable (under 30s as requested)
                    if execution_time > 30:
                        self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, f"Execution time too long: {execution_time}s (should be under 30s)", data)
                        return False
                    
                    self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", True, f"Successfully retrieved Gmail inbox data. Execution time: {execution_time:.2f}s, Data keys: {list(email_data.keys())}")
                    return True
                else:
                    # Check if it's a cookie issue
                    if "cookies" in message.lower() or "login" in message.lower():
                        self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, f"Cookie authentication failed: {message}", data)
                        return False
                    else:
                        self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, f"Gmail automation failed: {message}", data)
                        return False
            else:
                self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Automation - Check Inbox (brainlyarpit8649)", False, f"Error: {str(e)}")
            return False

    def test_gmail_automation_check_unread_brainlyarpit(self):
        """Test 3: Gmail automation - Check unread emails for brainlyarpit8649@gmail.com"""
        try:
            payload = {
                "user_email": "brainlyarpit8649@gmail.com",
                "provider": "gmail",
                "action": "check_unread"
            }
            
            response = requests.post(f"{BACKEND_URL}/automation/email-check", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["success", "message"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                success = data.get("success")
                message = data.get("message", "")
                
                if success:
                    # Check if actual email data is returned
                    email_data = data.get("data", {})
                    execution_time = data.get("execution_time", 0)
                    
                    if not email_data:
                        self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, "No email data returned despite success=True", data)
                        return False
                    
                    # Check if execution time is reasonable (under 30s as requested)
                    if execution_time > 30:
                        self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, f"Execution time too long: {execution_time}s (should be under 30s)", data)
                        return False
                    
                    self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", True, f"Successfully retrieved Gmail unread data. Execution time: {execution_time:.2f}s, Data keys: {list(email_data.keys())}")
                    return True
                else:
                    # Check if it's a cookie issue
                    if "cookies" in message.lower() or "login" in message.lower():
                        self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, f"Cookie authentication failed: {message}", data)
                        return False
                    else:
                        self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, f"Gmail automation failed: {message}", data)
                        return False
            else:
                self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Automation - Check Unread (brainlyarpit8649)", False, f"Error: {str(e)}")
            return False

    def test_gmail_chat_interface_check_inbox(self):
        """Test 4: Gmail automation via chat interface - Check inbox"""
        try:
            payload = {
                "message": "Check my Gmail inbox for brainlyarpit8649@gmail.com",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if intent was detected correctly
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Should detect email automation or similar intent
                if detected_intent not in ["email_automation", "check_gmail_inbox", "gmail_check"]:
                    self.log_test("Gmail Chat Interface - Check Inbox", False, f"Wrong intent detected: {detected_intent}. Expected email automation related intent.", data)
                    return False
                
                # Check if user email was extracted
                user_email = intent_data.get("user_email") or intent_data.get("email")
                if not user_email or "brainlyarpit8649@gmail.com" not in user_email:
                    self.log_test("Gmail Chat Interface - Check Inbox", False, f"User email not properly extracted: {user_email}", intent_data)
                    return False
                
                # Check response for automation results or approval requirement
                response_text = data.get("response", "")
                needs_approval = data.get("needs_approval", False)
                
                # Check if automation was executed directly or needs approval
                if "automation_result" in intent_data:
                    # Direct execution
                    automation_success = intent_data.get("automation_success", False)
                    execution_time = intent_data.get("execution_time", 0)
                    
                    if automation_success and execution_time <= 30:
                        self.log_test("Gmail Chat Interface - Check Inbox", True, f"Gmail inbox check executed directly via chat. Execution time: {execution_time:.2f}s")
                        return True
                    else:
                        self.log_test("Gmail Chat Interface - Check Inbox", False, f"Direct execution failed or took too long. Success: {automation_success}, Time: {execution_time}s", data)
                        return False
                elif needs_approval:
                    # Approval required
                    self.log_test("Gmail Chat Interface - Check Inbox", True, f"Gmail inbox check detected and requires approval. Intent: {detected_intent}")
                    return True
                else:
                    self.log_test("Gmail Chat Interface - Check Inbox", False, "Gmail automation not properly handled via chat interface", data)
                    return False
            else:
                self.log_test("Gmail Chat Interface - Check Inbox", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Chat Interface - Check Inbox", False, f"Error: {str(e)}")
            return False

    def test_gmail_chat_interface_check_unread(self):
        """Test 5: Gmail automation via chat interface - Check unread emails"""
        try:
            payload = {
                "message": "Check Gmail unread emails for brainlyarpit8649@gmail.com",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if intent was detected correctly
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                # Should detect email automation or similar intent
                if detected_intent not in ["email_automation", "check_gmail_unread", "gmail_check"]:
                    self.log_test("Gmail Chat Interface - Check Unread", False, f"Wrong intent detected: {detected_intent}. Expected email automation related intent.", data)
                    return False
                
                # Check if user email was extracted
                user_email = intent_data.get("user_email") or intent_data.get("email")
                if not user_email or "brainlyarpit8649@gmail.com" not in user_email:
                    self.log_test("Gmail Chat Interface - Check Unread", False, f"User email not properly extracted: {user_email}", intent_data)
                    return False
                
                # Check if action was extracted correctly
                action = intent_data.get("action")
                if action and "unread" not in action.lower():
                    self.log_test("Gmail Chat Interface - Check Unread", False, f"Action not properly extracted: {action}. Should contain 'unread'", intent_data)
                    return False
                
                # Check response for automation results or approval requirement
                response_text = data.get("response", "")
                needs_approval = data.get("needs_approval", False)
                
                # Check if automation was executed directly or needs approval
                if "automation_result" in intent_data:
                    # Direct execution
                    automation_success = intent_data.get("automation_success", False)
                    execution_time = intent_data.get("execution_time", 0)
                    
                    if automation_success and execution_time <= 30:
                        self.log_test("Gmail Chat Interface - Check Unread", True, f"Gmail unread check executed directly via chat. Execution time: {execution_time:.2f}s")
                        return True
                    else:
                        self.log_test("Gmail Chat Interface - Check Unread", False, f"Direct execution failed or took too long. Success: {automation_success}, Time: {execution_time}s", data)
                        return False
                elif needs_approval:
                    # Approval required
                    self.log_test("Gmail Chat Interface - Check Unread", True, f"Gmail unread check detected and requires approval. Intent: {detected_intent}")
                    return True
                else:
                    self.log_test("Gmail Chat Interface - Check Unread", False, "Gmail automation not properly handled via chat interface", data)
                    return False
            else:
                self.log_test("Gmail Chat Interface - Check Unread", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Gmail Chat Interface - Check Unread", False, f"Error: {str(e)}")
            return False

    def run_gmail_tests(self):
        """Run Gmail automation tests"""
        print("🚀 Starting Gmail Automation Testing for brainlyarpit8649@gmail.com...")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        tests = [
            self.test_cookie_detection_for_gmail_user,
            self.test_gmail_automation_check_inbox_brainlyarpit,
            self.test_gmail_automation_check_unread_brainlyarpit,
            self.test_gmail_chat_interface_check_inbox,
            self.test_gmail_chat_interface_check_unread
        ]
        
        passed = 0
        failed = 0
        
        for test_method in tests:
            try:
                if test_method():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ FAIL - {test_method.__name__}: Unexpected error: {str(e)}")
                failed += 1
            
            # Small delay between tests
            time.sleep(1)
        
        print("=" * 70)
        print(f"🏁 Gmail Automation Testing Complete!")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL GMAIL TESTS PASSED! Cookie-based Gmail automation is working perfectly!")
        else:
            print(f"⚠️  {failed} tests failed. Please check the details above.")
        
        return {
            "total_tests": len(tests),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = GmailAutomationTester()
    results = tester.run_gmail_tests()
    
    # Save detailed results
    with open("/app/gmail_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed results saved to: /app/gmail_test_results.json")