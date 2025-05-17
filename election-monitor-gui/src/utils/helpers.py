def format_country_name(country_name):
    """Format the country name for display."""
    return country_name.upper()

def validate_country_selection(selected_country, valid_countries):
    """Validate the selected country against the list of valid countries."""
    if selected_country not in valid_countries:
        raise ValueError(f"Invalid country selection: {selected_country}")

def load_cached_data(cache_file):
    """Load cached data from a JSON file."""
    import json
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cached_data(cache_file, data):
    """Save data to a JSON cache file."""
    import json
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=4)

def clear_cache(cache_file):
    """Clear the cache by deleting the cache file."""
    import os
    if os.path.exists(cache_file):
        os.remove(cache_file)