import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
import requests
from geopy.geocoders import Nominatim
import logging
from timezonefinder import TimezoneFinder
import json
import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# get weather from open meteo site
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city using a free API.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    geolocator = Nominatim(user_agent="weather_agent")
    try:
        location = geolocator.geocode(city)
        if not location:
            return {
                "status": "error",
                "error_message": f"Could not find location for '{city}'.",
            }

        api_url = os.getenv("OPEN_METEO_API_URL")
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current" : "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,cloud_cover,wind_speed_10m"
        }

        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if "current" in data:
            weather = data["current"]
            weather_code = weather["weather_code"]

            # Load weather descriptions from weathercodes.json
            try:
                with open("weather_agent/weathercodes.json", "r") as f:
                    weather_codes = json.load(f)
                weather_description = weather_codes.get(str(weather_code), "Unknown weather condition")
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error_message": "weathercodes.json file not found.",
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error_message": "Error decoding weathercodes.json.",
                }

            report = (
                f"The weather in {city} is {weather_description} with a temperature of "
                f"{weather['temperature_2m']} degrees Celsius."
                f"The apparent temperature is {weather['apparent_temperature']} degrees Celsius. "
                f"Humidity is {weather['relative_humidity_2m']}%. "
                f"Wind speed is {weather['wind_speed_10m']} m/s. "
                f"Cloud cover is {weather['cloud_cover']}%. "
                f"Precipitation is {weather['precipitation']} mm. "
                f"Rain is {weather['rain']} mm. "
                f"Showers are {weather['showers']} mm. "
                f"Snowfall is {weather['snowfall']} mm."
            )
            return {"status": "success", "report": report}
        else:
            return {
                "status": "error",
                "error_message": "Unable to retrieve weather data.",
            }
    except requests.RequestException as e:
        return {
            "status": "error",
            "error_message": f"An error occurred while fetching weather data: {e}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"An error occurred: {e}",
        }

# get current time 
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """
    try:
        location = Nominatim(user_agent="weather_agent").geocode(city)
        if not location:
            return {"status": "error", "error_message": f"Could not find location for '{city}'."}

        timezone_str = TimezoneFinder().timezone_at(lat=location.latitude, lng=location.longitude)
        if not timezone_str:
            return {"status": "error", "error_message": f"Could not determine timezone for '{city}'."}

        now = datetime.datetime.now(ZoneInfo(timezone_str))
        return {"status": "success", "current_time": now.strftime("%I:%M %p %Z")}
    except Exception as e:
        return {"status": "error", "error_message": f"An error occurred: {e}"}

# get next 7 days weather 
def get_weather_7_days(city: str) -> dict:
    """Retrieves a 7-day weather forecast for a specified city using a free API.

    Args:
        city (str): The name of the city for which to retrieve the weather forecast.

    Returns:
        dict: status and result or error message.
    """
    geolocator = Nominatim(user_agent="weather_agent")
    try:
        location = geolocator.geocode(city)
        if not location:
            return {
                "status": "error",
                "error_message": f"Could not find location for '{city}'.",
            }

        api_url = os.getenv("OPEN_METEO_API_URL")
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max",
            "timezone": "auto",
        }

        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if "daily" in data:
            daily_data = data["daily"]

            # Load weather descriptions from weathercodes.json
            try:
                with open("weather_agent/weathercodes.json", "r") as f:
                    weather_codes = json.load(f)
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error_message": "weathercodes.json file not found.",
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error_message": "Error decoding weathercodes.json.",
                }

            report = f"7-day weather forecast for {city}:\n"
            for i in range(len(daily_data["time"])):
                date = daily_data["time"][i]
                max_temp = daily_data["temperature_2m_max"][i]
                min_temp = daily_data["temperature_2m_min"][i]
                precipitation = daily_data["precipitation_sum"][i]
                rain = daily_data.get("rain_sum", [0])[i]
                snowfall = daily_data.get("snowfall_sum", [0])[i]
                wind_speed = daily_data.get("wind_speed_10m_max", [0])[i]
                uv_index = daily_data.get("uv_index_max", [0])[i]
                weather_code = daily_data["weather_code"][i]
                weather_description = weather_codes.get(str(weather_code), "Unknown weather condition")

                report += (
                    f"{date}: {weather_description}. Max Temp: {max_temp}°C, Min Temp: {min_temp}°C, "
                )
                if precipitation > 0:
                    report += f"Precipitation: {precipitation}mm, "
                if rain > 0:
                    report += f"Rain: {rain}mm, "
                if snowfall > 0:
                    report += f"Snowfall: {snowfall}mm, "
                if wind_speed > 0:
                    report += f"Wind Speed: {wind_speed}m/s, "
                if uv_index > 0:
                    report += f"UV Index: {uv_index}, "
                report = report.rstrip(", ") + "\n"

            return {"status": "success", "report": report}
        else:
            return {
                "status": "error",
                "error_message": "Unable to retrieve weather data.",
            }

    except requests.RequestException as e:
        return {
            "status": "error",
            "error_message": f"An error occurred while fetching weather data: {e}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"An error occurred: {e}",
        }



root_agent = Agent(
    name=os.getenv("AGENT_NAME"),
    model=os.getenv("MODEL_NAME"),
    description=(
        "Agent to answer questions about the time and weather of a city."
    ),
    instruction=(
        """
          < your instruction goes here >
          
        """
    ),
    tools=[get_weather, get_current_time, get_weather_7_days]
)

