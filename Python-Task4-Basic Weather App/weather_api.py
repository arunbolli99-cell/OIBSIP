import os
import requests
import urllib.parse
from PIL import Image, ImageTk
from datetime import datetime

import config_manager

# Custom exceptions for clear error propagation
class WeatherAPIException(Exception):
    """Base exception for Weather API errors."""
    pass

class InvalidAPIKeyException(WeatherAPIException):
    """Raised when the API key is invalid."""
    pass

class CityNotFoundException(WeatherAPIException):
    """Raised when the city/ZIP is not found."""
    pass

class NetworkTimeoutException(WeatherAPIException):
    """Raised when network requests timeout."""
    pass

class GeolocationException(WeatherAPIException):
    """Raised when auto-detecting location fails."""
    pass


# Directory to cache downloaded icons
CACHE_DIR = "weather_icons_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory cache for ImageTk objects
_icon_image_cache = {}

def get_current_location():
    """Detect user's current city based on active provider."""
    provider = config_manager.get_provider()
    if provider == "weatherapi":
        return "auto:ip"
        
    # OpenWeatherMap or Demo mode: resolve using ipinfo.io
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            city = data.get("city")
            country = data.get("country")
            if city:
                return f"{city},{country}" if country else city
        raise GeolocationException("Failed to get location from ipinfo.io response.")
    except requests.exceptions.RequestException as e:
        raise NetworkTimeoutException(f"Network error detecting location: {e}")
    except Exception as e:
        raise GeolocationException(f"Error auto-detecting location: {e}")

def _parse_owm_error(response):
    """Parse OWM error response and raise exception."""
    try:
        err_data = response.json()
        message = err_data.get("message", "Unknown error")
    except Exception:
        message = response.text or "Unknown error"
        
    status_code = response.status_code
    if status_code == 401:
        raise InvalidAPIKeyException("Invalid API key. Please check your OpenWeatherMap API key in settings.")
    elif status_code == 404:
        raise CityNotFoundException("Location not found. Please try a different city name or ZIP code.")
    else:
        raise WeatherAPIException(f"API Error ({status_code}): {message.capitalize()}")

def _parse_weatherapi_error(response):
    """Parse WeatherAPI.com error response and raise exception."""
    try:
        err_data = response.json()
        err_detail = err_data.get("error", {})
        code = err_detail.get("code")
        message = err_detail.get("message", "Unknown error")
    except Exception:
        code = None
        message = response.text or "Unknown error"
        
    status_code = response.status_code
    if code in (1002, 2006, 2007, 2008) or status_code in (401, 403):
        raise InvalidAPIKeyException("Invalid API key. Please check your WeatherAPI.com API key in settings.")
    elif code == 1006 or status_code == 400:
        raise CityNotFoundException("Location not found. Please try a different city name or ZIP code.")
    else:
        raise WeatherAPIException(f"API Error: {message.capitalize()} (Code {code})")

def fetch_weather_data(query, api_key, units="metric"):
    """Fetches weather data for either OpenWeatherMap or WeatherAPI.com depending on config."""
    if api_key.lower() == "demo":
        return get_mock_weather_data(query, units)
        
    if not api_key:
        raise InvalidAPIKeyException("API Key is missing. Please configure it in settings.")
        
    provider = config_manager.get_provider()
    
    if provider == "weatherapi":
        return _fetch_weatherapi_data(query, api_key, units)
    else:
        return _fetch_owm_data(query, api_key, units)

def _fetch_weatherapi_data(query, api_key, units):
    """Internal fetch for WeatherAPI.com."""
    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": api_key,
        "q": query.strip(),
        "days": 5,
        "aqi": "no",
        "alerts": "no"
    }
    try:
        res = requests.get(url, params=params, timeout=8)
        if res.status_code != 200:
            _parse_weatherapi_error(res)
        data = res.json()
        return parse_weatherapi_response(data, units)
    except requests.exceptions.Timeout:
        raise NetworkTimeoutException("Connection timed out. Please check your internet connection.")
    except requests.exceptions.ConnectionError:
        raise NetworkTimeoutException("Network connection failed. Please check your internet connection.")
    except WeatherAPIException:
        raise
    except Exception as e:
        raise WeatherAPIException(f"An unexpected error occurred: {e}")

def _fetch_owm_data(query, api_key, units):
    """Internal fetch for OpenWeatherMap."""
    # Build query params
    params = {
        "appid": api_key,
        "units": "metric" # Always fetch in metric internally, convert on UI
    }
    q_clean = query.strip()
    is_zip = q_clean.split(',')[0].strip().isdigit()
    if is_zip:
        params["zip"] = q_clean
    else:
        params["q"] = q_clean
        
    current_url = "https://api.openweathermap.org/data/2.5/weather"
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    
    try:
        curr_res = requests.get(current_url, params=params, timeout=8)
        if curr_res.status_code != 200:
            _parse_owm_error(curr_res)
        current_data = curr_res.json()
        
        fore_res = requests.get(forecast_url, params=params, timeout=8)
        if fore_res.status_code != 200:
            _parse_owm_error(fore_res)
        forecast_data = fore_res.json()
        
        return parse_owm_response(current_data, forecast_data, units)
    except requests.exceptions.Timeout:
        raise NetworkTimeoutException("Connection timed out. Please check your internet connection.")
    except requests.exceptions.ConnectionError:
        raise NetworkTimeoutException("Network connection failed. Please check your internet connection.")
    except WeatherAPIException:
        raise
    except Exception as e:
        raise WeatherAPIException(f"An unexpected error occurred: {e}")

def parse_owm_response(current_json, forecast_json, units):
    """Parses OpenWeatherMap responses into the app standard schema."""
    temp_symbol = "°C" if units == "metric" else "°F"
    speed_symbol = "m/s" if units == "metric" else "mph"
    
    main_section = current_json.get("main", {})
    wind_section = current_json.get("wind", {})
    weather_section = current_json.get("weather", [{}])[0]
    sys_section = current_json.get("sys", {})
    
    current_weather = {
        "city": current_json.get("name"),
        "country": sys_section.get("country"),
        "temp": round(main_section.get("temp", 0)),
        "feels_like": round(main_section.get("feels_like", 0)),
        "temp_min": round(main_section.get("temp_min", 0)),
        "temp_max": round(main_section.get("temp_max", 0)),
        "humidity": main_section.get("humidity", 0),
        "pressure": main_section.get("pressure", 0),
        "wind_speed": wind_section.get("speed", 0),
        "wind_deg": wind_section.get("wind_deg", 0),
        "description": weather_section.get("description", "").title(),
        "condition": weather_section.get("main", "Unknown"),
        "icon": weather_section.get("icon", "01d"),
        "dt": current_json.get("dt"),
        "temp_symbol": temp_symbol,
        "speed_symbol": speed_symbol
    }
    
    forecast_list = forecast_json.get("list", [])
    
    # Hourly Forecast: Next 5 items, step 3 (approx 15h)
    hourly_forecasts = []
    for item in forecast_list[:5]:
        item_main = item.get("main", {})
        item_weather = item.get("weather", [{}])[0]
        dt = item.get("dt")
        
        # Get local hour string
        time_str = datetime.fromtimestamp(dt).strftime("%I:%M %p").lstrip('0')
        
        hourly_forecasts.append({
            "time": time_str,
            "temp": round(item_main.get("temp", 0)),
            "icon": item_weather.get("icon", "01d"),
            "description": item_weather.get("description", "").title()
        })
        
    # Daily Forecast: Group by date
    daily_groups = {}
    for item in forecast_list:
        dt = item.get("dt")
        dt_date = datetime.fromtimestamp(dt).date()
        if dt_date not in daily_groups:
            daily_groups[dt_date] = []
        daily_groups[dt_date].append(item)
        
    daily_forecasts = []
    today = datetime.now().date()
    sorted_dates = sorted(daily_groups.keys())
    
    for date in sorted_dates:
        if date < today:
            continue
        items = daily_groups[date]
        temps = [item.get("main", {}).get("temp", 0) for item in items]
        min_temp = round(min(temps))
        max_temp = round(max(temps))
        
        # Noon item
        noon_item = items[0]
        min_diff = 24
        for item in items:
            item_hour = datetime.fromtimestamp(item.get("dt")).hour
            diff = abs(item_hour - 12)
            if diff < min_diff:
                min_diff = diff
                noon_item = item
                
        weather_item = noon_item.get("weather", [{}])[0]
        day_str = "Today" if date == today else date.strftime("%A")
        
        daily_forecasts.append({
            "date": date.strftime("%b %d"),
            "day": day_str,
            "temp_min": min_temp,
            "temp_max": max_temp,
            "icon": weather_item.get("icon", "01d"),
            "description": weather_item.get("description", "").title()
        })
        
    return {
        "current": current_weather,
        "hourly": hourly_forecasts,
        "daily": daily_forecasts[:5]
    }

def parse_weatherapi_response(data, units):
    """Parses WeatherAPI.com responses into the app standard schema."""
    temp_symbol = "°C" if units == "metric" else "°F"
    speed_symbol = "m/s" if units == "metric" else "mph"
    
    location = data.get("location", {})
    current = data.get("current", {})
    forecast = data.get("forecast", {})
    forecast_days = forecast.get("forecastday", [])
    
    country = location.get("country", "")
    if country.lower() == "united states of america":
        country = "US"
    elif country.lower() == "united kingdom":
        country = "GB"

    wind_kph = current.get("wind_kph", 0)
    wind_speed_ms = wind_kph * 0.27778
    
    cond = current.get("condition", {})
    icon_url = cond.get("icon", "")
    if icon_url and not icon_url.startswith("http"):
        icon_url = "https:" + icon_url

    current_weather = {
        "city": location.get("name"),
        "country": country,
        "temp": round(current.get("temp_c", 0)),
        "feels_like": round(current.get("feelslike_c", 0)),
        "temp_min": round(forecast_days[0].get("day", {}).get("mintemp_c", 0)) if forecast_days else round(current.get("temp_c", 0)),
        "temp_max": round(forecast_days[0].get("day", {}).get("maxtemp_c", 0)) if forecast_days else round(current.get("temp_c", 0)),
        "humidity": current.get("humidity", 0),
        "pressure": round(current.get("pressure_mb", 0)),
        "wind_speed": wind_speed_ms,
        "wind_deg": current.get("wind_degree", 0),
        "description": cond.get("text", "").title(),
        "condition": cond.get("text", "Unknown"),
        "icon": icon_url,
        "dt": location.get("localtime_epoch"),
        "temp_symbol": temp_symbol,
        "speed_symbol": speed_symbol
    }
    
    merged_hours = []
    for f_day in forecast_days[:2]:
        merged_hours.extend(f_day.get("hour", []))
        
    local_epoch = location.get("localtime_epoch", 0)
    future_hours = [h for h in merged_hours if h.get("time_epoch", 0) >= local_epoch - 1800]
    
    hourly_forecasts = []
    for offset in range(0, 15, 3):
        if offset < len(future_hours):
            h_item = future_hours[offset]
            h_cond = h_item.get("condition", {})
            h_icon = h_cond.get("icon", "")
            if h_icon and not h_icon.startswith("http"):
                h_icon = "https:" + h_icon
                
            try:
                time_str = datetime.strptime(h_item.get("time", ""), "%Y-%m-%d %H:%M").strftime("%I:%M %p").lstrip('0')
            except Exception:
                time_str = datetime.fromtimestamp(h_item.get("time_epoch", 0)).strftime("%I:%M %p").lstrip('0')
                
            hourly_forecasts.append({
                "time": time_str,
                "temp": round(h_item.get("temp_c", 0)),
                "icon": h_icon,
                "description": h_cond.get("text", "").title()
            })
            
    daily_forecasts = []
    today_date = datetime.fromtimestamp(local_epoch).date()
    
    for f_day in forecast_days:
        date_str = f_day.get("date", "")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            continue
            
        if date_obj < today_date:
            continue
            
        day_info = f_day.get("day", {})
        d_cond = day_info.get("condition", {})
        d_icon = d_cond.get("icon", "")
        if d_icon and not d_icon.startswith("http"):
            d_icon = "https:" + d_icon
            
        day_str = "Today" if date_obj == today_date else date_obj.strftime("%A")
            
        daily_forecasts.append({
            "date": date_obj.strftime("%b %d"),
            "day": day_str,
            "temp_min": round(day_info.get("mintemp_c", 0)),
            "temp_max": round(day_info.get("maxtemp_c", 0)),
            "icon": d_icon,
            "description": d_cond.get("text", "").title()
        })
        
    return {
        "current": current_weather,
        "hourly": hourly_forecasts,
        "daily": daily_forecasts[:5]
    }

def get_mock_weather_data(query, units="metric"):
    """Generates mock weather data for testing and demo mode."""
    q_clean = query.strip().lower()
    if q_clean == "auto:ip" or not q_clean:
        city = "San Francisco"
        country = "US"
    else:
        city = query.strip().title()
        country = "Local"
        
    temp = 20
    feels_like = 20
    temp_min = 15
    temp_max = 25
    humidity = 60
    pressure = 1013
    wind_speed = 3.5
    wind_deg = 180
    desc = "Partly Cloudy"
    cond_main = "Partly Cloudy"
    icon_code = "116"
    is_day = 1
    
    if "london" in q_clean:
        temp = 15
        feels_like = 14
        temp_min = 11
        temp_max = 18
        humidity = 85
        pressure = 1009
        wind_speed = 5.2
        wind_deg = 220
        desc = "Light Drizzle"
        cond_main = "Patchy rain nearby"
        icon_code = "176"
    elif "tokyo" in q_clean:
        temp = 26
        feels_like = 28
        temp_min = 21
        temp_max = 31
        humidity = 70
        pressure = 1012
        wind_speed = 2.1
        wind_deg = 90
        desc = "Sunny"
        cond_main = "Sunny"
        icon_code = "113"
    elif "paris" in q_clean:
        temp = 22
        feels_like = 22
        temp_min = 16
        temp_max = 27
        humidity = 50
        pressure = 1016
        wind_speed = 4.0
        wind_deg = 300
        desc = "Clear"
        cond_main = "Clear"
        icon_code = "113"
    elif "new york" in q_clean or "nyc" in q_clean:
        temp = 29
        feels_like = 32
        temp_min = 23
        temp_max = 34
        humidity = 75
        pressure = 1008
        wind_speed = 6.5
        wind_deg = 190
        desc = "Heavy Thunderstorm"
        cond_main = "Patchy light rain with thunder"
        icon_code = "386"
    elif "sydney" in q_clean:
        temp = 13
        feels_like = 12
        temp_min = 8
        temp_max = 17
        humidity = 55
        pressure = 1022
        wind_speed = 5.8
        wind_deg = 150
        desc = "Partly Cloudy"
        cond_main = "Partly Cloudy"
        icon_code = "116"
        is_day = 0
        
    icon_sub = "day" if is_day else "night"
    icon_url = f"https://cdn.weatherapi.com/weather/64x64/{icon_sub}/{icon_code}.png"
    
    current_weather = {
        "city": city,
        "country": country,
        "temp": temp,
        "feels_like": feels_like,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "wind_deg": wind_deg,
        "description": desc,
        "condition": cond_main,
        "icon": icon_url,
        "dt": int(datetime.now().timestamp()),
        "temp_symbol": "°C" if units == "metric" else "°F",
        "speed_symbol": "m/s" if units == "metric" else "mph"
    }
    
    daily_forecasts = []
    today = datetime.now().date()
    import datetime as dt_mod
    for i in range(5):
        forecast_date = today + dt_mod.timedelta(days=i)
        var = (i * 2 - 3) % 4 - 2
        d_min = temp_min + var
        d_max = temp_max + var
        day_str = "Today" if i == 0 else ("Tomorrow" if i == 1 else forecast_date.strftime("%A"))
        d_desc = desc
        d_icon_code = icon_code
        if i == 2:
            d_desc = "Sunny"
            d_icon_code = "113"
        elif i == 3:
            d_desc = "Cloudy"
            d_icon_code = "119"
        d_icon_url = f"https://cdn.weatherapi.com/weather/64x64/day/{d_icon_code}.png"
        daily_forecasts.append({
            "date": forecast_date.strftime("%b %d"),
            "day": day_str,
            "temp_min": d_min,
            "temp_max": d_max,
            "icon": d_icon_url,
            "description": d_desc
        })
        
    hourly_forecasts = []
    for step in range(5):
        hour_val = (datetime.now().hour + step * 3) % 24
        period = "AM" if hour_val < 12 else "PM"
        display_hour = hour_val % 12
        if display_hour == 0:
            display_hour = 12
        time_str = f"{display_hour}:00 {period}"
        hour_temp = temp
        if hour_val < 6 or hour_val > 20:
            hour_temp = temp - 4
            h_icon = f"https://cdn.weatherapi.com/weather/64x64/night/{icon_code}.png"
        else:
            hour_temp = temp + 2
            h_icon = f"https://cdn.weatherapi.com/weather/64x64/day/{icon_code}.png"
        hourly_forecasts.append({
            "time": time_str,
            "temp": hour_temp,
            "icon": h_icon,
            "description": desc
        })
        
    return {
        "current": current_weather,
        "hourly": hourly_forecasts,
        "daily": daily_forecasts
    }

def get_weather_icon(icon_url_or_code, size=100):
    """Fetches icon from WeatherAPI.com cdn url or OpenWeatherMap code, and caches it."""
    if not icon_url_or_code:
        return None
        
    # Identify provider based on icon parameter style
    is_url = icon_url_or_code.startswith("http") or icon_url_or_code.startswith("//")
    
    if is_url:
        icon_url = icon_url_or_code
        if icon_url.startswith("//"):
            icon_url = "https:" + icon_url
        try:
            parsed = urllib.parse.urlparse(icon_url)
            cache_filename = parsed.path.strip("/").replace("/", "_")
        except Exception:
            cache_filename = icon_url.split('/')[-1]
    else:
        # OpenWeatherMap code
        icon_code = icon_url_or_code
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        cache_filename = f"owm_{icon_code}@2x.png"
        
    local_path = os.path.join(CACHE_DIR, cache_filename)
    cache_key = f"{cache_filename}_{size}"
    
    if cache_key in _icon_image_cache:
        return _icon_image_cache[cache_key]
        
    if not os.path.exists(local_path):
        try:
            res = requests.get(icon_url, timeout=5)
            if res.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(res.content)
            else:
                return None
        except Exception:
            return None
            
    try:
        img = Image.open(local_path)
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        _icon_image_cache[cache_key] = photo
        return photo
    except Exception as e:
        print(f"Error loading icon: {e}")
        return None

def get_cardinal_direction(deg):
    """Converts a wind degree to a cardinal compass direction (e.g. NNE, W)."""
    if deg is None:
        return "--"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = round(deg / 22.5) % 16
    return dirs[ix]
