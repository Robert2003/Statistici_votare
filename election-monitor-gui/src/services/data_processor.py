from datetime import datetime, timedelta
import json
import requests
import numpy as np
import pandas as pd
import os
import sys
import matplotlib.pyplot as plt
import unicodedata
import re

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use absolute imports instead of relative imports
from data.constants import (CACHE_FILE, SSL_CERT_PATH, USER_AGENT, COUNTRIES, ROMANIA_NAME,
                     ELECTION_DATE_ROUND1, ELECTION_DATE_ROUND2, DATE_DIFF, 
                     VOTE_START, VOTE_END, UPDATE_MINUTE, UPDATE_SECOND)

class DataProcessor:
    def __init__(self):
        self.cached = {}
        self.request_data_cache = {}
        
        # Data storage
        self.LATEST_DATA = {
            'total': {'round1': 0, 'round2': 0, 'hourly_increase': 0},
            ROMANIA_NAME: {'round1': 0, 'round2': 0, 'hourly_increase': 0}
        }
        
        # Load cache
        self.load_cache()
        
        # Get the country list (either from cache or API)
        self.countries = self.get_country_list()
        
        # Initialize data structure for each country
        for country in self.countries:
            if country not in self.LATEST_DATA:
                self.LATEST_DATA[country] = {'round1': 0, 'round2': 0, 'hourly_increase': 0}
        
        # Initialize data storage for plots
        self.country_data = {}
        self.delta_percents = {}
        self.hourly_increases = {}
        
    def load_cache(self):
        """Load data from cache file"""
        try:
            with open(CACHE_FILE, "r") as f:
                self.cached = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("Cache invalid or missing, recreating...")
            self.cached = {}
    
    def save_cache(self):
        """Save data to cache file"""
        with open(CACHE_FILE, "w") as f:
            json.dump(self.cached, f, indent=4)
            
    def get_dates(self) -> list:
        """Generate a list of timestamps (day, hour) from vote start until now."""
        timestamp = VOTE_START
        now = datetime.now()
        
        if now.strftime("%M") == "00":
            return []  # Not allowed to run at exact hour

        now = (int(now.strftime("%d")), int(now.strftime("%H")))
        dates = []

        while timestamp < VOTE_END and timestamp <= now:
            dates.append(timestamp)
            day, hour = timestamp

            if hour == 23:
                timestamp = (day + 1, 0)
            else:
                timestamp = (day, hour + 1)

        return dates
        
    def get_request_data(self, url: str):
        """Fetch data from URL or cache, to avoid multiple requests for the same URL."""
        if url in self.request_data_cache:
            return self.request_data_cache[url]
            
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, verify=SSL_CERT_PATH)
            data = response.json()
            self.request_data_cache[url] = data
            return data
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return None
    
    def get_country_list(self):
        """Get the list of countries from the API or cache"""
        # Check if we have countries in cache
        if "COUNTRY_LIST" in self.cached:
            print("Using cached country list")
            countries = self.cached["COUNTRY_LIST"]
            
            # Sort countries by votes if we have vote data
            if self.LATEST_DATA:
                try:
                    # Sort by round2 vote count in descending order
                    countries = sorted(countries, 
                                      key=lambda country: self.LATEST_DATA.get(country, {}).get('round2', 0),
                                      reverse=True)
                except Exception as e:
                    print(f"Error sorting countries by votes: {e}")
                    # Fall back to alphabetical sort if sorting by votes fails
                    return sorted(countries)
            return countries
    
        print("Fetching country list from API")
        countries = set()
        
        try:
            # URL for the latest data
            url = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_now.json"
            
            # Get data from request cache or fetch new
            response_data = self.get_request_data(url)
            if response_data and "precinct" in response_data:
                data = pd.json_normalize(response_data["precinct"])
                if "uat.name" in data.columns:
                    # Extract country names
                    countries = set(data["uat.name"].unique())
                    
                    # Filter out any anomalies (empty strings, None, etc)
                    countries = {c for c in countries if c and isinstance(c, str)}
                    
                    # Make sure ROMANIA_NAME is not in the list (it's handled separately)
                    if ROMANIA_NAME in countries:
                        countries.remove(ROMANIA_NAME)
                    
                    # Convert to list
                    countries_list = list(countries)
                    
                    # Get vote data to sort by
                    vote_data = {}
                    for country in countries_list:
                        try:
                            country_data = data[data["uat.name"] == country]
                            total_votes = country_data["LT"].sum()
                            vote_data[country] = total_votes
                        except Exception as e:
                            print(f"Error getting vote data for {country}: {e}")
                            vote_data[country] = 0
                
                    # Sort by vote count in descending order
                    countries_list = sorted(countries_list, key=lambda c: vote_data.get(c, 0), reverse=True)
                    
                    # Cache the country list
                    self.cached["COUNTRY_LIST"] = countries_list
                    self.save_cache()
                    
                    return countries_list
        except Exception as e:
            print(f"Error fetching country list: {e}")
    
        # If we failed to get countries, return the default list sorted by votes if available
        print("Using default country list as fallback")
        if self.LATEST_DATA:
            try:
                # Sort by round2 vote count in descending order
                return sorted(COUNTRIES, 
                             key=lambda country: self.LATEST_DATA.get(country, {}).get('round2', 0),
                             reverse=True)
            except Exception:
                pass
    
        # If sorting fails, fall back to alphabetical sort
        return sorted(COUNTRIES)

    def extract_country_data(self, url: str, country_name: str = None) -> tuple:
        """Extract data for a specific country."""
        if country_name is None:
            country_name = self.countries[0] if self.countries else COUNTRIES[0]  # Use dynamic list
    
        # Skip processing ROMANIA through the regular country method
        # This prevents unnecessary requests for ROMANIA data since it's handled specially
        if country_name.upper() == ROMANIA_NAME.upper():
            return False, 0
    
        cache_key = f"{country_name}_{url}"
        
        if cache_key in self.cached:
            return True, self.cached[cache_key]
        
        # Get data from request cache or fetch new
        response_data = self.get_request_data(url)
        if not response_data:
            return False, 0
        
        try:
            data = pd.json_normalize(response_data["precinct"])
            country_data = data[data["uat.name"] == country_name]
            total = country_data["LT"].sum()
            
            # Cache with country-specific key
            self.cached[cache_key] = int(total)
            return False, int(total)
        except Exception as e:
            print(f"Error processing data for {country_name} from {url}: {e}")
            return False, 0
    
    def extract_total(self, url: str, cache=True) -> tuple:
        """Extract total votes from all counties."""
        cache_key = f"total_{url}"
        
        if cache and cache_key in self.cached:
            return True, self.cached[cache_key]

        # Get data from request cache or fetch new
        response_data = self.get_request_data(url)
        if not response_data:
            return False, 0
        
        try:
            data = pd.json_normalize(response_data["county"])
            total = data["LT"].sum()
            
            if cache:
                self.cached[cache_key] = int(total)
            return False, int(total)
        except Exception as e:
            print(f"Error processing total data from {url}: {e}")
            return False, 0
    
    def extract_straini_total(self, url: str, cache=True) -> tuple:
        """Extract total votes from foreign countries."""
        cache_key = f"straini_{url}"
        
        if cache and cache_key in self.cached:
            return True, self.cached[cache_key]
        
        # Get data from request cache or fetch new
        response_data = self.get_request_data(url)
        if not response_data:
            return False, 0
        
        try:
            # Pentru linkurile cu _sr_, structura este diferită față de ce credeam inițial
            if "precinct" in response_data:
                data = pd.json_normalize(response_data["precinct"])
                total = data["LT"].sum()
            else:
                # Încearcă să citească totalul direct din JSON, dacă există
                total = response_data.get("totalv", 0)
                if total == 0 and "county" in response_data:
                    # Alternativ, încearcă să calculeze suma dacă există "county"
                    data = pd.json_normalize(response_data["county"])
                    if "LT" in data:
                        total = data["LT"].sum()

            if cache:
                self.cached[cache_key] = int(total)
            return False, int(total)
        except Exception as e:
            print(f"Error processing foreign data from {url}: {e}")
            return False, 0
    
    def extract_romania_data(self, total_url: str, straini_url: str, cache=True) -> tuple:
        """Calculate Romania votes by subtracting foreign votes from total."""
        try:
            # Check cache first
            if cache:
                cache_key = f"romania_{total_url}_{straini_url}"
                if cache_key in self.cached:
                    return True, self.cached[cache_key]
            
            # Try to get total response first to check if we're banned
            total_response = requests.get(total_url, headers={"User-Agent": USER_AGENT}, verify=SSL_CERT_PATH)
            straini_response = requests.get(straini_url, headers={"User-Agent": USER_AGENT}, verify=SSL_CERT_PATH)
            
            # Proceed only if both responses are successful
            if total_response.status_code == 200 and straini_response.status_code == 200:
                # Regular processing
                cached_total, total = self.extract_total(total_url, cache)
                cached_straini, straini = self.extract_straini_total(straini_url, cache)
                romania = max(0, total - straini)
                if cache:
                    cache_key = f"romania_{total_url}_{straini_url}"
                    self.cached[cache_key] = int(romania)
                return (cached_total and cached_straini), romania
            else:
                # We might be banned or having connection issues
                print(f"Access issue detected - Total: {total_response.status_code}, Straini: {straini_response.status_code}")
                return False, 0
        except Exception as e:
            print(f"Error in extract_romania_data: {e}")
            return False, 0
    
    def calculate_statistics(self, today_data, last_time_data):
        """Calculate delta percentages and hourly increases for given datasets."""
        delta_percents = np.zeros(len(today_data))
        hourly_increases = np.zeros(len(today_data))
        
        for i in range(len(today_data)):
            # Calculate delta percentage
            if last_time_data[i] > 0:
                delta_percents[i] = ((today_data[i] - last_time_data[i]) / last_time_data[i]) * 100
            
            # Calculate hourly increase
            if i > 0:
                hourly_increases[i] = today_data[i] - today_data[i-1]
                
        return delta_percents, hourly_increases
    
    def process_country_data_with_output(self, dates, country_name):
        """Process data for a specific country and return formatted output."""
        output_lines = []
        
        # Add header
        output_lines.append("\n" + "-"*80)
        output_lines.append(f"  DATE PENTRU {country_name.upper()}  ".center(80, "-"))
        output_lines.append("-"*80)
        
        # Table header
        output_lines.append(f"┌{'─'*10}┬{'─'*14}┬{'─'*14}┬{'─'*14}┬{'─'*16}┬{'─'*10}┐")
        output_lines.append(f"│{' Data ':^10}│{' Tur 2 ':^14}│{' Tur 1 ':^14}│{' Diferență ':^14}│{' Creștere orară ':^16}│{' Delta ':^10}│")
        output_lines.append(f"├{'─'*10}┼{'─'*14}┼{'─'*14}┼{'─'*14}┼{'─'*16}┼{'─'*10}┤")
    
        last_time_data = np.zeros(len(dates))
        today_data = np.zeros(len(dates))
        
        # For tracking hourly increases
        prev_hour_data = 0
        
        for i, (day, hour) in enumerate(dates):
            # Special handling for ROMANIA - reuse existing extract_romania_data method
            if country_name.upper() == ROMANIA_NAME.upper():
                # Pentru România avem nevoie de două URL-uri
                url_today_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_2025-05-{day:02d}_{hour:02d}-00.json"
                url_today_straini = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_2025-05-{day:02d}_{hour:02d}-00.json"
                url_prev_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
                url_prev_straini = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_sr_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
                
                cached_today, total_today = self.extract_romania_data(url_today_total, url_today_straini)
                cached_prev, total_prev = self.extract_romania_data(url_prev_total, url_prev_straini)
            else:
                # Regular handling for other countries
                url_today = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_2025-05-{day:02d}_{hour:02d}-00.json"
                url_prev = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_sr_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
                
                cached_today, total_today = self.extract_country_data(url_today, country_name)
                cached_prev, total_prev = self.extract_country_data(url_prev, country_name)
        
            # Calculate hourly increase
            hourly_increase = total_today - prev_hour_data if i > 0 else total_today
            prev_hour_data = total_today
            
            # Format the time string
            time_str = f"[{day:02d} {hour:02d}:01]"
            
            # Add table row to output
            diff = total_today - total_prev
            hourly_str = f"{hourly_increase:+,d}" if i > 0 else "N/A"
            delta_str = f"{(diff / total_prev * 100):+.2f}%" if total_prev > 0 else "N/A"
            output_lines.append(f"│{time_str:^10}│{total_today:>14,d}│{total_prev:>14,d}│{diff:>+14,d}│{hourly_str:^16}│{delta_str:^10}│")
            
            # Store data
            last_time_data[i] = total_prev
            today_data[i] = total_today
            
            # Store latest data
            if i == len(dates) - 1:
                self.LATEST_DATA[country_name]['round1'] = total_prev
                self.LATEST_DATA[country_name]['round2'] = total_today
                self.LATEST_DATA[country_name]['hourly_increase'] = hourly_increase
    
        # Add table footer
        output_lines.append(f"└{'─'*10}┴{'─'*14}┴{'─'*14}┴{'─'*14}┴{'─'*16}┴{'─'*10}┘")
        
        return "\n".join(output_lines), today_data, last_time_data

    def process_country_data(self, dates, country_name):
        """Process data for a specific country."""
        last_time_data = np.zeros(len(dates))
        today_data = np.zeros(len(dates))
        
        # For tracking hourly increases
        prev_hour_data = 0
        
        for i, (day, hour) in enumerate(dates):
            # Build URLs
            url_today = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_2025-05-{day:02d}_{hour:02d}-00.json"
            url_prev = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_sr_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            
            # Get data
            cached_today, total_today = self.extract_country_data(url_today, country_name)
            cached_prev, total_prev = self.extract_country_data(url_prev, country_name)
            
            # Calculate hourly increase
            hourly_increase = total_today - prev_hour_data if i > 0 else total_today
            prev_hour_data = total_today
            
            # Store data
            last_time_data[i] = total_prev
            today_data[i] = total_today
            
            # Store latest data
            if i == len(dates) - 1:
                self.LATEST_DATA[country_name]['round1'] = total_prev
                self.LATEST_DATA[country_name]['round2'] = total_today
                self.LATEST_DATA[country_name]['hourly_increase'] = hourly_increase
        
        return today_data, last_time_data

    def process_romania_data(self, dates):
        """Process Romania data (without abroad)."""
        last_time_data = np.zeros(len(dates))
        today_data = np.zeros(len(dates))
        
        # For tracking hourly increases
        prev_hour_data = 0
        
        for i, (day, hour) in enumerate(dates):
            # Pentru România avem nevoie de două URL-uri
            url_today_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_2025-05-{day:02d}_{hour:02d}-00.json"
            url_today_straini = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_2025-05-{day:02d}_{hour:02d}-00.json"
            url_prev_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            url_prev_straini = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_sr_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            
            cached_today, total_today = self.extract_romania_data(url_today_total, url_today_straini)
            cached_prev, total_prev = self.extract_romania_data(url_prev_total, url_prev_straini)
            
            # Calculate hourly increase
            hourly_increase = total_today - prev_hour_data if i > 0 else total_today
            prev_hour_data = total_today
            
            # Store data
            last_time_data[i] = total_prev
            today_data[i] = total_today
            
            # Store latest data
            if i == len(dates) - 1:
                self.LATEST_DATA[ROMANIA_NAME]['round1'] = total_prev
                self.LATEST_DATA[ROMANIA_NAME]['round2'] = total_today
                self.LATEST_DATA[ROMANIA_NAME]['hourly_increase'] = hourly_increase
        
        return today_data, last_time_data

    def process_total_data(self, dates):
        """Process total votes data."""
        last_time_data = np.zeros(len(dates))
        today_data = np.zeros(len(dates))
        
        # For tracking hourly increases
        prev_hour_data = 0
        
        for i, (day, hour) in enumerate(dates):
            # Build URLs
            url_today = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_2025-05-{day:02d}_{hour:02d}-00.json"
            url_prev = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            
            # Get data
            cached_today, total_today = self.extract_total(url_today)
            cached_prev, total_prev = self.extract_total(url_prev)
            
            # Calculate hourly increase
            hourly_increase = total_today - prev_hour_data if i > 0 else total_today
            prev_hour_data = total_today
            
            # Store data
            last_time_data[i] = total_prev
            today_data[i] = total_today
            
            # Store latest data
            if i == len(dates) - 1:
                self.LATEST_DATA['total']['round1'] = total_prev
                self.LATEST_DATA['total']['round2'] = total_today
                self.LATEST_DATA['total']['hourly_increase'] = hourly_increase
        
        return today_data, last_time_data

    def update_all_data(self):
        """Update all data needed for plots and summary"""
        # Clear request cache
        self.request_data_cache = {}
        
        # Get dates list
        dates = self.get_dates()
        if not dates:
            return
            
        # Reset data dictionaries
        self.country_data = {}
        self.delta_percents = {}
        self.hourly_increases = {}
        
        # Process data for each country in our dynamic list
        for country in self.countries:
            today_data, last_time_data = self.process_country_data(dates, country)
            
            # Store data for plots
            self.country_data[country] = {
                'today': today_data.copy(),
                'previous': last_time_data.copy()
            }
            
            # Calculate statistics
            delta_pct, hourly_inc = self.calculate_statistics(today_data, last_time_data)
            self.delta_percents[country] = delta_pct
            self.hourly_increases[country] = hourly_inc
        
        # Process Romania data
        today_romania, last_time_romania = self.process_romania_data(dates)
        self.country_data[ROMANIA_NAME] = {
            'today': today_romania,
            'previous': last_time_romania
        }
        delta_pct, hourly_inc = self.calculate_statistics(today_romania, last_time_romania)
        self.delta_percents[ROMANIA_NAME] = delta_pct
        self.hourly_increases[ROMANIA_NAME] = hourly_inc
        
        # Process total data
        today_total, last_time_total = self.process_total_data(dates)
        self.country_data['total'] = {
            'today': today_total,
            'previous': last_time_total
        }
        delta_pct, hourly_inc = self.calculate_statistics(today_total, last_time_total)
        self.delta_percents['total'] = delta_pct
        self.hourly_increases['total'] = hourly_inc
        
        # Save cache
        self.save_cache()

    def plot_voting_data(self, ax, title, today_data, last_time_data, dates):
        """Create a plot for voting data with hover annotations."""
        ax.clear()
        ax.set_title(title)
        
        # Plot the three lines
        line1, = ax.plot(today_data, label="turul 2")
        line2, = ax.plot(last_time_data, label="turul 1")
        line3, = ax.plot(today_data - last_time_data, label="diferenta")
        
        # Set x-ticks to show only every 3 hours to prevent crowding
        tick_interval = 3
        ax.set_xticks(ticks=range(0, len(dates), tick_interval))
        ax.set_xticklabels([f"{hour}" for _, hour in dates[::tick_interval]])
        
        # Move legend to the left
        ax.legend(loc='upper left')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Create vertical line for hover effect - make it dotted
        vline = ax.axvline(0, color='gray', linestyle=':', alpha=0.8, visible=False)
        
        # Create annotation object - initial visibility False to avoid drawing until needed
        annot = ax.annotate("", xy=(0,0), xytext=(0,0), textcoords="offset pixels",
                   bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.9, ec="gray"),
                   arrowprops=None, visible=False)
    
        # Store the lines and their corresponding data - precompute difference
        diff_data = today_data - last_time_data
    
        # Flag to track if we're currently processing hover
        is_processing = [False]
        last_coord = [-1, -1]  # Track last processed position to avoid redundant updates
    
        def hover(event):
            # Only process hover if the mouse is inside this axes and we're not already processing
            if event.inaxes == ax and not is_processing[0]:
                try:
                    is_processing[0] = True
                    x_coord = int(round(event.xdata))
                    
                    # Skip if same position as last time to avoid redrawing
                    if x_coord == last_coord[0]:
                        is_processing[0] = False
                        return
                    
                    last_coord[0] = x_coord
                    last_coord[1] = event.ydata
                    
                    if 0 <= x_coord < len(today_data):
                        # Update the vertical line position - make it more visible
                        vline.set_xdata([x_coord, x_coord])
                        vline.set_visible(True)
                        vline.set_alpha(0.8)  # Increased alpha for better visibility
                        
                        # Format timestamp
                        time_str = ""
                        if x_coord < len(dates):
                            day, hour = dates[x_coord]
                            time_str = f"[{day:02d} {hour:02d}:00]"
                        
                        # Collect data at this position - prepare all text at once
                        text_parts = [f"Timestamp: {time_str}"]
                        
                        # Get values directly without looping
                        t2_val = today_data[x_coord]
                        t1_val = last_time_data[x_coord]
                        diff_val = diff_data[x_coord]
                        
                        text_parts.append(f"Turul 2: {t2_val:,.0f}")
                        text_parts.append(f"Turul 1: {t1_val:,.0f}")
                        text_parts.append(f"Diferență: {diff_val:+,.0f}")
                        
                        # Position annotation directly at mouse pointer coordinates
                        annot.xy = (x_coord, event.ydata)
                        annot.xyann = (10, 10)  # Offset from cursor
                        annot.set_text('\n'.join(text_parts))
                        
                        # Set visible and remove any arrow
                        annot.set_visible(True)
                        
                        # Optimize redraw - only update what's needed
                        ax.figure.canvas.draw_idle()
                    else:
                        # Hide annotation and line when outside plot area
                        vline.set_visible(False)
                        annot.set_visible(False)
                        ax.figure.canvas.draw_idle()
                except:
                    pass
                finally:
                    is_processing[0] = False
            elif event.inaxes != ax and annot.get_visible():
                # Hide when mouse leaves the axes
                vline.set_visible(False)
                annot.set_visible(False)
                ax.figure.canvas.draw_idle()
    
        # Connect event with throttling to reduce computational load
        ax.figure.canvas.mpl_connect("motion_notify_event", hover)


    def plot_combined_stats(self, ax, delta_percents, hourly_increases, dates):
        """Create a combined plot for delta percentages and hourly increases with hover annotations."""
        ax.clear()
        ax_twin = ax.twinx()
        
        # Add title for the combined plot
        ax.set_title("Creștere procentuală (Delta %) și Creștere orară")
        
        # Add TOTAL delta percentage line on the main axis
        line1, = ax.plot(delta_percents["total"], label="TOTAL %", linewidth=4, color='darkblue')
        
        # Add TOTAL hourly increase line on the secondary axis
        line2, = ax_twin.plot(hourly_increases["total"], label="Creștere orară", linewidth=3, color='red', linestyle='--')
        
        # Set x-ticks to show only every 3 hours
        tick_interval = 3
        ax.set_xticks(ticks=range(0, len(dates), tick_interval))
        ax.set_xticklabels([f"{hour}" for _, hour in dates[::tick_interval]])
        ax.set_ylabel('Creștere %')
        ax_twin.set_ylabel('Creștere orară (voturi)')
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Move legend to the left
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax_twin.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize='small')
        
        # Create vertical line for hover effect
        vline = ax.axvline(0, color='gray', linestyle=':', alpha=0.8, visible=False)
        
        # Create annotation object with improved positioning
        annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.9, ec="gray"),
                    arrowprops=None, visible=False)

        # Flag to track if we're currently processing hover
        is_processing = [False]
        last_coord = [-1, -1]  # Track last processed position

        # Precompute data arrays for faster access
        delta_data = delta_percents["total"]
        hourly_data = hourly_increases["total"]
        
        def hover(event):
            # Only process hover if inside axes and not already processing
            if (event.inaxes in [ax, ax_twin]) and not is_processing[0]:
                try:
                    is_processing[0] = True
                    x_coord = int(round(event.xdata))
                    
                    # Skip if same position as last time or invalid coordinate
                    if x_coord == last_coord[0] or x_coord < 0:
                        is_processing[0] = False
                        return
                    
                    last_coord[0] = x_coord
                    
                    # Make sure the coordinates are valid
                    if x_coord < len(delta_data):
                        # Update the vertical line position
                        vline.set_xdata([x_coord, x_coord])
                        vline.set_visible(True)
                        
                        # Format timestamp
                        time_str = ""
                        if x_coord < len(dates):
                            day, hour = dates[x_coord]
                            time_str = f"[{day:02d} {hour:02d}:00]"
                        
                        # Prepare all text at once
                        text_parts = [f"Timestamp: {time_str}"]
                        
                        # Get values directly - ensure we show some value even if data is missing
                        delta_value = delta_data[x_coord] if x_coord < len(delta_data) else 0
                        text_parts.append(f"Delta %: {delta_value:+.2f}%")
                        
                        hourly_value = hourly_data[x_coord] if x_coord < len(hourly_data) else 0
                        text_parts.append(f"Creștere orară: {hourly_value:+,.0f}")
                        
                        # Position annotation at cursor position
                        annot.xy = (x_coord, event.ydata)
                        annot.set_text('\n'.join(text_parts))
                        
                        # Make annotation visible
                        annot.set_visible(True)
                        
                        # Force redraw to ensure visibility
                        ax.figure.canvas.draw_idle()
                    else:
                        # Hide annotation when outside plot area
                        vline.set_visible(False)
                        annot.set_visible(False)
                        ax.figure.canvas.draw_idle()
                except Exception as e:
                    print(f"Hover error: {e}")
                finally:
                    is_processing[0] = False
            elif event.inaxes not in [ax, ax_twin] and annot.get_visible():
                # Hide when mouse leaves the axes
                vline.set_visible(False)
                annot.set_visible(False)
                ax.figure.canvas.draw_idle()

        # Connect event
        ax.figure.canvas.mpl_connect("motion_notify_event", hover)

    def get_live_total(self):
        """Get the latest total vote count directly from the live endpoint"""
        try:
            # Use the presence_now.json endpoint which returns the most current data
            url = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_now.json"
            
            # Set cache=False to force a fresh request
            _, total = self.extract_total(url, cache=False)
            return total
        except Exception as e:
            print(f"Error fetching live data: {e}")
            # Fall back to the last known total if there's an error
            if 'total' in self.LATEST_DATA:
                return self.LATEST_DATA['total'].get('round2', 0)
            return 0

    def calculate_next_update_time(self):
        """Calculate the next update time."""
        now = datetime.now()
        
        # Calculate next update time (next hour at UPDATE_MINUTE:UPDATE_SECOND)
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        next_update = next_hour.replace(minute=UPDATE_MINUTE, second=UPDATE_SECOND)
        
        # If we're after UPDATE_MINUTE:UPDATE_SECOND of current hour, go to next hour
        if now.minute > UPDATE_MINUTE or (now.minute == UPDATE_MINUTE and now.second >= UPDATE_SECOND):
            wait_seconds = (next_update - now).total_seconds()
        else:
            # Otherwise update at UPDATE_MINUTE:UPDATE_SECOND of current hour
            wait_seconds = (now.replace(minute=UPDATE_MINUTE, second=UPDATE_SECOND) - now).total_seconds()
            if wait_seconds < 0:
                wait_seconds = (next_update - now).total_seconds()
        
        return next_update, wait_seconds
    
    def refresh_country_list(self):
        """Force a refresh of the country list from the API"""
        if "COUNTRY_LIST" in self.cached:
            del self.cached["COUNTRY_LIST"]
        
        self.countries = self.get_country_list()
        
        # Make sure all countries have data structures
        for country in self.countries:
            if country not in self.LATEST_DATA:
                self.LATEST_DATA[country] = {'round1': 0, 'round2': 0, 'hourly_increase': 0}
        
        # Save updated cache
        self.save_cache()
        
        return self.countries

    # Add a utility method to handle country name display
    def get_display_name(self, country):
        """Get a shortened display name for a country if needed"""
        if country == "REGATUL UNIT AL MARII BRITANIEI \u0218I AL IRLANDEI DE NORD":
            return "MAREA BRITANIE"
        return country
    
    def search_countries(self, search_term, max_results=10):
        """
        Search for countries that match the search term.
        
        Args:
            search_term: String to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of matching country names, sorted by relevance
        """
        if not search_term or not self.countries:
            return self.countries[:max_results]  # Return all countries if no search term
        
        # Normalize the search term (lowercase, remove accents)
        search_term = self._normalize_text(search_term)
        
        # Match scores for each country
        # (higher score = better match)
        matches = []
        
        for country in self.countries:
            # Normalize country name for matching
            norm_country = self._normalize_text(country)
            
            # Skip if there's no match at all
            if search_term not in norm_country:
                continue
                
            # Calculate match score based on various factors
            score = 0
            
            # Exact match gets highest score
            if norm_country == search_term:
                score = 100
            # Starting with the search term gets high score
            elif norm_country.startswith(search_term):
                score = 75 + (len(search_term) / len(norm_country)) * 20
            # Contains the search term as a whole word gets medium-high score
            elif re.search(r'\b' + re.escape(search_term) + r'\b', norm_country):
                score = 60 + (len(search_term) / len(norm_country)) * 15
            # Contains the search term gets medium score
            else:
                score = 30 + (len(search_term) / len(norm_country)) * 25
                
            matches.append((country, score))
        
        # Sort matches by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N matches
        return [country for country, _ in matches[:max_results]]

    def _normalize_text(self, text):
        """Remove accents and convert to lowercase for better matching"""
        # Convert to lowercase
        text = text.lower()
        # Remove accents
        text = ''.join(c for c in unicodedata.normalize('NFD', text)
                       if unicodedata.category(c) != 'Mn')
        return text