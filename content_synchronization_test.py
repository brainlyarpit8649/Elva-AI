#!/usr/bin/env python3
"""
Content Synchronization Testing for Elva AI
Tests the specific fix for approval modal content synchronization issue.

This test verifies that:
1. AI Summary (response) and intent_data fields contain the SAME content
2. Both use identical text with no separate generation
3. Content synchronization is working properly
4. Content extraction patterns are finding and matching the right content from Claude's response
"""

import requests
import json
import uuid
import time
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Backend URL from frontend/.env
BACKEND_URL = "https://72e97293-ded7-4170-aeb3-7df6343cbbb4.preview.emergentagent.com/api"

class ContentSynchronizationTester:
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

    def extract_content_from_response(self, response_text: str, intent: str) -> Optional[str]:
        """Extract the actual content from Claude's response based on intent type"""
        try:
            if intent == "send_email":
                # Extract subject and body from Claude's response
                subject_match = re.search(r'Subject:\s*(.+)', response_text)
                body_match = re.search(r'Body:\s*(.*?)(?:\n\nThe content|$)', response_text, re.DOTALL)
                
                if subject_match and body_match:
                    return {
                        "subject": subject_match.group(1).strip(),
                        "body": body_match.group(1).strip()
                    }
                    
            elif intent == "linkedin_post":
                # Enhanced LinkedIn post content extraction with multiple patterns
                content_patterns = [
                    r'📱.*?:\s*\n+(.*?)(?:\n\n(?:This|Feel free|Let me know)|$)',
                    r'Here\'s.*?:\s*\n+(.*?)(?:\n\n(?:This|Feel free|Let me know)|$)',
                    r'"([^"]{50,})"',  # Look for substantial quoted content
                    r'\n\n([^"]+?)\n\n',
                    r'^[^.!?]+[.!?]\s*\n+(.*?)(?:\n\nThis|$)',
                ]
                
                for pattern in content_patterns:
                    match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        candidate_content = match.group(1).strip()
                        if len(candidate_content) > 20 and not candidate_content.lower().startswith(('here', 'i\'ve', 'let me')):
                            return candidate_content.replace('""', '"').strip()
                            
            elif intent == "creative_writing":
                # Similar pattern extraction for creative writing
                content_patterns = [
                    r'✨.*?:\s*\n+(.*?)(?:\n\n(?:This|Feel free|Let me know)|$)',
                    r'Here\'s.*?:\s*\n+(.*?)(?:\n\n(?:This|Feel free|Let me know)|$)',
                    r'"([^"]{50,})"',
                    r'\n\n([^"]+?)\n\n',
                ]
                
                for pattern in content_patterns:
                    match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        candidate_content = match.group(1).strip()
                        if len(candidate_content) > 20:
                            return candidate_content.replace('""', '"').strip()
                            
        except Exception as e:
            print(f"    Content extraction error: {e}")
            
        return None

    def compare_content_synchronization(self, response_text: str, intent_data: dict, intent: str) -> Tuple[bool, str]:
        """Compare content between Claude response and intent_data fields"""
        try:
            if intent == "send_email":
                # Extract content from Claude response
                extracted_content = self.extract_content_from_response(response_text, intent)
                if not extracted_content:
                    return False, "Could not extract subject/body from Claude response"
                
                # Compare with intent_data
                intent_subject = intent_data.get("subject", "").strip()
                intent_body = intent_data.get("body", "").strip()
                
                extracted_subject = extracted_content.get("subject", "").strip()
                extracted_body = extracted_content.get("body", "").strip()
                
                # Check if they match (allowing for minor formatting differences)
                subject_match = self.content_similarity(extracted_subject, intent_subject)
                body_match = self.content_similarity(extracted_body, intent_body)
                
                if subject_match and body_match:
                    return True, f"✅ Content synchronized - Subject: '{intent_subject}' | Body: {len(intent_body)} chars"
                else:
                    return False, f"❌ Content mismatch - Subject match: {subject_match}, Body match: {body_match}\nExtracted Subject: '{extracted_subject}'\nIntent Subject: '{intent_subject}'\nExtracted Body: '{extracted_body[:100]}...'\nIntent Body: '{intent_body[:100]}...'"
                    
            elif intent == "linkedin_post":
                # Extract content from Claude response
                extracted_content = self.extract_content_from_response(response_text, intent)
                if not extracted_content:
                    return False, "Could not extract post content from Claude response"
                
                # Compare with intent_data
                intent_content = intent_data.get("post_content", "").strip()
                
                if self.content_similarity(extracted_content, intent_content):
                    return True, f"✅ LinkedIn content synchronized - {len(intent_content)} chars"
                else:
                    return False, f"❌ LinkedIn content mismatch\nExtracted: '{extracted_content[:100]}...'\nIntent: '{intent_content[:100]}...'"
                    
            elif intent == "creative_writing":
                # Extract content from Claude response
                extracted_content = self.extract_content_from_response(response_text, intent)
                if not extracted_content:
                    return False, "Could not extract creative content from Claude response"
                
                # Compare with intent_data
                intent_content = intent_data.get("content", "").strip()
                
                if self.content_similarity(extracted_content, intent_content):
                    return True, f"✅ Creative content synchronized - {len(intent_content)} chars"
                else:
                    return False, f"❌ Creative content mismatch\nExtracted: '{extracted_content[:100]}...'\nIntent: '{intent_content[:100]}...'"
                    
            return False, f"Unsupported intent type for content synchronization: {intent}"
            
        except Exception as e:
            return False, f"Content comparison error: {str(e)}"

    def content_similarity(self, content1: str, content2: str, threshold: float = 0.8) -> bool:
        """Check if two content strings are similar enough (accounting for minor formatting differences)"""
        if not content1 or not content2:
            return False
            
        # Normalize whitespace and remove quotes
        norm1 = ' '.join(content1.replace('"', '').replace("'", "").split())
        norm2 = ' '.join(content2.replace('"', '').replace("'", "").split())
        
        # Check if they're identical after normalization
        if norm1 == norm2:
            return True
            
        # Check if one contains the other (for cases where extraction might include extra text)
        if norm1 in norm2 or norm2 in norm1:
            return True
            
        # Calculate similarity ratio
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= threshold

    def test_email_content_synchronization(self):
        """Test 1: Email intent content synchronization"""
        try:
            payload = {
                "message": "Send a professional email to Sarah about the quarterly meeting schedule",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check basic structure
                intent_data = data.get("intent_data", {})
                response_text = data.get("response", "")
                intent = intent_data.get("intent", "")
                
                if intent != "send_email":
                    self.log_test("Email Content Synchronization", False, f"Wrong intent detected: {intent}", data)
                    return False
                
                # Check that intent_data has required fields
                required_fields = ["subject", "body", "recipient_name"]
                missing_fields = [field for field in required_fields if not intent_data.get(field)]
                
                if missing_fields:
                    self.log_test("Email Content Synchronization", False, f"Missing intent fields: {missing_fields}", intent_data)
                    return False
                
                # Main test: Compare content synchronization
                is_synchronized, details = self.compare_content_synchronization(response_text, intent_data, intent)
                
                if is_synchronized:
                    self.log_test("Email Content Synchronization", True, f"Email content properly synchronized. {details}")
                    return True
                else:
                    self.log_test("Email Content Synchronization", False, f"Content synchronization failed. {details}")
                    return False
                    
            else:
                self.log_test("Email Content Synchronization", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Email Content Synchronization", False, f"Error: {str(e)}")
            return False

    def test_linkedin_content_synchronization(self):
        """Test 2: LinkedIn post intent content synchronization"""
        try:
            payload = {
                "message": "Create a LinkedIn post about AI innovations in 2025",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check basic structure
                intent_data = data.get("intent_data", {})
                response_text = data.get("response", "")
                intent = intent_data.get("intent", "")
                
                if intent != "linkedin_post":
                    self.log_test("LinkedIn Content Synchronization", False, f"Wrong intent detected: {intent}", data)
                    return False
                
                # Check that intent_data has post_content field
                if not intent_data.get("post_content"):
                    self.log_test("LinkedIn Content Synchronization", False, "Missing post_content field", intent_data)
                    return False
                
                # Main test: Compare content synchronization
                is_synchronized, details = self.compare_content_synchronization(response_text, intent_data, intent)
                
                if is_synchronized:
                    self.log_test("LinkedIn Content Synchronization", True, f"LinkedIn content properly synchronized. {details}")
                    return True
                else:
                    self.log_test("LinkedIn Content Synchronization", False, f"Content synchronization failed. {details}")
                    return False
                    
            else:
                self.log_test("LinkedIn Content Synchronization", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("LinkedIn Content Synchronization", False, f"Error: {str(e)}")
            return False

    def test_creative_writing_content_synchronization(self):
        """Test 3: Creative writing intent content synchronization"""
        try:
            payload = {
                "message": "Write creative content about teamwork and collaboration for my website",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check basic structure
                intent_data = data.get("intent_data", {})
                response_text = data.get("response", "")
                intent = intent_data.get("intent", "")
                
                if intent != "creative_writing":
                    self.log_test("Creative Writing Content Synchronization", False, f"Wrong intent detected: {intent}", data)
                    return False
                
                # Check that intent_data has content field
                if not intent_data.get("content"):
                    self.log_test("Creative Writing Content Synchronization", False, "Missing content field", intent_data)
                    return False
                
                # Main test: Compare content synchronization
                is_synchronized, details = self.compare_content_synchronization(response_text, intent_data, intent)
                
                if is_synchronized:
                    self.log_test("Creative Writing Content Synchronization", True, f"Creative content properly synchronized. {details}")
                    return True
                else:
                    self.log_test("Creative Writing Content Synchronization", False, f"Content synchronization failed. {details}")
                    return False
                    
            else:
                self.log_test("Creative Writing Content Synchronization", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Creative Writing Content Synchronization", False, f"Error: {str(e)}")
            return False

    def test_content_extraction_patterns(self):
        """Test 4: Verify content extraction patterns are working correctly"""
        try:
            # Test with a known response format
            test_response = """📱 Here's an engaging LinkedIn post for you:

🚀 The future of AI in 2025 is here! From revolutionary breakthroughs in machine learning to game-changing applications across industries, we're witnessing unprecedented innovation.

Key trends to watch:
✨ Hybrid AI architectures combining multiple models
🎯 Enhanced emotional intelligence in AI systems  
🔗 Seamless integration with business workflows
💡 Creative AI pushing boundaries in content generation

The possibilities are endless when technology meets human creativity! 

#AI2025 #Innovation #TechTrends #FutureOfWork #MachineLearning

This should help you engage with your professional network about the exciting developments in AI!"""
            
            # Test extraction
            extracted_content = self.extract_content_from_response(test_response, "linkedin_post")
            
            if extracted_content:
                # Check if the extracted content contains the main post content
                expected_keywords = ["AI in 2025", "Key trends", "#AI2025", "machine learning"]
                found_keywords = sum(1 for keyword in expected_keywords if keyword.lower() in extracted_content.lower())
                
                if found_keywords >= 3:
                    self.log_test("Content Extraction Patterns", True, f"Successfully extracted LinkedIn content with {found_keywords}/4 expected keywords")
                    return True
                else:
                    self.log_test("Content Extraction Patterns", False, f"Extracted content missing key elements. Found {found_keywords}/4 keywords. Content: {extracted_content[:200]}...")
                    return False
            else:
                self.log_test("Content Extraction Patterns", False, "Failed to extract any content from test response")
                return False
                
        except Exception as e:
            self.log_test("Content Extraction Patterns", False, f"Error: {str(e)}")
            return False

    def run_content_synchronization_tests(self):
        """Run all content synchronization tests"""
        print("🎯 Starting Content Synchronization Testing for Elva AI")
        print("=" * 60)
        print("Testing the fix for approval modal content synchronization issue")
        print("Verifying that AI Summary and intent_data fields contain SAME content")
        print("=" * 60)
        
        test_methods = [
            self.test_email_content_synchronization,
            self.test_linkedin_content_synchronization,
            self.test_creative_writing_content_synchronization,
            self.test_content_extraction_patterns
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
            time.sleep(1)
        
        print("=" * 60)
        print(f"🏁 Content Synchronization Testing Complete!")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        # Summary of what was tested
        print("\n📋 Test Summary:")
        print("✓ Email intent: AI response vs intent_data (subject, body) synchronization")
        print("✓ LinkedIn post intent: AI response vs intent_data (post_content) synchronization")  
        print("✓ Creative writing intent: AI response vs intent_data (content) synchronization")
        print("✓ Content extraction patterns: Regex patterns finding correct content")
        
        return {
            "total_tests": len(test_methods),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = ContentSynchronizationTester()
    results = tester.run_content_synchronization_tests()
    
    # Save detailed results
    with open("/app/content_sync_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed results saved to: /app/content_sync_test_results.json")