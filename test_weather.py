#!/usr/bin/env python3
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, '/app/backend')

# Load environment variables
load_dotenv('/app/backend/.env')
print(f"API Key loaded: {os.environ.get('TOMORROW_API_KEY', 'NOT FOUND')}")

# Import the weather function
from weather_service_tomorrow import get_weather_forecast

async def test_weather():
    print("Testing weather forecast function...")
    
    # Test tomorrow's weather in Delhi
    result = await get_weather_forecast("Delhi", 1)
    print("=" * 60)
    print("RESULT for 'Will it rain tomorrow in Delhi' (days=1):")
    print(result)
    print("=" * 60)
    
    # Test 3-day forecast
    result3 = await get_weather_forecast("Delhi", 3)
    print("RESULT for '3-day forecast in Delhi':")
    print(result3)
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_weather())