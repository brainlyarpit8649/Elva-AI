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

async def get_current_weather(location: str, username: str = None) -> Optional[str]:
    """
    Fetches current weather using Tomorrow.io API with friendly response template
    """
    if not TOMORROW_API_KEY:
        return "⚠️ Tomorrow.io API key not set."

    # Check cache first
    cache_key = get_cache_key("current_weather", location)
    cached_result = cache.get(cache_key)
    if cached_result and is_cache_valid(cached_result):
        logger.info(f"🚀 Returning cached current weather for {location}")
        # Re-apply friendly template with username for cached results
        return _apply_current_weather_template(cached_result.get('raw_data', {}), location, username)

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
        
        raw_weather_data = {
            "temperature": weather.get("temperature", "N/A"),
            "feels_like": weather.get("temperatureApparent", "N/A"),
            "humidity": weather.get("humidity", "N/A"),
            "wind_speed": weather.get("windSpeed", "N/A"),
            "condition_code": weather.get("weatherCode", "Unknown"),
            "actual_location": actual_location
        }

        # Apply friendly template
        result = _apply_current_weather_template(raw_weather_data, actual_location, username)

        # Cache both raw data and the friendly result
        cache[cache_key] = {
            'data': result,
            'raw_data': raw_weather_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Successfully fetched and cached current weather for {location}")
        return result

    except Exception as e:
        logger.error(f"❌ Error fetching current weather: {e}")
        return f"⚠️ Unable to fetch weather information for '{location}' right now. Error: {str(e)}"

def _apply_current_weather_template(raw_data: dict, location: str, username: str = None) -> str:
    """Apply friendly current weather template"""
    temperature = raw_data.get("temperature", "N/A")
    feels_like = raw_data.get("feels_like", "N/A") 
    humidity = raw_data.get("humidity", "N/A")
    wind_speed = raw_data.get("wind_speed", "N/A")
    condition_code = raw_data.get("condition_code", "Unknown")
    
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
    condition = condition_map.get(condition_code, "🌥️ Moderate conditions")
    
    # Friendly current weather template
    response = (
        f"🌤️ Hey {username or 'there'}! Here's the current weather in {location}:\n"
        f"- 🌡️ Temperature: {temperature}°C (Feels like {feels_like}°C)\n"
        f"- ☁️ Condition: {condition}\n"
        f"- 💧 Humidity: {humidity}%\n"
        f"- 🌬️ Wind: {wind_speed} km/h\n"
        f"Would you like me to share tomorrow's forecast too? 😊"
    )
    
    return response

async def get_weather_forecast(location: str, days: int = 3, username: str = None) -> Optional[str]:
    """
    Fetches weather forecast for next N days (up to 7) using Tomorrow.io API
    and returns a friendly, readable summary with enhanced rain detection.
    """
    if not TOMORROW_API_KEY:
        return "⚠️ Tomorrow.io API key not set."

    # Limit days to maximum 7
    days = min(days, 7)
    
    # Check cache first
    cache_key = get_cache_key(f"forecast_{days}d", location)
    cached_result = cache.get(cache_key)
    if cached_result and is_cache_valid(cached_result):
        logger.info(f"🚀 Returning cached forecast for {location}")
        # Re-apply friendly template with username for cached results
        return _apply_forecast_template(cached_result.get('raw_data', {}), location, days, username)

    try:
        params = {
            "location": location,
            "timesteps": "1d",
            "units": UNITS,
            "apikey": TOMORROW_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL_FORECAST, params=params) as resp:
                if resp.status != 200:
                    return f"❌ Couldn't fetch forecast for '{location}'. Status: {resp.status}"
                
                data = await resp.json()

        if "timelines" not in data:
            return f"❌ Couldn't fetch forecast for '{location}'."

        forecasts = data["timelines"]["daily"]
        if not forecasts:
            return f"⚠️ No forecast data available for '{location}'."

        location_data = data.get("location", {})
        actual_location = location_data.get("name", location.title())

        # Store raw forecast data
        raw_forecast_data = {
            "forecasts": forecasts[:days],
            "actual_location": actual_location,
            "days": days
        }

        # Special handling for tomorrow-specific rain queries (days=1)
        if days == 1 and len(forecasts) >= 2:
            tomorrow_data = forecasts[1]  # Index 1 is tomorrow
            values = tomorrow_data["values"]
            
            rain_chance = values.get("precipitationProbabilityAvg", 0)
            rain_intensity = values.get("rainIntensityAvg", 0)
            rain_accumulation = values.get("rainAccumulationAvg", 0)
            condition_code = values.get("weatherCodeMax", 1001)
            temp_avg = values.get("temperatureAvg", "N/A")
            
            # Check if it will rain tomorrow - using rain intensity, accumulation, and probability
            will_rain = (rain_intensity > 0.5 or 
                        rain_accumulation > 0.5 or
                        rain_chance > 50 or 
                        condition_code in [4000, 4001, 4200, 4201, 8000])
            
            # Friendly rain tomorrow template
            if will_rain:
                response = f"☔ Yes {username or 'friend'}, it looks like rain is likely tomorrow in {actual_location} with a {rain_chance}% chance of precipitation. Don't forget your umbrella! 🌧️"
            else:
                response = f"☀️ Nope, it should stay dry tomorrow in {actual_location}! Perfect weather to go out and enjoy your day! 😄"
            
            # Add follow-up action suggestion
            response += f"\n\nWould you like me to set a rain alert for tomorrow?"
            
            # Cache the result
            cache[cache_key] = {
                'data': response,
                'raw_data': raw_forecast_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return response

        # Regular forecast display for multiple days
        result = _apply_forecast_template(raw_forecast_data, actual_location, days, username)

        # Cache the result
        cache[cache_key] = {
            'data': result,
            'raw_data': raw_forecast_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Successfully fetched and cached forecast for {location}")
        return result

    except Exception as e:
        logger.error(f"❌ Error fetching forecast: {e}")
        return f"⚠️ Unable to fetch forecast information for '{location}' right now. Error: {str(e)}"

def _apply_forecast_template(raw_data: dict, location: str, days: int, username: str = None) -> str:
    """Apply friendly forecast template"""
    forecasts = raw_data.get("forecasts", [])
    
    if not forecasts:
        return f"⚠️ No forecast data available for '{location}'."
    
    # Build forecast list
    forecast_list = ""
    
    for i, day_data in enumerate(forecasts):
        date_str = day_data["time"].split("T")[0]
        date_obj = datetime.fromisoformat(date_str)
        day_name = date_obj.strftime("%A")
        
        values = day_data["values"]
        temp_max = values.get("temperatureMax", "N/A")
        temp_min = values.get("temperatureMin", "N/A")
        rain_chance = values.get("precipitationProbabilityAvg", 0)
        condition_code = values.get("weatherCodeMax", 1001)

        condition_map = {
            0: "❓ Unknown",
            1000: "☀️ Clear",
            1100: "🌤️ Mostly Clear",
            1101: "⛅ Partly Cloudy", 
            1102: "☁️ Cloudy",
            1001: "☁️ Cloudy",
            2000: "🌫️ Fog",
            4000: "🌧️ Light Rain",
            4001: "🌦️ Rain",
            4200: "🌧️ Light Rain",
            4201: "🌧️ Heavy Rain",
            5000: "❄️ Snow",
            5001: "❄️ Flurries",
            5100: "🌨️ Light Snow",
            5101: "❄️ Heavy Snow",
            6000: "🌧️ Freezing Drizzle",
            8000: "⛈️ Thunderstorm"
        }
        condition_emoji = condition_map.get(condition_code, "🌥️")

        if i == 0:
            day_label = "Today"
        elif i == 1:
            day_label = "Tomorrow"
        else:
            day_label = day_name

        if temp_max != "N/A" and temp_min != "N/A":
            temp_display = f"{int(temp_max)}°C"
        else:
            temp_display = "N/A"

        forecast_list += f"• {day_label}: {condition_emoji} {temp_display}, Rain chance {int(rain_chance)}%\n"

    # Friendly forecast template
    response = (
        f"📅 Hi {username or 'buddy'}! Here's the {days}-day weather forecast for {location}:\n"
        f"{forecast_list}\n"
        f"🌟 Tip: I can set a reminder for rainy days if you'd like! ☔"
    )
    
    return response

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