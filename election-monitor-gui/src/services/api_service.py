from datetime import datetime
import requests
import json
import os
from src.data.constants import COUNTRIES, ELECTION_DATE_ROUND1, ELECTION_DATE_ROUND2

CACHE_FILE = "src/data/cache.json"

def fetch_data(url):
    """Fetch data from the given URL and return the JSON response."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None

def get_cached_data():
    """Load cached data from the cache file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cached_data(data):
    """Save data to the cache file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_election_data(country):
    """Get election data for the specified country."""
    url_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_{country}.json"
    url_foreign = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_{country}.json"
    
    total_data = fetch_data(url_total)
    foreign_data = fetch_data(url_foreign)
    
    return total_data, foreign_data

def get_all_countries_data():
    """Fetch data for all countries and cache it."""
    all_data = {}
    for country in COUNTRIES:
        total_data, foreign_data = get_election_data(country)
        all_data[country] = {
            "total": total_data,
            "foreign": foreign_data
        }
    save_cached_data(all_data)
    return all_data

def get_country_names():
    """Return the list of country names."""
    return COUNTRIES

def get_election_dates():
    """Return the election dates."""
    return ELECTION_DATE_ROUND1, ELECTION_DATE_ROUND2

def get_current_time():
    """Return the current time formatted as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")