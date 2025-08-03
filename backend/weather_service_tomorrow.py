import os
import aiohttp
import logging
from typing import Optional
import json
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

TOMORROW_API_KEY = os.environ.get("TOMORROW_API_KEY", "")
BASE_URL_REALTIME = "https://api.tomorrow.io/v4/weather/realtime"
BASE_URL_FORECAST = "https://api.tomorrow.io/v4/weather/forecast"
BASE_URL_AIRQUALITY = "https://api.tomorrow.io/v4/weather/realtime"
UNITS = "metric"  # 'imperial' for Fahrenheit

# Simple in-memory cache with 5-minute expiry
cache = {}
CACHE_TTL = 300  # 5 minutes in seconds

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid (within 5 minutes)"""
    if cache_entry is None:
        return False
    cache_time = cache_entry.get('timestamp')
    if not cache_time:
        return False
    
    cache_datetime = datetime.fromisoformat(cache_time)
    now = datetime.utcnow()
    return (now - cache_datetime).total_seconds() < CACHE_TTL

def get_cache_key(operation: str, location: str) -> str:
    """Generate cache key for location and operation"""
    return f"{operation}_{location.lower().strip().replace(' ', '_')}"

async def get_current_weather(location: str) -> Optional[str]:
    """
    Fetches current weather using Tomorrow.io API with 5-minute caching
    """
    if not TOMORROW_API_KEY:
        return "⚠️ Tomorrow.io API key not set."

    # Check cache first
    cache_key = get_cache_key("current_weather", location)
    cached_result = cache.get(cache_key)
    if cached_result and is_cache_valid(cached_result):
        logger.info(f"🚀 Returning cached current weather for {location}")
        return cached_result['data']

    try:
        params = {
            "location": location,
            "apikey": TOMORROW_API_KEY,
            "units": UNITS
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL_REALTIME, params=params) as resp:
                if resp.status != 200:
                    return f"❌ Couldn't fetch weather data for '{location}'. Status: {resp.status}"
                
                data = await resp.json()

        if "data" not in data:
            return f"❌ Couldn't fetch weather data for '{location}'."

        weather = data["data"]["values"]
        location_data = data["data"].get("location", {})
        actual_location = location_data.get("name", location.title())
        
        temp = weather.get("temperature", "N/A")
        feels_like = weather.get("temperatureApparent", "N/A")
        humidity = weather.get("humidity", "N/A")
        wind_speed = weather.get("windSpeed", "N/A")
        visibility = weather.get("visibility", "N/A")
        uv_index = weather.get("uvIndex", "N/A")
        pressure = weather.get("pressureSeaLevel", "N/A")
        condition = weather.get("weatherCode", "Unknown")

        condition_map = {
            0: "❓ Unknown",
            1000: "☀️ Clear",
            1100: "🌤️ Mostly Clear", 
            1101: "⛅ Partly Cloudy",
            1102: "☁️ Cloudy",
            1001: "☁️ Cloudy",
            2000: "🌫️ Fog",
            2100: "🌫️ Light Fog",
            4000: "🌧️ Drizzle",
            4001: "🌦️ Rain",
            4200: "🌧️ Light Rain",
            4201: "🌧️ Heavy Rain",
            5000: "❄️ Snow",
            5001: "❄️ Flurries",
            5100: "🌨️ Light Snow",
            5101: "❄️ Heavy Snow",
            6000: "🌧️ Freezing Drizzle",
            6001: "🧊 Freezing Rain",
            6200: "🧊 Light Freezing Rain",
            6201: "🧊 Heavy Freezing Rain",
            7000: "🧊 Ice Pellets",
            7101: "🧊 Heavy Ice Pellets",
            7102: "🧊 Light Ice Pellets",
            8000: "⛈️ Thunderstorm"
        }
        condition_text = condition_map.get(condition, "🌥️ Moderate conditions")

        result = f"🌦️ **Weather in {actual_location}:**\n"
        result += f"- 🌡️ **Temperature:** {temp}°C (Feels like {feels_like}°C)\n"
        result += f"- **Condition:** {condition_text}\n"
        result += f"- 💧 **Humidity:** {humidity}%\n" 
        result += f"- 🌬️ **Wind:** {wind_speed} km/h\n"
        
        if visibility != "N/A":
            result += f"- 👁️ **Visibility:** {visibility} km\n"
        if uv_index != "N/A":
            result += f"- ☀️ **UV Index:** {uv_index}\n"
        if pressure != "N/A":
            result += f"- 🌡️ **Pressure:** {pressure:.1f} hPa\n"

        # Cache the result
        cache[cache_key] = {
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Successfully fetched and cached current weather for {location}")
        return result

    except Exception as e:
        logger.error(f"❌ Error fetching current weather: {e}")
        return f"⚠️ Unable to fetch weather information for '{location}' right now. Error: {str(e)}"

async def get_weather_forecast(location: str, days: int = 3) -> Optional[str]:
    """
    Fetches weather forecast for next N days (up to 7) using Tomorrow.io API
    and returns a friendly, readable summary with enhanced rain detection.
    """
    if not TOMORROW_API_KEY:
        return "⚠️ Tomorrow.io API key not set."

    try:
        params = {
            "location": location,
            "timesteps": "1d",
            "units": UNITS,
            "apikey": TOMORROW_API_KEY
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL_FORECAST, params=params) as resp:
                data = await resp.json()

        if resp.status != 200 or "data" not in data or "timelines" not in data["data"]:
            return f"❌ Couldn't fetch forecast for '{location}'."

        forecasts = data["data"]["timelines"]["daily"]
        if not forecasts:
            return f"⚠️ No forecast data available for '{location}'."

        message = f"📅 Weather Forecast for {location.title()} (next {days} days):\n"
        rain_tomorrow = False

        for i, day_data in enumerate(forecasts[:days]):
            date = day_data["time"].split("T")[0]
            values = day_data["values"]

            temp = values.get("temperatureAvg", "N/A")
            rain_chance = values.get("precipitationProbabilityAvg", 0)
            precip = values.get("precipitationType", 0)
            condition_code = values.get("weatherCodeMax", 1001)

            condition_map = {
                1000: "☀️ Clear",
                1100: "🌤️ Mostly Clear",
                1101: "⛅ Partly Cloudy",
                1102: "☁️ Cloudy",
                4000: "🌧️ Light Rain",
                4200: "🌧️ Rain",
                5001: "❄️ Snow",
                8000: "⛈️ Thunderstorm"
            }
            condition = condition_map.get(condition_code, "🌥️ Moderate conditions")

            message += f"\n📌 {date}: {condition}, Avg Temp: {temp}°C, 🌧️ Rain chance: {rain_chance}%"

            # Detect if tomorrow (index 1) has rain
            if i == 1 and (precip in [4000, 4200, 8000] or rain_chance > 50):
                rain_tomorrow = True

        # If query is specifically "will it rain tomorrow"
        if days == 1 or "tomorrow" in location.lower():
            return (
                f"🌧️ Yes, rain is likely tomorrow in {location.title()}."
                if rain_tomorrow else
                f"☀️ No, rain is unlikely tomorrow in {location.title()}."
            )

        return message

    except Exception as e:
        logger.error(f"❌ Error fetching forecast: {e}")
        return "⚠️ Unable to fetch forecast information right now."

async def get_air_quality_index(location: str) -> Optional[str]:
    """
    Fetches air quality index using Tomorrow.io API with 5-minute caching
    """
    if not TOMORROW_API_KEY:
        return "⚠️ Tomorrow.io API key not set."

    # Check cache first
    cache_key = get_cache_key("air_quality", location)
    cached_result = cache.get(cache_key)
    if cached_result and is_cache_valid(cached_result):
        logger.info(f"🚀 Returning cached air quality for {location}")
        return cached_result['data']

    try:
        params = {
            "location": location,
            "apikey": TOMORROW_API_KEY,
            "units": UNITS,
            "fields": ["particulateMatter25", "particulateMatter10", "pollutantO3", "pollutantNO2", "pollutantCO", "pollutantSO2"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL_AIRQUALITY, params=params) as resp:
                if resp.status != 200:
                    return f"❌ Couldn't fetch air quality data for '{location}'. Status: {resp.status}"
                
                data = await resp.json()

        if "data" not in data:
            return f"❌ Couldn't fetch air quality data for '{location}'."

        values = data["data"]["values"]
        location_data = data["data"].get("location", {})
        actual_location = location_data.get("name", location.title())
        
        pm25 = values.get("particulateMatter25", "N/A")
        pm10 = values.get("particulateMatter10", "N/A") 
        o3 = values.get("pollutantO3", "N/A")
        no2 = values.get("pollutantNO2", "N/A")
        co = values.get("pollutantCO", "N/A")
        so2 = values.get("pollutantSO2", "N/A")

        # Calculate AQI level based on PM2.5 (simplified)
        aqi_level = "❓ Unknown"
        aqi_emoji = "❓"
        if pm25 != "N/A":
            if pm25 <= 12:
                aqi_level = "Good"
                aqi_emoji = "🟢"
            elif pm25 <= 35.4:
                aqi_level = "Moderate"
                aqi_emoji = "🟡"
            elif pm25 <= 55.4:
                aqi_level = "Unhealthy for Sensitive Groups"
                aqi_emoji = "🟠"
            elif pm25 <= 150.4:
                aqi_level = "Unhealthy"
                aqi_emoji = "🔴"
            else:
                aqi_level = "Hazardous"
                aqi_emoji = "🟣"

        result = f"🌬️ **Air Quality in {actual_location}:**\n"
        result += f"- {aqi_emoji} **Overall Level:** {aqi_level}\n\n"
        result += f"**Pollutant Levels:**\n"
        
        if pm25 != "N/A":
            result += f"- 🔬 **PM2.5:** {pm25:.1f} µg/m³\n"
        if pm10 != "N/A":
            result += f"- 🔬 **PM10:** {pm10:.1f} µg/m³\n"
        if o3 != "N/A":
            result += f"- 💨 **Ozone (O₃):** {o3:.1f} µg/m³\n"
        if no2 != "N/A":
            result += f"- 🏭 **Nitrogen Dioxide (NO₂):** {no2:.1f} µg/m³\n"
        if co != "N/A":
            result += f"- 🚗 **Carbon Monoxide (CO):** {co:.1f} mg/m³\n"
        if so2 != "N/A":
            result += f"- 🏭 **Sulfur Dioxide (SO₂):** {so2:.1f} µg/m³\n"

        # Cache the result
        cache[cache_key] = {
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Successfully fetched and cached air quality for {location}")
        return result

    except Exception as e:
        logger.error(f"❌ Error fetching air quality: {e}")
        return f"⚠️ Unable to fetch air quality information for '{location}' right now. Error: {str(e)}"

async def get_weather_alerts(location: str) -> Optional[str]:
    """
    Fetches weather alerts/warnings - simplified implementation
    Note: Tomorrow.io doesn't have a dedicated alerts endpoint in the free tier
    """
    return f"⚠️ **Weather Alerts for {location.title()}:**\n\nWeather alerts feature requires Premium Tomorrow.io API access. For now, please check local weather services for severe weather warnings.\n\n💡 **Tip:** Use our current weather and forecast features to stay informed about conditions!"

async def get_sun_times(location: str) -> Optional[str]:
    """
    Fetches sunrise/sunset times using Tomorrow.io API with 5-minute caching
    """
    if not TOMORROW_API_KEY:
        return "⚠️ Tomorrow.io API key not set."

    # Check cache first
    cache_key = get_cache_key("sun_times", location)
    cached_result = cache.get(cache_key)
    if cached_result and is_cache_valid(cached_result):
        logger.info(f"🚀 Returning cached sun times for {location}")
        return cached_result['data']

    try:
        params = {
            "location": location,
            "apikey": TOMORROW_API_KEY,
            "units": UNITS,
            "fields": ["sunriseTime", "sunsetTime"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL_REALTIME, params=params) as resp:
                if resp.status != 200:
                    return f"❌ Couldn't fetch sun times for '{location}'. Status: {resp.status}"
                
                data = await resp.json()

        if "data" not in data:
            return f"❌ Couldn't fetch sun times for '{location}'."

        values = data["data"]["values"]
        location_data = data["data"].get("location", {})
        actual_location = location_data.get("name", location.title())
        
        sunrise = values.get("sunriseTime", "N/A")
        sunset = values.get("sunsetTime", "N/A")

        result = f"🌅 **Sun Times for {actual_location}:**\n"
        
        if sunrise != "N/A":
            # Convert ISO datetime to readable format
            try:
                sunrise_dt = datetime.fromisoformat(sunrise.replace('Z', '+00:00'))
                sunrise_time = sunrise_dt.strftime("%I:%M %p")
                result += f"- 🌅 **Sunrise:** {sunrise_time}\n"
            except:
                result += f"- 🌅 **Sunrise:** {sunrise}\n"
        
        if sunset != "N/A":
            # Convert ISO datetime to readable format
            try:
                sunset_dt = datetime.fromisoformat(sunset.replace('Z', '+00:00'))
                sunset_time = sunset_dt.strftime("%I:%M %p") 
                result += f"- 🌇 **Sunset:** {sunset_time}\n"
            except:
                result += f"- 🌇 **Sunset:** {sunset}\n"

        if sunrise != "N/A" and sunset != "N/A":
            try:
                sunrise_dt = datetime.fromisoformat(sunrise.replace('Z', '+00:00'))
                sunset_dt = datetime.fromisoformat(sunset.replace('Z', '+00:00'))
                daylight_duration = sunset_dt - sunrise_dt
                hours = int(daylight_duration.total_seconds() // 3600)
                minutes = int((daylight_duration.total_seconds() % 3600) // 60)
                result += f"- ☀️ **Daylight Duration:** {hours}h {minutes}m\n"
            except:
                pass

        # Cache the result
        cache[cache_key] = {
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Successfully fetched and cached sun times for {location}")
        return result

    except Exception as e:
        logger.error(f"❌ Error fetching sun times: {e}")
        return f"⚠️ Unable to fetch sun times for '{location}' right now. Error: {str(e)}"

async def clear_weather_cache():
    """Clear all weather cache entries"""
    global cache
    cache.clear()
    logger.info("🧹 Weather cache cleared")

def get_cache_stats():
    """Get cache statistics"""
    valid_entries = sum(1 for entry in cache.values() if is_cache_valid(entry))
    return {
        "total_entries": len(cache),
        "valid_entries": valid_entries,
        "expired_entries": len(cache) - valid_entries
    }