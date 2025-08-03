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
    """Apply friendly current weather template with detailed bullet points"""
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
    
    # Get comfort level based on temperature
    comfort_level = ""
    if temperature != "N/A":
        temp_val = float(temperature)
        if temp_val < 0:
            comfort_level = "❄️ **Freezing conditions** - Bundle up with heavy winter clothing!"
        elif temp_val < 10:
            comfort_level = "🧥 **Cold weather** - Wear a warm jacket and consider gloves"
        elif temp_val < 20:
            comfort_level = "🌡️ **Cool temperature** - Light jacket or sweater recommended"
        elif temp_val < 25:
            comfort_level = "👕 **Pleasant weather** - Perfect for outdoor activities"
        elif temp_val < 30:
            comfort_level = "☀️ **Warm conditions** - Light clothing and stay hydrated"
        else:
            comfort_level = "🔥 **Hot weather** - Stay cool, drink plenty of water, and avoid prolonged sun exposure"
    
    # Wind comfort assessment
    wind_comfort = ""
    if wind_speed != "N/A":
        wind_val = float(wind_speed)
        if wind_val < 5:
            wind_comfort = "🍃 **Calm winds** - Barely noticeable breeze, perfect for outdoor dining"
        elif wind_val < 15:
            wind_comfort = "🌬️ **Light breeze** - Pleasant wind conditions, ideal for walking"
        elif wind_val < 25:
            wind_comfort = "💨 **Moderate winds** - Noticeable breeze, secure loose items"
        else:
            wind_comfort = "🌪️ **Strong winds** - Windy conditions, be cautious of flying debris"
    
    # Humidity comfort
    humidity_comfort = ""
    if humidity != "N/A":
        humidity_val = float(humidity)
        if humidity_val < 30:
            humidity_comfort = "🏜️ **Low humidity** - Dry air, consider moisturizing and staying hydrated"
        elif humidity_val < 60:
            humidity_comfort = "✨ **Comfortable humidity** - Pleasant moisture levels in the air"
        else:
            humidity_comfort = "💧 **High humidity** - Muggy conditions, may feel warmer than actual temperature"
    
    # Enhanced current weather template with detailed bullet points
    response = (
        f"🌤️ **Current Weather Report for {location}**\n\n"
        f"Hey {username or 'there'}! Here's your detailed current weather conditions:\n\n"
        f"**📊 Temperature Details:**\n"
        f"• 🌡️ **Current Temperature:** {temperature}°C\n"
        f"• 🤔 **Feels Like:** {feels_like}°C (accounting for wind chill and humidity)\n"
        f"• {comfort_level}\n\n"
        f"**🌤️ Weather Conditions:**\n"
        f"• ☁️ **Sky Condition:** {condition}\n"
        f"• 💧 **Humidity Level:** {humidity}% - {humidity_comfort}\n"
        f"• 🌬️ **Wind Speed:** {wind_speed} km/h - {wind_comfort}\n\n"
        f"**💡 Weather Tips:**\n"
        f"• 👔 **Clothing Suggestion:** Based on current conditions, dress appropriately for the temperature and wind\n"
        f"• ⏰ **Best Time:** Current conditions are perfect for checking what's coming up!\n"
        f"• 🔮 **Planning Ahead:** Would you like me to share tomorrow's detailed forecast as well?\n\n"
        f"💬 Feel free to ask me about the extended forecast, air quality, or any specific weather concerns! 😊"
    )
    
    return response

async def get_weather_forecast(location: str, days: int = 3, username: str = None, conversation_context: str = None) -> Optional[str]:
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
        # Re-apply friendly template with username and context for cached results
        return _apply_forecast_template(cached_result.get('raw_data', {}), location, days, username, conversation_context)

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
            temp_max = values.get("temperatureMax", "N/A")
            temp_min = values.get("temperatureMin", "N/A")
            humidity = values.get("humidityAvg", "N/A")
            wind_speed = values.get("windSpeedAvg", "N/A")
            
            # Check if it will rain tomorrow - using rain intensity, accumulation, and probability
            will_rain = (rain_intensity > 0.5 or 
                        rain_accumulation > 0.5 or
                        rain_chance > 50 or 
                        condition_code in [4000, 4001, 4200, 4201, 8000])
            
            # Get tomorrow's date for display
            tomorrow_date = datetime.now() + timedelta(days=1)
            tomorrow_formatted = tomorrow_date.strftime("%A, %B %d, %Y")
            
            # Check conversation context for previous weather questions
            context_reference = ""
            if conversation_context and any(phrase in conversation_context.lower() for phrase in ["weather", "forecast", "rain", "temperature"]):
                context_reference = "\n💭 **Following up on your weather inquiry:** "
            
            # Enhanced rain tomorrow template with comprehensive bullet points
            if will_rain:
                response = (
                    f"☔ **Rain Expected Tomorrow in {actual_location}**{context_reference}\n\n"
                    f"Hey {username or 'friend'}! Yes, rain is likely tomorrow ({tomorrow_formatted}). Here are the detailed conditions:\n\n"
                    f"**🌧️ Rain Forecast Details:**\n"
                    f"• ☔ **Rain Probability:** {rain_chance}% chance of precipitation\n"
                    f"• 💧 **Rain Intensity:** {'Light' if rain_intensity < 2 else 'Moderate' if rain_intensity < 5 else 'Heavy'} rainfall expected\n"
                    f"• 🌊 **Accumulation:** Expected rainfall of {rain_accumulation:.1f}mm\n"
                    f"• ⏰ **Duration:** Intermittent showers likely throughout the day\n\n"
                    f"**🌡️ Temperature & Conditions:**\n"
                    f"• 🌡️ **Temperature Range:** High {int(temp_max) if temp_max != 'N/A' else 'N/A'}°C / Low {int(temp_min) if temp_min != 'N/A' else 'N/A'}°C\n"
                    f"• 💧 **Humidity:** {int(humidity) if humidity != 'N/A' else 'N/A'}% - Will feel muggy due to rain\n"
                    f"• 🌬️ **Wind:** {wind_speed if wind_speed != 'N/A' else 'N/A'} km/h - May affect umbrella use\n\n"
                    f"**☂️ Tomorrow's Rain Preparation Guide:**\n"
                    f"• 🌂 **Essential Item:** Don't forget your umbrella or raincoat!\n"
                    f"• 👟 **Footwear:** Wear waterproof shoes or boots to stay dry\n"
                    f"• 🚗 **Driving:** Allow extra time for travel due to wet road conditions\n"
                    f"• 📱 **Stay Updated:** Check weather updates as conditions may change\n"
                    f"• 🏠 **Indoor Plans:** Consider backup indoor activities just in case\n\n"
                    f"💡 **Pro Tips:** Plan your outdoor activities for early morning or late evening when rain might be lighter. Would you like me to set a rain reminder for tomorrow morning? 🌧️"
                )
            else:
                response = (
                    f"☀️ **No Rain Expected Tomorrow in {actual_location}**{context_reference}\n\n"
                    f"Great news {username or 'friend'}! It should stay dry tomorrow ({tomorrow_formatted}). Here are the conditions:\n\n"
                    f"**🌤️ Clear Weather Details:**\n"
                    f"• ☀️ **Rain Probability:** Only {rain_chance}% chance of precipitation - Very unlikely!\n"
                    f"• 🌤️ **Sky Conditions:** Mostly clear to partly cloudy skies expected\n"
                    f"• ☔ **Dry Day:** No significant rainfall anticipated\n"
                    f"• 🌈 **Perfect Day:** Great conditions for outdoor activities\n\n"
                    f"**🌡️ Temperature & Conditions:**\n"
                    f"• 🌡️ **Temperature Range:** High {int(temp_max) if temp_max != 'N/A' else 'N/A'}°C / Low {int(temp_min) if temp_min != 'N/A' else 'N/A'}°C\n"
                    f"• 💧 **Humidity:** {int(humidity) if humidity != 'N/A' else 'N/A'}% - Comfortable moisture levels\n"
                    f"• 🌬️ **Wind:** {wind_speed if wind_speed != 'N/A' else 'N/A'} km/h - Pleasant breeze conditions\n\n"
                    f"**☀️ Perfect Weather Activity Guide:**\n"
                    f"• 🚶‍♂️ **Outdoor Activities:** Perfect day for walks, hiking, or sports\n"
                    f"• 🧺 **Picnic Weather:** Ideal conditions for outdoor dining or barbecues\n"
                    f"• 📸 **Photography:** Great lighting for outdoor photography\n"
                    f"• 🚲 **Exercise:** Perfect for cycling, jogging, or other outdoor fitness\n"
                    f"• 🌻 **Gardening:** Excellent day for garden work or outdoor projects\n\n"
                    f"💡 **Enjoy Your Day:** Take advantage of the beautiful weather! Would you like me to check the extended forecast to help you plan more activities? 😄"
                )
            
            # Add follow-up action suggestion
            response += f"\n\n🔮 **Want More Details?** Ask me about the weekly forecast, air quality, or sunset times for tomorrow!"
            
            # Cache the result
            cache[cache_key] = {
                'data': response,
                'raw_data': raw_forecast_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return response

        # Regular forecast display for multiple days
        result = _apply_forecast_template(raw_forecast_data, actual_location, days, username, conversation_context)

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
    """Apply detailed forecast template with comprehensive bullet points"""
    forecasts = raw_data.get("forecasts", [])
    
    if not forecasts:
        return f"⚠️ No forecast data available for '{location}'."
    
    # Build detailed forecast with bullet points
    forecast_details = ""
    
    for i, day_data in enumerate(forecasts):
        date_str = day_data["time"].split("T")[0]
        date_obj = datetime.fromisoformat(date_str)
        day_name = date_obj.strftime("%A")
        day_date = date_obj.strftime("%B %d, %Y")
        
        values = day_data["values"]
        temp_max = values.get("temperatureMax", "N/A")
        temp_min = values.get("temperatureMin", "N/A")
        temp_avg = values.get("temperatureAvg", "N/A")
        rain_chance = values.get("precipitationProbabilityAvg", 0)
        humidity = values.get("humidityAvg", "N/A")
        wind_speed = values.get("windSpeedAvg", "N/A")
        condition_code = values.get("weatherCodeMax", 1001)

        condition_map = {
            0: "❓ Unknown",
            1000: "☀️ Clear Skies",
            1100: "🌤️ Mostly Clear",
            1101: "⛅ Partly Cloudy", 
            1102: "☁️ Cloudy",
            1001: "☁️ Cloudy",
            2000: "🌫️ Foggy",
            4000: "🌧️ Light Rain",
            4001: "🌦️ Rainy",
            4200: "🌧️ Light Rain",
            4201: "🌧️ Heavy Rain",
            5000: "❄️ Snowy",
            5001: "❄️ Light Snow",
            5100: "🌨️ Light Snow",
            5101: "❄️ Heavy Snow",
            6000: "🌧️ Freezing Drizzle",
            8000: "⛈️ Thunderstorms"
        }
        condition_emoji = condition_map.get(condition_code, "🌥️")

        if i == 0:
            day_label = "Today"
            time_reference = "throughout the day"
        elif i == 1:
            day_label = "Tomorrow"
            time_reference = "during the day"
        else:
            day_label = day_name
            time_reference = "during the day"

        # Temperature analysis
        temp_analysis = ""
        if temp_max != "N/A" and temp_min != "N/A":
            temp_range = int(temp_max) - int(temp_min)
            if temp_range > 15:
                temp_analysis = "🌡️ **Large temperature swing** - Dress in layers"
            elif temp_range > 10:
                temp_analysis = "🌡️ **Moderate temperature change** - Consider layered clothing"
            else:
                temp_analysis = "🌡️ **Stable temperatures** - Consistent conditions all day"

        # Rain analysis
        rain_analysis = ""
        if rain_chance >= 80:
            rain_analysis = "☔ **High rain probability** - Definitely bring an umbrella!"
        elif rain_chance >= 50:
            rain_analysis = "🌦️ **Moderate rain chance** - Keep an umbrella handy"
        elif rain_chance >= 20:
            rain_analysis = "⛅ **Low rain possibility** - Light rain possible, but unlikely"
        else:
            rain_analysis = "☀️ **Dry conditions expected** - No rain concerns"

        # Activity recommendations
        activity_rec = ""
        if condition_code == 1000 and rain_chance < 20:
            activity_rec = "🏃‍♂️ **Perfect for outdoor activities** - Great day for sports, picnics, or walks"
        elif rain_chance > 70:
            activity_rec = "🏠 **Indoor day recommended** - Good time for indoor activities"
        elif condition_code in [4000, 4001, 4200, 4201]:
            activity_rec = "☔ **Rainy day activities** - Museums, shopping, or cozy indoor time"
        else:
            activity_rec = "🚶‍♂️ **Mixed outdoor conditions** - Check weather before heading out"

        forecast_details += (
            f"**📅 {day_label} ({day_date}):**\n"
            f"• 🌤️ **Weather Condition:** {condition_emoji} {condition_map.get(condition_code, 'Mixed conditions')} {time_reference}\n"
            f"• 🌡️ **Temperature Range:** High {int(temp_max) if temp_max != 'N/A' else 'N/A'}°C / Low {int(temp_min) if temp_min != 'N/A' else 'N/A'}°C"
        )
        
        if temp_avg != "N/A":
            forecast_details += f" (Average: {int(temp_avg)}°C)\n"
        else:
            forecast_details += "\n"
            
        forecast_details += (
            f"• ☔ **Rain Probability:** {int(rain_chance)}% chance of precipitation\n"
        )
        
        if humidity != "N/A":
            forecast_details += f"• 💧 **Humidity Level:** {int(humidity)}% - "
            humidity_val = float(humidity)
            if humidity_val < 40:
                forecast_details += "Dry conditions\n"
            elif humidity_val < 70:
                forecast_details += "Comfortable moisture levels\n"
            else:
                forecast_details += "High humidity, may feel muggy\n"
        
        if wind_speed != "N/A":
            forecast_details += f"• 🌬️ **Wind Speed:** {wind_speed} km/h - "
            wind_val = float(wind_speed)
            if wind_val < 10:
                forecast_details += "Light breeze\n"
            elif wind_val < 20:
                forecast_details += "Moderate winds\n"
            else:
                forecast_details += "Breezy conditions\n"
        
        forecast_details += (
            f"• 🧠 **Analysis:** {temp_analysis}\n"
            f"• 🌧️ **Rain Outlook:** {rain_analysis}\n"
            f"• 🎯 **Activity Suggestion:** {activity_rec}\n\n"
        )

    # Enhanced forecast template with comprehensive details
    response = (
        f"📅 **{days}-Day Weather Forecast for {location}**\n\n"
        f"Hi {username or 'there'}! Here's your comprehensive weather forecast with all the details you need:\n\n"
        f"{forecast_details}"
        f"**🌟 Additional Weather Tips:**\n"
        f"• 📱 **Stay Updated:** Weather conditions can change, so check back for updates\n"
        f"• 🧥 **Clothing Guide:** Plan your outfits based on temperature ranges and rain chances\n"
        f"• 🚗 **Travel Planning:** Consider weather conditions for your daily commute and activities\n"
        f"• ⏰ **Best Times:** Plan outdoor activities during clear weather windows\n\n"
        f"💬 Need more specific weather details like air quality, sunrise times, or weather alerts? Just ask! 😊"
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