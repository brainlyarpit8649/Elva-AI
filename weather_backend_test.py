#!/usr/bin/env python3
"""
Comprehensive Weather Forecast Backend Testing for Elva AI
Tests the fixed weather forecast functionality as requested in the review
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://ab5f30cf-28b7-448e-92ee-50cd74c372d1.preview.emergentagent.com/api"

class WeatherBackendTester:
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

    def test_direct_weather_forecast_api_1_day(self):
        """Test 1: Direct API endpoint test - GET /api/weather/forecast?location=Delhi&days=1"""
        try:
            response = requests.get(f"{BACKEND_URL}/weather/forecast?location=Delhi&days=1", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["status", "data", "location", "days"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Direct API - Weather Forecast 1 Day", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check status is success
                if data.get("status") != "success":
                    self.log_test("Direct API - Weather Forecast 1 Day", False, f"Status not success: {data.get('status')}", data)
                    return False
                
                # Check location is Delhi
                if "Delhi" not in data.get("location", ""):
                    self.log_test("Direct API - Weather Forecast 1 Day", False, f"Location mismatch: {data.get('location')}", data)
                    return False
                
                # Check days is 1
                if data.get("days") != 1:
                    self.log_test("Direct API - Weather Forecast 1 Day", False, f"Days mismatch: {data.get('days')}", data)
                    return False
                
                # Check forecast data contains rain information
                forecast_data = data.get("data", "")
                if not forecast_data:
                    self.log_test("Direct API - Weather Forecast 1 Day", False, "No forecast data returned", data)
                    return False
                
                # For 1-day forecast, should contain yes/no rain answer
                rain_keywords = ["yes", "no", "rain", "likely", "unlikely", "%"]
                has_rain_info = any(keyword.lower() in forecast_data.lower() for keyword in rain_keywords)
                
                if not has_rain_info:
                    self.log_test("Direct API - Weather Forecast 1 Day", False, "No rain information in forecast", data)
                    return False
                
                self.log_test("Direct API - Weather Forecast 1 Day", True, f"Successfully retrieved 1-day forecast for Delhi with rain information")
                return True
            else:
                self.log_test("Direct API - Weather Forecast 1 Day", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Direct API - Weather Forecast 1 Day", False, f"Error: {str(e)}")
            return False

    def test_direct_weather_forecast_api_3_days(self):
        """Test 2: Direct API endpoint test - GET /api/weather/forecast?location=Delhi&days=3"""
        try:
            response = requests.get(f"{BACKEND_URL}/weather/forecast?location=Delhi&days=3", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["status", "data", "location", "days"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Direct API - Weather Forecast 3 Days", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check status is success
                if data.get("status") != "success":
                    self.log_test("Direct API - Weather Forecast 3 Days", False, f"Status not success: {data.get('status')}", data)
                    return False
                
                # Check location is Delhi
                if "Delhi" not in data.get("location", ""):
                    self.log_test("Direct API - Weather Forecast 3 Days", False, f"Location mismatch: {data.get('location')}", data)
                    return False
                
                # Check days is 3
                if data.get("days") != 3:
                    self.log_test("Direct API - Weather Forecast 3 Days", False, f"Days mismatch: {data.get('days')}", data)
                    return False
                
                # Check forecast data contains detailed daily breakdown
                forecast_data = data.get("data", "")
                if not forecast_data:
                    self.log_test("Direct API - Weather Forecast 3 Days", False, "No forecast data returned", data)
                    return False
                
                # For 3-day forecast, should contain daily breakdown
                daily_keywords = ["today", "tomorrow", "day", "temperature", "rain chance", "%"]
                has_daily_breakdown = any(keyword.lower() in forecast_data.lower() for keyword in daily_keywords)
                
                if not has_daily_breakdown:
                    self.log_test("Direct API - Weather Forecast 3 Days", False, "No daily breakdown in forecast", data)
                    return False
                
                self.log_test("Direct API - Weather Forecast 3 Days", True, f"Successfully retrieved 3-day forecast for Delhi with daily breakdown")
                return True
            else:
                self.log_test("Direct API - Weather Forecast 3 Days", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Direct API - Weather Forecast 3 Days", False, f"Error: {str(e)}")
            return False

    def test_chat_integration_rain_tomorrow_delhi(self):
        """Test 3: Chat integration - 'Will it rain tomorrow in Delhi' (should map to get_weather_forecast with days=1)"""
        try:
            payload = {
                "message": "Will it rain tomorrow in Delhi",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["id", "message", "response", "intent_data", "needs_approval", "timestamp"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Chat Integration - Rain Tomorrow Delhi", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check intent detection
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                if detected_intent != "get_weather_forecast":
                    self.log_test("Chat Integration - Rain Tomorrow Delhi", False, f"Wrong intent detected: {detected_intent}, expected get_weather_forecast", data)
                    return False
                
                # Check location extraction
                location = intent_data.get("location")
                if not location or "Delhi" not in location:
                    self.log_test("Chat Integration - Rain Tomorrow Delhi", False, f"Location not extracted correctly: {location}", data)
                    return False
                
                # Check days parameter (should be 1 for tomorrow)
                days = intent_data.get("days", 0)
                if days != 1:
                    self.log_test("Chat Integration - Rain Tomorrow Delhi", False, f"Days parameter incorrect: {days}, expected 1", data)
                    return False
                
                # Check needs_approval is False (weather queries should be instant)
                if data.get("needs_approval") != False:
                    self.log_test("Chat Integration - Rain Tomorrow Delhi", False, "Weather queries should not need approval", data)
                    return False
                
                # Check response contains rain information with yes/no answer
                response_text = data.get("response", "")
                rain_answer_keywords = ["yes", "no", "likely", "unlikely", "rain"]
                has_rain_answer = any(keyword.lower() in response_text.lower() for keyword in rain_answer_keywords)
                
                if not has_rain_answer:
                    self.log_test("Chat Integration - Rain Tomorrow Delhi", False, "Response doesn't contain clear rain answer", data)
                    return False
                
                self.log_test("Chat Integration - Rain Tomorrow Delhi", True, f"Successfully detected weather forecast intent with rain answer: {response_text[:100]}...")
                return True
            else:
                self.log_test("Chat Integration - Rain Tomorrow Delhi", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Chat Integration - Rain Tomorrow Delhi", False, f"Error: {str(e)}")
            return False

    def test_chat_integration_weather_forecast_delhi_tomorrow(self):
        """Test 4: Chat integration - 'Weather forecast for Delhi tomorrow'"""
        try:
            payload = {
                "message": "Weather forecast for Delhi tomorrow",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check intent detection
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                if detected_intent != "get_weather_forecast":
                    self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", False, f"Wrong intent detected: {detected_intent}", data)
                    return False
                
                # Check location and days
                location = intent_data.get("location")
                days = intent_data.get("days", 0)
                
                if not location or "Delhi" not in location:
                    self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", False, f"Location not extracted: {location}", data)
                    return False
                
                if days != 1:
                    self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", False, f"Days parameter incorrect: {days}", data)
                    return False
                
                # Check response contains weather information
                response_text = data.get("response", "")
                weather_keywords = ["temperature", "weather", "rain", "sunny", "cloudy", "°C", "%"]
                has_weather_info = any(keyword.lower() in response_text.lower() for keyword in weather_keywords)
                
                if not has_weather_info:
                    self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", False, "Response doesn't contain weather information", data)
                    return False
                
                self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", True, f"Successfully processed weather forecast query")
                return True
            else:
                self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Chat Integration - Weather Forecast Delhi Tomorrow", False, f"Error: {str(e)}")
            return False

    def test_chat_integration_3_day_forecast_delhi(self):
        """Test 5: Chat integration - '3-day weather forecast in Delhi'"""
        try:
            payload = {
                "message": "3-day weather forecast in Delhi",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check intent detection
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                if detected_intent != "get_weather_forecast":
                    self.log_test("Chat Integration - 3-Day Forecast Delhi", False, f"Wrong intent detected: {detected_intent}", data)
                    return False
                
                # Check location and days
                location = intent_data.get("location")
                days = intent_data.get("days", 0)
                
                if not location or "Delhi" not in location:
                    self.log_test("Chat Integration - 3-Day Forecast Delhi", False, f"Location not extracted: {location}", data)
                    return False
                
                if days != 3:
                    self.log_test("Chat Integration - 3-Day Forecast Delhi", False, f"Days parameter incorrect: {days}, expected 3", data)
                    return False
                
                # Check response contains detailed daily breakdown
                response_text = data.get("response", "")
                daily_breakdown_keywords = ["today", "tomorrow", "day 1", "day 2", "day 3", "daily", "forecast"]
                has_daily_breakdown = any(keyword.lower() in response_text.lower() for keyword in daily_breakdown_keywords)
                
                if not has_daily_breakdown:
                    self.log_test("Chat Integration - 3-Day Forecast Delhi", False, "Response doesn't contain daily breakdown", data)
                    return False
                
                self.log_test("Chat Integration - 3-Day Forecast Delhi", True, f"Successfully processed 3-day forecast query with daily breakdown")
                return True
            else:
                self.log_test("Chat Integration - 3-Day Forecast Delhi", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Chat Integration - 3-Day Forecast Delhi", False, f"Error: {str(e)}")
            return False

    def test_chat_integration_weather_tomorrow_goa(self):
        """Test 6: Chat integration - 'What's the weather tomorrow in Goa'"""
        try:
            payload = {
                "message": "What's the weather tomorrow in Goa",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check intent detection
                intent_data = data.get("intent_data", {})
                detected_intent = intent_data.get("intent")
                
                if detected_intent != "get_weather_forecast":
                    self.log_test("Chat Integration - Weather Tomorrow Goa", False, f"Wrong intent detected: {detected_intent}", data)
                    return False
                
                # Check location and days
                location = intent_data.get("location")
                days = intent_data.get("days", 0)
                
                if not location or "Goa" not in location:
                    self.log_test("Chat Integration - Weather Tomorrow Goa", False, f"Location not extracted: {location}", data)
                    return False
                
                if days != 1:
                    self.log_test("Chat Integration - Weather Tomorrow Goa", False, f"Days parameter incorrect: {days}", data)
                    return False
                
                # Check response contains weather information for Goa
                response_text = data.get("response", "")
                if "Goa" not in response_text:
                    self.log_test("Chat Integration - Weather Tomorrow Goa", False, "Response doesn't mention Goa", data)
                    return False
                
                weather_keywords = ["temperature", "weather", "rain", "sunny", "cloudy", "°C", "%"]
                has_weather_info = any(keyword.lower() in response_text.lower() for keyword in weather_keywords)
                
                if not has_weather_info:
                    self.log_test("Chat Integration - Weather Tomorrow Goa", False, "Response doesn't contain weather information", data)
                    return False
                
                self.log_test("Chat Integration - Weather Tomorrow Goa", True, f"Successfully processed weather query for Goa")
                return True
            else:
                self.log_test("Chat Integration - Weather Tomorrow Goa", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Chat Integration - Weather Tomorrow Goa", False, f"Error: {str(e)}")
            return False

    def test_rain_detection_verification(self):
        """Test 7: Rain detection verification - Check API fields and thresholds"""
        try:
            # Test with a location that might have rain data
            response = requests.get(f"{BACKEND_URL}/weather/forecast?location=Mumbai&days=1", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                forecast_data = data.get("data", "")
                
                # Check if response contains rain percentage information
                rain_percentage_patterns = ["%", "chance", "probability", "rain"]
                has_rain_percentage = any(pattern in forecast_data.lower() for pattern in rain_percentage_patterns)
                
                if not has_rain_percentage:
                    self.log_test("Rain Detection Verification", False, "No rain percentage information found", data)
                    return False
                
                # Check for clear decision text (yes/no answers for tomorrow queries)
                decision_keywords = ["yes", "no", "likely", "unlikely"]
                has_clear_decision = any(keyword.lower() in forecast_data.lower() for keyword in decision_keywords)
                
                if not has_clear_decision:
                    self.log_test("Rain Detection Verification", False, "No clear rain decision found", data)
                    return False
                
                # Check temperature information is included
                temp_keywords = ["temperature", "°C", "°F", "temp"]
                has_temperature = any(keyword.lower() in forecast_data.lower() for keyword in temp_keywords)
                
                if not has_temperature:
                    self.log_test("Rain Detection Verification", False, "No temperature information found", data)
                    return False
                
                self.log_test("Rain Detection Verification", True, f"Rain detection working with proper fields and thresholds")
                return True
            else:
                self.log_test("Rain Detection Verification", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Rain Detection Verification", False, f"Error: {str(e)}")
            return False

    def test_error_handling_invalid_location(self):
        """Test 8: Error handling - Test with invalid location like 'InvalidCity123'"""
        try:
            response = requests.get(f"{BACKEND_URL}/weather/forecast?location=InvalidCity123&days=1", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if error is handled gracefully
                status = data.get("status")
                forecast_data = data.get("data", "")
                
                # Should either return error status or error message in data
                error_indicators = ["error", "couldn't", "unable", "invalid", "not found"]
                has_error_handling = (
                    status != "success" or 
                    any(indicator in forecast_data.lower() for indicator in error_indicators)
                )
                
                if not has_error_handling:
                    self.log_test("Error Handling - Invalid Location", False, "Invalid location not handled properly", data)
                    return False
                
                self.log_test("Error Handling - Invalid Location", True, f"Invalid location handled gracefully")
                return True
            else:
                # HTTP error is also acceptable for invalid location
                self.log_test("Error Handling - Invalid Location", True, f"Invalid location returned HTTP {response.status_code}")
                return True
                
        except Exception as e:
            self.log_test("Error Handling - Invalid Location", False, f"Error: {str(e)}")
            return False

    def test_response_format_verification_tomorrow_query(self):
        """Test 9: Response format verification - Tomorrow-specific queries return direct yes/no answers"""
        try:
            payload = {
                "message": "Will it rain tomorrow in London",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Check for direct yes/no answer
                direct_answers = ["yes", "no", "likely", "unlikely"]
                has_direct_answer = any(answer.lower() in response_text.lower() for answer in direct_answers)
                
                if not has_direct_answer:
                    self.log_test("Response Format - Tomorrow Query", False, "No direct yes/no answer found", data)
                    return False
                
                # Check for temperature information
                temp_keywords = ["temperature", "°C", "°F"]
                has_temperature = any(keyword in response_text for keyword in temp_keywords)
                
                if not has_temperature:
                    self.log_test("Response Format - Tomorrow Query", False, "No temperature information found", data)
                    return False
                
                # Check for rain percentage
                has_percentage = "%" in response_text
                
                if not has_percentage:
                    self.log_test("Response Format - Tomorrow Query", False, "No rain percentage found", data)
                    return False
                
                self.log_test("Response Format - Tomorrow Query", True, f"Tomorrow query returns proper format with yes/no answer, temperature, and percentage")
                return True
            else:
                self.log_test("Response Format - Tomorrow Query", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Response Format - Tomorrow Query", False, f"Error: {str(e)}")
            return False

    def test_response_format_verification_multi_day_forecast(self):
        """Test 10: Response format verification - Multi-day forecasts show detailed daily breakdown"""
        try:
            payload = {
                "message": "5-day weather forecast for Paris",
                "session_id": self.session_id,
                "user_id": "test_user"
            }
            
            response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Check for daily breakdown indicators
                daily_indicators = ["today", "tomorrow", "day", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                has_daily_breakdown = any(indicator.lower() in response_text.lower() for indicator in daily_indicators)
                
                if not has_daily_breakdown:
                    self.log_test("Response Format - Multi-Day Forecast", False, "No daily breakdown found", data)
                    return False
                
                # Check for multiple temperature readings (indicating multiple days)
                temp_count = response_text.count("°C") + response_text.count("°F")
                if temp_count < 2:
                    self.log_test("Response Format - Multi-Day Forecast", False, f"Not enough temperature readings for multi-day forecast: {temp_count}", data)
                    return False
                
                # Check for detailed information (rain chances, conditions)
                detail_keywords = ["rain", "sunny", "cloudy", "chance", "%", "condition"]
                detail_count = sum(1 for keyword in detail_keywords if keyword.lower() in response_text.lower())
                
                if detail_count < 3:
                    self.log_test("Response Format - Multi-Day Forecast", False, f"Not enough detailed information: {detail_count} keywords found", data)
                    return False
                
                self.log_test("Response Format - Multi-Day Forecast", True, f"Multi-day forecast shows proper daily breakdown with detailed information")
                return True
            else:
                self.log_test("Response Format - Multi-Day Forecast", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Response Format - Multi-Day Forecast", False, f"Error: {str(e)}")
            return False

    def test_weather_cache_functionality(self):
        """Test 11: Weather cache functionality"""
        try:
            # Test cache stats endpoint
            response = requests.get(f"{BACKEND_URL}/weather/cache/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                if "status" not in data or "cache_stats" not in data:
                    self.log_test("Weather Cache Functionality", False, "Missing cache stats fields", data)
                    return False
                
                cache_stats = data.get("cache_stats", {})
                required_stats = ["total_entries", "valid_entries", "expired_entries"]
                missing_stats = [stat for stat in required_stats if stat not in cache_stats]
                
                if missing_stats:
                    self.log_test("Weather Cache Functionality", False, f"Missing cache stats: {missing_stats}", data)
                    return False
                
                self.log_test("Weather Cache Functionality", True, f"Cache stats working: {cache_stats}")
                return True
            else:
                self.log_test("Weather Cache Functionality", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Weather Cache Functionality", False, f"Error: {str(e)}")
            return False

    def test_weather_api_key_configuration(self):
        """Test 12: Weather API key configuration via health endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check weather integration section
                weather_integration = data.get("weather_integration", {})
                
                if not weather_integration:
                    self.log_test("Weather API Key Configuration", False, "No weather integration section in health check", data)
                    return False
                
                # Check provider
                if weather_integration.get("provider") != "Tomorrow.io":
                    self.log_test("Weather API Key Configuration", False, f"Wrong provider: {weather_integration.get('provider')}", data)
                    return False
                
                # Check API key configuration
                api_key_configured = weather_integration.get("api_key_configured", False)
                if not api_key_configured:
                    self.log_test("Weather API Key Configuration", False, "Tomorrow.io API key not configured", data)
                    return False
                
                # Check status
                status = weather_integration.get("status")
                if status != "ready":
                    self.log_test("Weather API Key Configuration", False, f"Weather integration status: {status}", data)
                    return False
                
                # Check supported intents
                supported_intents = weather_integration.get("supported_intents", [])
                expected_intents = ["get_current_weather", "get_weather_forecast", "get_air_quality_index", "get_weather_alerts", "get_sun_times"]
                missing_intents = [intent for intent in expected_intents if intent not in supported_intents]
                
                if missing_intents:
                    self.log_test("Weather API Key Configuration", False, f"Missing weather intents: {missing_intents}", data)
                    return False
                
                self.log_test("Weather API Key Configuration", True, f"Weather integration properly configured with Tomorrow.io API")
                return True
            else:
                self.log_test("Weather API Key Configuration", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Weather API Key Configuration", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all weather forecast tests"""
        print("🌦️ Starting Comprehensive Weather Forecast Backend Testing...")
        print("=" * 80)
        
        tests = [
            self.test_direct_weather_forecast_api_1_day,
            self.test_direct_weather_forecast_api_3_days,
            self.test_chat_integration_rain_tomorrow_delhi,
            self.test_chat_integration_weather_forecast_delhi_tomorrow,
            self.test_chat_integration_3_day_forecast_delhi,
            self.test_chat_integration_weather_tomorrow_goa,
            self.test_rain_detection_verification,
            self.test_error_handling_invalid_location,
            self.test_response_format_verification_tomorrow_query,
            self.test_response_format_verification_multi_day_forecast,
            self.test_weather_cache_functionality,
            self.test_weather_api_key_configuration
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
                print(f"❌ CRITICAL ERROR in {test.__name__}: {e}")
                failed += 1
            
            # Small delay between tests
            time.sleep(0.5)
        
        print("=" * 80)
        print(f"🌦️ Weather Forecast Testing Complete!")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed / (passed + failed) * 100):.1f}%")
        
        if failed == 0:
            print("🎉 ALL WEATHER FORECAST TESTS PASSED!")
        else:
            print("⚠️ Some tests failed. Check the details above.")
        
        return passed, failed

if __name__ == "__main__":
    tester = WeatherBackendTester()
    tester.run_all_tests()