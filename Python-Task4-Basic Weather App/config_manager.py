import os
import json

CONFIG_FILE = "weather_config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "units": "metric",  # "metric" for Celsius, "imperial" for Fahrenheit
    "provider": "openweathermap"  # "openweathermap" or "weatherapi" or "demo"
}

def load_config():
    """Loads the config file. If it doesn't exist, returns the default config."""
    # Check environment variable first
    env_key = os.environ.get("OPENWEATHER_API_KEY", "")
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Ensure all default keys exist
                for key, val in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = val
                
                # If env key is set, override the file key
                if env_key:
                    config["api_key"] = env_key
                return config
        except Exception:
            pass
            
    # If file doesn't exist or is corrupt, return defaults with env override
    config = DEFAULT_CONFIG.copy()
    if env_key:
        config["api_key"] = env_key
    return config

def save_config(config):
    """Saves the config dict to weather_config.json."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_api_key():
    """Gets the active API key."""
    return load_config().get("api_key", "")

def set_api_key(api_key):
    """Sets the API key in config."""
    config = load_config()
    config["api_key"] = api_key.strip()
    save_config(config)

def get_units():
    """Gets the active units preference."""
    return load_config().get("units", "metric")

def set_units(units):
    """Sets the unit preference ('metric' or 'imperial')."""
    if units not in ("metric", "imperial"):
        raise ValueError("Units must be 'metric' or 'imperial'")
    config = load_config()
    config["units"] = units
    save_config(config)

def get_provider():
    """Gets the active provider preference."""
    return load_config().get("provider", "openweathermap")

def set_provider(provider):
    """Sets the provider preference ('openweathermap' or 'weatherapi')."""
    if provider not in ("openweathermap", "weatherapi", "demo"):
        raise ValueError("Provider must be 'openweathermap', 'weatherapi' or 'demo'")
    config = load_config()
    config["provider"] = provider
    save_config(config)
