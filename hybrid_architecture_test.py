#!/usr/bin/env python3
"""
Specific Testing for NEW HYBRID AI ARCHITECTURE
Tests the Claude Sonnet + Groq integration as requested in the review
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://682dd8cc-6ce4-48cb-bb8d-86737ebce0c9.preview.emergentagent.com/api"

class HybridArchitectureTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: any = None):
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
        print()

    def test_hybrid_routing_general_chat(self):
        """Test: General chat should route directly to Claude for warm conversation"""
        try:
            payload = {
                "message": "Hi Elva! How are you doing today? I'm feeling a bit stressed about work.",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be classified as general_chat
                intent_data = data.get("intent_data", {})
                if intent_data.get("intent") != "general_chat":
                    self.log_test("Hybrid Routing - General Chat", False, f"Wrong intent: {intent_data.get('intent')}")
                    return False
                
                # Should not need approval
                if data.get("needs_approval") != False:
                    self.log_test("Hybrid Routing - General Chat", False, "General chat should not need approval")
                    return False
                
                # Response should be warm and empathetic (Claude's strength)
                response_text = data.get("response", "")
                if len(response_text) < 20:
                    self.log_test("Hybrid Routing - General Chat", False, "Response too short for emotional intelligence")
                    return False
                
                # Check for emotional intelligence indicators
                emotional_indicators = ["feel", "understand", "support", "here for you", "sorry to hear", "glad", "wonderful"]
                has_emotional_response = any(indicator in response_text.lower() for indicator in emotional_indicators)
                
                if not has_emotional_response:
                    self.log_test("Hybrid Routing - General Chat", False, f"Response lacks emotional intelligence: {response_text[:100]}...")
                    return False
                
                self.log_test("Hybrid Routing - General Chat", True, f"Claude provided emotionally intelligent response: {response_text[:100]}...")
                return True
            else:
                self.log_test("Hybrid Routing - General Chat", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Hybrid Routing - General Chat", False, f"Error: {str(e)}")
            return False

    def test_hybrid_routing_email_intent(self):
        """Test: Email intent should use Groq for detection + Claude for draft"""
        try:
            payload = {
                "message": "I need to send a professional email to my colleague Maria about the quarterly budget review meeting we discussed",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be classified as send_email (Groq's structured reasoning)
                intent_data = data.get("intent_data", {})
                if intent_data.get("intent") != "send_email":
                    self.log_test("Hybrid Routing - Email Intent", False, f"Wrong intent: {intent_data.get('intent')}")
                    return False
                
                # Should need approval
                if data.get("needs_approval") != True:
                    self.log_test("Hybrid Routing - Email Intent", False, "Email intent should need approval")
                    return False
                
                # Check Groq's structured data extraction
                required_fields = ["recipient_name", "subject", "body"]
                missing_fields = [field for field in required_fields if not intent_data.get(field)]
                if missing_fields:
                    self.log_test("Hybrid Routing - Email Intent", False, f"Groq failed to extract: {missing_fields}")
                    return False
                
                # Check if recipient name was extracted correctly
                recipient_name = intent_data.get("recipient_name", "")
                if "maria" not in recipient_name.lower():
                    self.log_test("Hybrid Routing - Email Intent", False, f"Failed to extract recipient: {recipient_name}")
                    return False
                
                # Check Claude's friendly draft generation
                response_text = data.get("response", "")
                if len(response_text) < 50:
                    self.log_test("Hybrid Routing - Email Intent", False, "Claude's draft too short")
                    return False
                
                # Check for professional yet friendly tone (Claude's strength)
                professional_indicators = ["draft", "professional", "subject", "review", "feel free"]
                has_professional_tone = any(indicator in response_text.lower() for indicator in professional_indicators)
                
                if not has_professional_tone:
                    self.log_test("Hybrid Routing - Email Intent", False, f"Response lacks professional tone: {response_text[:100]}...")
                    return False
                
                self.log_test("Hybrid Routing - Email Intent", True, f"Groq detected intent + Claude generated professional draft. Recipient: {recipient_name}")
                return True
            else:
                self.log_test("Hybrid Routing - Email Intent", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Hybrid Routing - Email Intent", False, f"Error: {str(e)}")
            return False

    def test_hybrid_routing_linkedin_post(self):
        """Test: LinkedIn post should use Groq for detection + Claude for professional content"""
        try:
            payload = {
                "message": "Create a LinkedIn post about the importance of AI ethics in modern technology development",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be classified as linkedin_post
                intent_data = data.get("intent_data", {})
                if intent_data.get("intent") != "linkedin_post":
                    self.log_test("Hybrid Routing - LinkedIn Post", False, f"Wrong intent: {intent_data.get('intent')}")
                    return False
                
                # Should need approval
                if data.get("needs_approval") != True:
                    self.log_test("Hybrid Routing - LinkedIn Post", False, "LinkedIn post should need approval")
                    return False
                
                # Check Groq's topic extraction
                topic = intent_data.get("topic", "")
                if not topic or "ai" not in topic.lower():
                    self.log_test("Hybrid Routing - LinkedIn Post", False, f"Failed to extract topic: {topic}")
                    return False
                
                # Check Claude's professional content generation
                response_text = data.get("response", "")
                if len(response_text) < 50:
                    self.log_test("Hybrid Routing - LinkedIn Post", False, "Claude's LinkedIn content too short")
                    return False
                
                # Check for LinkedIn-appropriate professional tone
                linkedin_indicators = ["linkedin", "professional", "network", "insights", "share", "connect"]
                has_linkedin_tone = any(indicator in response_text.lower() for indicator in linkedin_indicators)
                
                if not has_linkedin_tone:
                    self.log_test("Hybrid Routing - LinkedIn Post", False, f"Response lacks LinkedIn tone: {response_text[:100]}...")
                    return False
                
                self.log_test("Hybrid Routing - LinkedIn Post", True, f"Groq detected LinkedIn intent + Claude generated professional content. Topic: {topic}")
                return True
            else:
                self.log_test("Hybrid Routing - LinkedIn Post", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Hybrid Routing - LinkedIn Post", False, f"Error: {str(e)}")
            return False

    def test_complex_intent_context(self):
        """Test: Complex intents with various wording and contexts"""
        test_cases = [
            {
                "message": "Could you help me draft an email to John Smith regarding the project deadline extension?",
                "expected_intent": "send_email",
                "expected_recipient": "john"
            },
            {
                "message": "I want to schedule a team standup for next Monday at 9 AM",
                "expected_intent": "create_event",
                "expected_title": "team"
            },
            {
                "message": "Please remind me to submit the expense report by Friday",
                "expected_intent": "set_reminder",
                "expected_text": "expense"
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(test_cases):
            try:
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get("intent_data", {})
                    
                    # Check intent classification
                    if intent_data.get("intent") != test_case["expected_intent"]:
                        print(f"    ❌ Test case {i+1}: Wrong intent {intent_data.get('intent')} vs {test_case['expected_intent']}")
                        all_passed = False
                        continue
                    
                    # Check specific field extraction
                    if test_case["expected_intent"] == "send_email":
                        recipient = intent_data.get("recipient_name", "").lower()
                        if test_case["expected_recipient"] not in recipient:
                            print(f"    ❌ Test case {i+1}: Failed to extract recipient {test_case['expected_recipient']} from {recipient}")
                            all_passed = False
                            continue
                    elif test_case["expected_intent"] == "create_event":
                        title = intent_data.get("event_title", "").lower()
                        if test_case["expected_title"] not in title:
                            print(f"    ❌ Test case {i+1}: Failed to extract title {test_case['expected_title']} from {title}")
                            all_passed = False
                            continue
                    elif test_case["expected_intent"] == "set_reminder":
                        reminder_text = intent_data.get("reminder_text", "").lower()
                        if test_case["expected_text"] not in reminder_text:
                            print(f"    ❌ Test case {i+1}: Failed to extract text {test_case['expected_text']} from {reminder_text}")
                            all_passed = False
                            continue
                    
                    print(f"    ✅ Test case {i+1}: {test_case['expected_intent']} correctly detected and processed")
                else:
                    print(f"    ❌ Test case {i+1}: HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                print(f"    ❌ Test case {i+1}: Error {str(e)}")
                all_passed = False
        
        if all_passed:
            self.log_test("Complex Intent Context", True, f"All {len(test_cases)} complex intent scenarios handled correctly")
            return True
        else:
            self.log_test("Complex Intent Context", False, "Some complex intent scenarios failed")
            return False

    def test_error_handling_fallback(self):
        """Test: Error handling and fallback mechanisms"""
        try:
            # Test with potentially problematic input
            payload = {
                "message": "This is a very ambiguous message that could be anything really, maybe send something or create something or just chat, who knows?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should have some response (fallback working)
                if not data.get("response"):
                    self.log_test("Error Handling - Fallback", False, "No response provided for ambiguous input")
                    return False
                
                # Should classify as something (even if general_chat)
                intent_data = data.get("intent_data", {})
                if not intent_data.get("intent"):
                    self.log_test("Error Handling - Fallback", False, "No intent classification for ambiguous input")
                    return False
                
                # Should not crash the system
                self.log_test("Error Handling - Fallback", True, f"Ambiguous input handled gracefully: {intent_data.get('intent')}")
                return True
            else:
                self.log_test("Error Handling - Fallback", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Error Handling - Fallback", False, f"Error: {str(e)}")
            return False

    def test_performance_comparison(self):
        """Test: Performance and quality comparison indicators"""
        try:
            # Test response time for general chat (Claude)
            start_time = time.time()
            
            payload = {
                "message": "Tell me about your capabilities and how you can help me with my daily tasks",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
            claude_response_time = time.time() - start_time
            
            if response.status_code != 200:
                self.log_test("Performance Comparison", False, "Failed to get Claude response")
                return False
            
            claude_data = response.json()
            claude_response_length = len(claude_data.get("response", ""))
            
            # Test response time for intent detection (Groq)
            start_time = time.time()
            
            payload = {
                "message": "Send an email to the marketing team about the new product launch campaign",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=30)
            groq_response_time = time.time() - start_time
            
            if response.status_code != 200:
                self.log_test("Performance Comparison", False, "Failed to get Groq response")
                return False
            
            groq_data = response.json()
            intent_data = groq_data.get("intent_data", {})
            
            # Analyze results
            performance_details = f"Claude (general chat): {claude_response_time:.2f}s, {claude_response_length} chars | Groq (intent): {groq_response_time:.2f}s, {len(intent_data)} fields extracted"
            
            # Both should complete within reasonable time
            if claude_response_time > 15 or groq_response_time > 15:
                self.log_test("Performance Comparison", False, f"Response times too slow: {performance_details}")
                return False
            
            # Claude should provide substantial response for general chat
            if claude_response_length < 100:
                self.log_test("Performance Comparison", False, f"Claude response too short: {claude_response_length} chars")
                return False
            
            # Groq should extract structured data
            if len(intent_data) < 3:
                self.log_test("Performance Comparison", False, f"Groq extracted insufficient data: {len(intent_data)} fields")
                return False
            
            self.log_test("Performance Comparison", True, f"Both models performing well: {performance_details}")
            return True
            
        except Exception as e:
            self.log_test("Performance Comparison", False, f"Error: {str(e)}")
            return False

    def run_hybrid_tests(self):
        """Run all hybrid architecture specific tests"""
        print("🚀 Starting Hybrid AI Architecture Testing")
        print("Testing Claude Sonnet + Groq Integration")
        print("=" * 60)
        
        test_methods = [
            self.test_hybrid_routing_general_chat,
            self.test_hybrid_routing_email_intent,
            self.test_hybrid_routing_linkedin_post,
            self.test_complex_intent_context,
            self.test_error_handling_fallback,
            self.test_performance_comparison
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
            
            time.sleep(1)  # Longer delay for API rate limits
        
        print("=" * 60)
        print(f"🏁 Hybrid Architecture Testing Complete!")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        return {
            "total_tests": len(test_methods),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = HybridArchitectureTester()
    results = tester.run_hybrid_tests()
    
    # Save detailed results
    with open("/app/hybrid_architecture_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed results saved to: /app/hybrid_architecture_test_results.json")