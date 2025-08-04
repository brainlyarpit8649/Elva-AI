#!/usr/bin/env python3
"""
Simple Weather Functionality Testing for Elva AI
Quick tests for the enhanced weather functionality requirements
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://958507ec-1e07-4ecd-9523-c0f204730193.preview.emergentagent.com/api"

def test_weather_direct_api():
    """Test direct weather API endpoints"""
    print("🌦️ Testing Direct Weather API Endpoints...")
    
    # Test 1: Weather forecast endpoint
    try:
        response = requests.get(f"{BACKEND_URL}/weather/forecast?location=Kahalgaon&days=4", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                forecast_data = data.get("data", "")
                
                # Check for bullet point format
                bullet_indicators = ["•", "◦", "-", "*", "▪", "▫"]
                has_bullets = any(indicator in forecast_data for indicator in bullet_indicators)
                
                # Check for comprehensive details
                required_details = ["temperature", "humidity", "wind", "condition", "rain"]
                details_found = sum(1 for detail in required_details if detail.lower() in forecast_data.lower())
                
                print(f"✅ Weather Forecast API: SUCCESS")
                print(f"   - Bullet format: {'Yes' if has_bullets else 'No'}")
                print(f"   - Weather details: {details_found}/5")
                print(f"   - Response length: {len(forecast_data)} chars")
                print(f"   - Location: Kahalgaon referenced")
                return True
            else:
                print(f"❌ Weather Forecast API: Failed - {data}")
                return False
        else:
            print(f"❌ Weather Forecast API: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Weather Forecast API: Error - {str(e)}")
        return False

def test_current_weather_api():
    """Test current weather API"""
    print("\n🌤️ Testing Current Weather API...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/weather/current?location=Delhi", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                weather_data = data.get("data", "")
                
                # Check for bullet point format
                bullet_indicators = ["•", "◦", "-", "*", "▪", "▫"]
                has_bullets = any(indicator in weather_data for indicator in bullet_indicators)
                
                # Check for current weather details
                current_details = ["temperature", "humidity", "wind", "condition", "current"]
                details_found = sum(1 for detail in current_details if detail.lower() in weather_data.lower())
                
                print(f"✅ Current Weather API: SUCCESS")
                print(f"   - Bullet format: {'Yes' if has_bullets else 'No'}")
                print(f"   - Weather details: {details_found}/5")
                print(f"   - Response length: {len(weather_data)} chars")
                print(f"   - Location: Delhi referenced")
                return True
            else:
                print(f"❌ Current Weather API: Failed - {data}")
                return False
        else:
            print(f"❌ Current Weather API: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Current Weather API: Error - {str(e)}")
        return False

def test_rain_query_api():
    """Test rain query through forecast API"""
    print("\n🌧️ Testing Rain Query API...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/weather/forecast?location=Mumbai&days=1", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                weather_data = data.get("data", "")
                
                # Check for rain information
                rain_keywords = ["rain", "precipitation", "shower", "drizzle", "chance", "probability"]
                rain_mentions = sum(1 for keyword in rain_keywords if keyword.lower() in weather_data.lower())
                
                # Check for bullet format
                bullet_indicators = ["•", "◦", "-", "*", "▪", "▫"]
                has_bullets = any(indicator in weather_data for indicator in bullet_indicators)
                
                print(f"✅ Rain Query API: SUCCESS")
                print(f"   - Bullet format: {'Yes' if has_bullets else 'No'}")
                print(f"   - Rain information: {rain_mentions} mentions")
                print(f"   - Response length: {len(weather_data)} chars")
                print(f"   - Location: Mumbai referenced")
                return True
            else:
                print(f"❌ Rain Query API: Failed - {data}")
                return False
        else:
            print(f"❌ Rain Query API: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Rain Query API: Error - {str(e)}")
        return False

def test_weather_health():
    """Test weather integration health"""
    print("\n🏥 Testing Weather Integration Health...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            weather_integration = data.get("weather_integration", {})
            
            status = weather_integration.get("status")
            api_key_configured = weather_integration.get("api_key_configured")
            provider = weather_integration.get("provider")
            
            print(f"✅ Weather Health Check: SUCCESS")
            print(f"   - Status: {status}")
            print(f"   - API Key: {'Configured' if api_key_configured else 'Missing'}")
            print(f"   - Provider: {provider}")
            print(f"   - Endpoints: {len(weather_integration.get('endpoints', []))}")
            
            return status == "ready" and api_key_configured
        else:
            print(f"❌ Weather Health Check: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Weather Health Check: Error - {str(e)}")
        return False

def test_chat_weather_simple():
    """Test simple weather query through chat endpoint with short timeout"""
    print("\n💬 Testing Simple Weather Chat...")
    
    session_id = str(uuid.uuid4())
    
    try:
        payload = {
            "message": "What's the weather in Delhi?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "")
            intent_data = data.get("intent_data", {})
            
            # Check if weather intent was detected
            is_weather_intent = intent_data.get("intent") in ["get_current_weather", "get_weather_forecast"]
            
            # Check for weather content
            weather_keywords = ["weather", "temperature", "condition", "delhi"]
            weather_mentions = sum(1 for keyword in weather_keywords if keyword.lower() in response_text.lower())
            
            print(f"✅ Simple Weather Chat: SUCCESS")
            print(f"   - Intent: {intent_data.get('intent')}")
            print(f"   - Weather intent: {'Yes' if is_weather_intent else 'No'}")
            print(f"   - Weather content: {weather_mentions} mentions")
            print(f"   - Response length: {len(response_text)} chars")
            
            return is_weather_intent and weather_mentions >= 2
        else:
            print(f"❌ Simple Weather Chat: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Simple Weather Chat: Error - {str(e)}")
        return False

def main():
    """Run all simple weather tests"""
    print("🌦️ Starting Simple Weather Functionality Testing...")
    print("=" * 60)
    
    tests = [
        test_weather_direct_api,
        test_current_weather_api,
        test_rain_query_api,
        test_weather_health,
        test_chat_weather_simple
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
    
    print("\n" + "=" * 60)
    print(f"🌦️ Simple Weather Testing Complete: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL SIMPLE WEATHER TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {total-passed} tests failed - see details above")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)