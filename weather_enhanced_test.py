#!/usr/bin/env python3
"""
Enhanced Weather Functionality Testing for Elva AI
Tests the enhanced weather functionality with specific requirements from review request:
1. Weather Forecast Format - detailed bullet point format
2. Current Weather Format - detailed bullet point format  
3. Rain Query Format - detailed rain preparation guide
4. Context Awareness - verify context references
5. Conversation Memory - verify memory across weather questions
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://036e8f47-2d63-48b2-8d92-5307403f57fb.preview.emergentagent.com/api"

class WeatherEnhancedTester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.test_results = []
        self.message_ids = []
        
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

    def test_weather_forecast_format(self):
        """Test 1: Weather Forecast Format - "4-day weather forecast in Kahalgaon" - verify detailed bullet point format"""
        try:
            payload = {
                "message": "4-day weather forecast in Kahalgaon",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                intent_data = data.get("intent_data", {})
                
                # Check if weather intent was detected
                if intent_data.get("intent") != "get_weather_forecast":
                    self.log_test("Weather Forecast Format - Intent Detection", False, f"Expected get_weather_forecast, got {intent_data.get('intent')}")
                    return False
                
                # Check if response is in detailed bullet point format
                bullet_indicators = ["•", "◦", "-", "*", "▪", "▫"]
                has_bullets = any(indicator in response_text for indicator in bullet_indicators)
                
                if not has_bullets:
                    self.log_test("Weather Forecast Format - Bullet Points", False, "Response not in bullet point format")
                    return False
                
                # Check for comprehensive weather details
                required_details = [
                    "temperature", "humidity", "wind", "condition", 
                    "forecast", "day", "weather"
                ]
                
                details_found = sum(1 for detail in required_details if detail.lower() in response_text.lower())
                
                if details_found < 4:  # At least 4 weather details should be present
                    self.log_test("Weather Forecast Format - Comprehensive Details", False, f"Only {details_found} weather details found, expected at least 4")
                    return False
                
                # Check response length (should be lengthy with comprehensive information)
                if len(response_text) < 200:
                    self.log_test("Weather Forecast Format - Length", False, f"Response too short ({len(response_text)} chars), expected lengthy description")
                    return False
                
                # Check for 4-day forecast structure
                day_indicators = ["today", "tomorrow", "day", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                day_mentions = sum(1 for day in day_indicators if day.lower() in response_text.lower())
                
                if day_mentions < 3:  # Should mention multiple days
                    self.log_test("Weather Forecast Format - Multi-day Structure", False, f"Only {day_mentions} day mentions found, expected multi-day forecast")
                    return False
                
                self.message_ids.append(data["id"])
                self.log_test("Weather Forecast Format", True, f"4-day forecast for Kahalgaon in detailed bullet format with {details_found} weather details, {len(response_text)} chars, {day_mentions} day mentions")
                return True
            else:
                self.log_test("Weather Forecast Format", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Weather Forecast Format", False, f"Error: {str(e)}")
            return False

    def test_current_weather_format(self):
        """Test 2: Current Weather Format - "What's the current weather in Delhi?" - verify detailed bullet point format"""
        try:
            payload = {
                "message": "What's the current weather in Delhi?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                intent_data = data.get("intent_data", {})
                
                # Check if weather intent was detected
                if intent_data.get("intent") != "get_current_weather":
                    self.log_test("Current Weather Format - Intent Detection", False, f"Expected get_current_weather, got {intent_data.get('intent')}")
                    return False
                
                # Check if response is in detailed bullet point format
                bullet_indicators = ["•", "◦", "-", "*", "▪", "▫"]
                has_bullets = any(indicator in response_text for indicator in bullet_indicators)
                
                if not has_bullets:
                    self.log_test("Current Weather Format - Bullet Points", False, "Response not in bullet point format")
                    return False
                
                # Check for comprehensive current weather information
                required_details = [
                    "temperature", "humidity", "wind", "condition", 
                    "feels like", "visibility", "pressure", "delhi"
                ]
                
                details_found = sum(1 for detail in required_details if detail.lower() in response_text.lower())
                
                if details_found < 5:  # At least 5 current weather details should be present
                    self.log_test("Current Weather Format - Comprehensive Details", False, f"Only {details_found} weather details found, expected at least 5")
                    return False
                
                # Check response length (should be comprehensive)
                if len(response_text) < 150:
                    self.log_test("Current Weather Format - Length", False, f"Response too short ({len(response_text)} chars), expected comprehensive description")
                    return False
                
                # Check for current weather indicators
                current_indicators = ["current", "now", "currently", "present", "today"]
                current_mentions = sum(1 for indicator in current_indicators if indicator.lower() in response_text.lower())
                
                if current_mentions < 1:
                    self.log_test("Current Weather Format - Current Indicators", False, "No current weather indicators found")
                    return False
                
                self.message_ids.append(data["id"])
                self.log_test("Current Weather Format", True, f"Current weather for Delhi in detailed bullet format with {details_found} weather details, {len(response_text)} chars, {current_mentions} current indicators")
                return True
            else:
                self.log_test("Current Weather Format", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Current Weather Format", False, f"Error: {str(e)}")
            return False

    def test_rain_query_format(self):
        """Test 3: Rain Query Format - "Will it rain tomorrow in Mumbai?" - verify detailed rain preparation guide"""
        try:
            payload = {
                "message": "Will it rain tomorrow in Mumbai?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                intent_data = data.get("intent_data", {})
                
                # Check if weather forecast intent was detected (rain queries are forecast-based)
                if intent_data.get("intent") != "get_weather_forecast":
                    self.log_test("Rain Query Format - Intent Detection", False, f"Expected get_weather_forecast, got {intent_data.get('intent')}")
                    return False
                
                # Check for rain-specific information
                rain_keywords = [
                    "rain", "precipitation", "shower", "drizzle", 
                    "chance", "probability", "umbrella", "wet"
                ]
                
                rain_mentions = sum(1 for keyword in rain_keywords if keyword.lower() in response_text.lower())
                
                if rain_mentions < 2:
                    self.log_test("Rain Query Format - Rain Information", False, f"Only {rain_mentions} rain-related terms found, expected comprehensive rain information")
                    return False
                
                # Check for detailed rain preparation guide elements
                preparation_keywords = [
                    "umbrella", "raincoat", "indoor", "outdoor", "prepare", 
                    "advice", "suggestion", "recommend", "avoid", "plan"
                ]
                
                preparation_mentions = sum(1 for keyword in preparation_keywords if keyword.lower() in response_text.lower())
                
                if preparation_mentions < 1:
                    self.log_test("Rain Query Format - Preparation Guide", False, f"No rain preparation guidance found")
                    return False
                
                # Check if response is in detailed bullet point format
                bullet_indicators = ["•", "◦", "-", "*", "▪", "▫"]
                has_bullets = any(indicator in response_text for indicator in bullet_indicators)
                
                if not has_bullets:
                    self.log_test("Rain Query Format - Bullet Points", False, "Response not in bullet point format")
                    return False
                
                # Check response length (should be detailed)
                if len(response_text) < 100:
                    self.log_test("Rain Query Format - Length", False, f"Response too short ({len(response_text)} chars), expected detailed rain guide")
                    return False
                
                # Check for Mumbai location reference
                if "mumbai" not in response_text.lower():
                    self.log_test("Rain Query Format - Location Reference", False, "Mumbai not mentioned in response")
                    return False
                
                # Check for tomorrow reference
                tomorrow_indicators = ["tomorrow", "next day", "24 hours"]
                tomorrow_mentions = sum(1 for indicator in tomorrow_indicators if indicator.lower() in response_text.lower())
                
                if tomorrow_mentions < 1:
                    self.log_test("Rain Query Format - Tomorrow Reference", False, "No tomorrow reference found")
                    return False
                
                self.message_ids.append(data["id"])
                self.log_test("Rain Query Format", True, f"Rain query for Mumbai with {rain_mentions} rain terms, {preparation_mentions} preparation elements, {len(response_text)} chars, bullet format")
                return True
            else:
                self.log_test("Rain Query Format", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Rain Query Format", False, f"Error: {str(e)}")
            return False

    def test_context_awareness(self):
        """Test 4: Context Awareness - First "What's the weather in Delhi?" then "What about tomorrow?" - verify context references"""
        try:
            # First message: "What's the weather in Delhi?"
            payload1 = {
                "message": "What's the weather in Delhi?",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response1 = requests.post(f"{BACKEND_URL}/chat", json=payload1, timeout=20)
            
            if response1.status_code != 200:
                self.log_test("Context Awareness - First Message", False, f"HTTP {response1.status_code}", response1.text)
                return False
            
            data1 = response1.json()
            response_text1 = data1.get("response", "")
            
            # Wait a moment for context to be stored
            time.sleep(2)
            
            # Second message: "What about tomorrow?"
            payload2 = {
                "message": "What about tomorrow?",
                "session_id": self.session_id,  # Same session ID for context
                "user_id": "test_user"
            }
            
            response2 = requests.post(f"{BACKEND_URL}/chat", json=payload2, timeout=20)
            
            if response2.status_code != 200:
                self.log_test("Context Awareness - Second Message", False, f"HTTP {response2.status_code}", response2.text)
                return False
            
            data2 = response2.json()
            response_text2 = data2.get("response", "")
            intent_data2 = data2.get("intent_data", {})
            
            # Check if the second response references the previous weather question context
            context_indicators = [
                "delhi", "previous", "earlier", "before", "mentioned", 
                "asked", "weather", "forecast", "tomorrow"
            ]
            
            context_references = sum(1 for indicator in context_indicators if indicator.lower() in response_text2.lower())
            
            if context_references < 2:
                self.log_test("Context Awareness - Context References", False, f"Only {context_references} context references found, expected context-aware response")
                return False
            
            # Check if Delhi is mentioned in the second response (context awareness)
            if "delhi" not in response_text2.lower():
                self.log_test("Context Awareness - Location Context", False, "Delhi not referenced in follow-up response, context not maintained")
                return False
            
            # Check if the second response is weather-related
            weather_keywords = ["weather", "temperature", "forecast", "condition", "rain", "sunny", "cloudy"]
            weather_mentions = sum(1 for keyword in weather_keywords if keyword.lower() in response_text2.lower())
            
            if weather_mentions < 1:
                self.log_test("Context Awareness - Weather Context", False, "Second response not weather-related, context not understood")
                return False
            
            # Check if tomorrow is properly handled
            tomorrow_indicators = ["tomorrow", "next day", "24 hours", "forecast"]
            tomorrow_mentions = sum(1 for indicator in tomorrow_indicators if indicator.lower() in response_text2.lower())
            
            if tomorrow_mentions < 1:
                self.log_test("Context Awareness - Tomorrow Context", False, "Tomorrow context not properly handled")
                return False
            
            self.message_ids.extend([data1["id"], data2["id"]])
            self.log_test("Context Awareness", True, f"Context maintained: {context_references} context refs, Delhi referenced, {weather_mentions} weather terms, {tomorrow_mentions} tomorrow refs")
            return True
            
        except Exception as e:
            self.log_test("Context Awareness", False, f"Error: {str(e)}")
            return False

    def test_conversation_memory(self):
        """Test 5: Conversation Memory - Multiple weather questions in sequence to verify memory"""
        try:
            weather_questions = [
                "What's the weather like in London?",
                "How about Paris?",
                "Will it rain in Berlin tomorrow?",
                "What was the weather I asked about first?"
            ]
            
            responses = []
            all_passed = True
            
            for i, question in enumerate(weather_questions):
                payload = {
                    "message": question,
                    "session_id": self.session_id,  # Same session for memory
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
                
                if response.status_code != 200:
                    self.log_test(f"Conversation Memory - Question {i+1}", False, f"HTTP {response.status_code}")
                    all_passed = False
                    continue
                
                data = response.json()
                response_text = data.get("response", "")
                responses.append({
                    "question": question,
                    "response": response_text,
                    "id": data.get("id")
                })
                
                # Wait between requests for memory processing
                time.sleep(1)
            
            if not all_passed:
                return False
            
            # Check if the last question about "first weather" references London
            last_response = responses[-1]["response"].lower()
            
            if "london" not in last_response:
                self.log_test("Conversation Memory - First Question Reference", False, "Last response doesn't reference London (first weather question)")
                return False
            
            # Check if middle questions show context awareness
            second_response = responses[1]["response"].lower()
            if "paris" not in second_response:
                self.log_test("Conversation Memory - Location Context", False, "Second response doesn't mention Paris")
                return False
            
            third_response = responses[2]["response"].lower()
            if "berlin" not in third_response or "rain" not in third_response:
                self.log_test("Conversation Memory - Rain Context", False, "Third response doesn't properly handle Berlin rain query")
                return False
            
            # Check for conversation continuity indicators
            continuity_indicators = ["also", "additionally", "furthermore", "previous", "earlier", "before"]
            continuity_found = 0
            
            for response_data in responses[1:]:  # Skip first response
                response_text = response_data["response"].lower()
                continuity_found += sum(1 for indicator in continuity_indicators if indicator in response_text)
            
            if continuity_found < 1:
                self.log_test("Conversation Memory - Continuity Indicators", False, "No conversation continuity indicators found")
                return False
            
            # Add all message IDs
            self.message_ids.extend([r["id"] for r in responses if r.get("id")])
            
            self.log_test("Conversation Memory", True, f"Memory maintained across {len(responses)} questions: London→Paris→Berlin sequence, first question referenced, {continuity_found} continuity indicators")
            return True
            
        except Exception as e:
            self.log_test("Conversation Memory", False, f"Error: {str(e)}")
            return False

    def test_weather_api_endpoints_direct(self):
        """Test 6: Direct Weather API Endpoints - Test backend weather endpoints directly"""
        try:
            # Test current weather endpoint
            current_response = requests.get(f"{BACKEND_URL}/weather/current?location=Delhi", timeout=15)
            
            if current_response.status_code != 200:
                self.log_test("Weather API - Current Weather", False, f"HTTP {current_response.status_code}")
                return False
            
            current_data = current_response.json()
            if current_data.get("status") != "success":
                self.log_test("Weather API - Current Weather", False, f"API status: {current_data.get('status')}")
                return False
            
            # Test forecast endpoint
            forecast_response = requests.get(f"{BACKEND_URL}/weather/forecast?location=Mumbai&days=3", timeout=15)
            
            if forecast_response.status_code != 200:
                self.log_test("Weather API - Forecast", False, f"HTTP {forecast_response.status_code}")
                return False
            
            forecast_data = forecast_response.json()
            if forecast_data.get("status") != "success":
                self.log_test("Weather API - Forecast", False, f"API status: {forecast_data.get('status')}")
                return False
            
            # Test health endpoint for weather integration
            health_response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if health_response.status_code != 200:
                self.log_test("Weather API - Health Check", False, f"HTTP {health_response.status_code}")
                return False
            
            health_data = health_response.json()
            weather_integration = health_data.get("weather_integration", {})
            
            if weather_integration.get("status") != "ready":
                self.log_test("Weather API - Integration Status", False, f"Weather integration status: {weather_integration.get('status')}")
                return False
            
            if not weather_integration.get("api_key_configured"):
                self.log_test("Weather API - API Key", False, "Weather API key not configured")
                return False
            
            self.log_test("Weather API Endpoints", True, f"Current weather, forecast, and health endpoints working. Provider: {weather_integration.get('provider')}")
            return True
            
        except Exception as e:
            self.log_test("Weather API Endpoints", False, f"Error: {str(e)}")
            return False

    def test_weather_response_natural_language(self):
        """Test 7: Natural Language Weather Responses - Verify responses are natural and friendly"""
        try:
            test_queries = [
                "Is it going to be hot today in Chennai?",
                "Should I carry an umbrella in Bangalore?",
                "What should I wear for the weather in Kolkata?"
            ]
            
            all_passed = True
            natural_scores = []
            
            for query in test_queries:
                payload = {
                    "message": query,
                    "session_id": self.session_id,
                    "user_id": "test_user"
                }
                
                response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=20)
                
                if response.status_code != 200:
                    all_passed = False
                    continue
                
                data = response.json()
                response_text = data.get("response", "")
                
                # Check for natural language indicators
                natural_indicators = [
                    "you", "your", "i", "recommend", "suggest", "should", 
                    "would", "could", "might", "probably", "likely"
                ]
                
                natural_score = sum(1 for indicator in natural_indicators if indicator.lower() in response_text.lower())
                natural_scores.append(natural_score)
                
                # Check for friendly tone
                friendly_indicators = [
                    "!", "😊", "☀️", "🌧️", "⛅", "🌤️", "❄️", "🌈", 
                    "great", "perfect", "lovely", "nice", "enjoy"
                ]
                
                friendly_score = sum(1 for indicator in friendly_indicators if indicator in response_text)
                
                if natural_score < 2 and friendly_score < 1:
                    self.log_test(f"Natural Language - {query[:30]}...", False, f"Response not natural/friendly enough: natural={natural_score}, friendly={friendly_score}")
                    all_passed = False
                
                self.message_ids.append(data["id"])
            
            if all_passed:
                avg_natural_score = sum(natural_scores) / len(natural_scores)
                self.log_test("Weather Response Natural Language", True, f"All responses natural and friendly. Avg natural score: {avg_natural_score:.1f}")
                return True
            else:
                self.log_test("Weather Response Natural Language", False, "Some responses not natural/friendly enough")
                return False
                
        except Exception as e:
            self.log_test("Weather Response Natural Language", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all enhanced weather functionality tests"""
        print("🌦️ Starting Enhanced Weather Functionality Testing...")
        print(f"Session ID: {self.session_id}")
        print("=" * 80)
        
        tests = [
            self.test_weather_forecast_format,
            self.test_current_weather_format,
            self.test_rain_query_format,
            self.test_context_awareness,
            self.test_conversation_memory,
            self.test_weather_api_endpoints_direct,
            self.test_weather_response_natural_language
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
        
        print("=" * 80)
        print(f"🌦️ Enhanced Weather Testing Complete: {passed}/{total} tests passed")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL ENHANCED WEATHER FUNCTIONALITY TESTS PASSED!")
        else:
            print(f"⚠️  {total-passed} tests failed - see details above")
        
        return passed == total

def main():
    """Main test execution"""
    tester = WeatherEnhancedTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Enhanced Weather Functionality: ALL TESTS PASSED")
        exit(0)
    else:
        print("\n❌ Enhanced Weather Functionality: SOME TESTS FAILED")
        exit(1)

if __name__ == "__main__":
    main()