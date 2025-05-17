#!/usr/bin/env python3
# Copyright (c) 2025 Alexandru Sima (332CA) - Tema 3 PCLP 1

from datetime import datetime, timedelta
import json
import time
import requests
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import argparse
from matplotlib.animation import FuncAnimation

# Configuration constants
CACHE_FILE = "cache.json"
SSL_CERT_PATH = '/etc/ssl/certs/ca-certificates.crt'
USER_AGENT = "Mozilla/5.0"

# Election specific constants
COUNTRIES = ["REGATUL UNIT AL MARII BRITANII \u0218I AL IRLANDEI DE NORD", "GERMANIA", "FRAN\u021aA", "ITALIA", "SPANIA", "REGATUL \u021a\u0102RILOR DE JOS", "REPUBLICA MOLDOVA"]
ROMANIA_NAME = "ROMANIA"  # Pentru filtrare

ELECTION_DATE_ROUND1 = "04052025"
ELECTION_DATE_ROUND2 = "18052025"
DATE_DIFF = 14  # Days difference between rounds

# Time constants
VOTE_START = (15, 22)  # Day, hour
VOTE_END = (18, 21)    # Day, hour
UPDATE_MINUTE = 1
UPDATE_SECOND = 1

# Plotting constants
FIGURE_SIZE = (9, 12)  # Mărit pentru a acomoda 3 grafice
PLOT_PADDING = {'pad': 1.0, 'h_pad': 0.5}
PLOT_SPACE = {'hspace': 0.3}  # Spațiere între subplot-uri

# Data storage for summary
LATEST_DATA = {
    'total': {'round1': 0, 'round2': 0, 'hourly_increase': 0},
    ROMANIA_NAME: {'round1': 0, 'round2': 0, 'hourly_increase': 0}
}

# Initialize data structure for each country
for country in COUNTRIES:
    LATEST_DATA[country] = {'round1': 0, 'round2': 0, 'hourly_increase': 0}

# Cache dictionary
cached = {}
# Request data cache to avoid multiple requests for the same URL
request_data_cache = {}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Monitor presidential election data")
    parser.add_argument('-c', '--country', choices=COUNTRIES, 
                      default=COUNTRIES[0],
                      help='Select country to display in the first chart')
    return parser.parse_args()

def get_dates() -> list:
    """Generate a list of timestamps (day, hour) from vote start until now."""
    timestamp = VOTE_START
    now = datetime.now()
    
    if now.strftime("%M") == "00":
        print("Nu ai voie sa rulezi acest script la fix!")
        exit(-1)

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

def get_request_data(url: str):
    """Fetch data from URL or cache, to avoid multiple requests for the same URL."""
    global request_data_cache
    
    if url in request_data_cache:
        return request_data_cache[url]
        
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, verify=SSL_CERT_PATH)
        data = response.json()
        request_data_cache[url] = data
        return data
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def extract_country_data(url: str, country_name: str = None) -> tuple[bool, int]:
    """Extract data for a specific country."""
    if country_name is None:
        country_name = COUNTRIES[0]  # Default to first country if not specified
    
    global cached
    cache_key = f"{country_name}_{url}"
    
    if cache_key in cached:
        return True, cached[cache_key]
    
    # Get data from request cache or fetch new
    response_data = get_request_data(url)
    if not response_data:
        return False, 0
    
    try:
        data = pd.json_normalize(response_data["precinct"])
        country_data = data[data["uat.name"] == country_name]
        total = country_data["LT"].sum()
        
        # Cache with country-specific key
        cached[cache_key] = int(total)
        return False, int(total)
    except Exception as e:
        print(f"Error processing data for {country_name} from {url}: {e}")
        return False, 0

def extract_total(url: str, cache=True) -> tuple[bool, int]:
    """Extract total votes from all counties."""
    global cached
    cache_key = f"total_{url}"
    
    if cache and cache_key in cached:
        return True, cached[cache_key]

    # Get data from request cache or fetch new
    response_data = get_request_data(url)
    if not response_data:
        return False, 0
    
    try:
        data = pd.json_normalize(response_data["county"])
        total = data["LT"].sum()
        
        if cache:
            cached[cache_key] = int(total)
        return False, int(total)
    except Exception as e:
        print(f"Error processing total data from {url}: {e}")
        return False, 0

def extract_straini_total(url: str, cache=True) -> tuple[bool, int]:
    """Extract total votes from foreign countries."""
    global cached
    cache_key = f"straini_{url}"
    
    if cache and cache_key in cached:
        return True, cached[cache_key]
    
    # Get data from request cache or fetch new
    response_data = get_request_data(url)
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
            cached[cache_key] = int(total)
        return False, int(total)
    except Exception as e:
        print(f"Error processing foreign data from {url}: {e}")
        return False, 0

def extract_romania_data(total_url: str, straini_url: str, cache=True) -> tuple[bool, int]:
    """Calculate Romania votes by subtracting foreign votes from total."""
    # Obține total
    cached_total, total = extract_total(total_url, cache)
    
    # Obține străini
    cached_straini, straini = extract_straini_total(straini_url, cache)
    
    # România = Total - Străinătate
    romania = total - straini
    
    # Cache Romania result separately
    if cache:
        cache_key = f"romania_{total_url}_{straini_url}"
        cached[cache_key] = int(romania)
    
    return (cached_total and cached_straini), romania

def print_table_header():
    """Print the standard table header for data comparisons."""
    print(f"┌{'─'*10}┬{'─'*14}┬{'─'*14}┬{'─'*14}┬{'─'*16}┬{'─'*10}┐")
    print(f"│{' Data ':^10}│{' Tur 2 ':^14}│{' Tur 1 ':^14}│{' Diferență ':^14}│{' Creștere orară ':^16}│{' Delta ':^10}│")
    print(f"├{'─'*10}┼{'─'*14}┼{'─'*14}┼{'─'*14}┼{'─'*16}┼{'─'*10}┤")

def print_table_row(time_str, total_today, total_prev, hourly_increase, i, delta_percent=None):
    """Print a formatted table row for data display."""
    diff = total_today - total_prev
    
    # Format the hourly increase field
    hourly_str = f"{hourly_increase:+,d}" if i > 0 else "N/A"
    
    # Format the delta percentage field
    if delta_percent is not None:
        delta_str = f"{delta_percent:+.2f}%" if total_prev > 0 else "N/A"
    else:
        delta_str = f"{(diff / total_prev * 100):+.2f}%" if total_prev > 0 else "N/A"
        
    print(f"│{time_str:^10}│{total_today:>14,d}│{total_prev:>14,d}│{diff:>+14,d}│{hourly_str:^16}│{delta_str:^10}│")

def print_table_footer():
    """Print the standard table footer for data comparisons."""
    print(f"└{'─'*10}┴{'─'*14}┴{'─'*14}┴{'─'*14}┴{'─'*16}┴{'─'*10}┘")

def print_section_header(title):
    """Print a formatted section header."""
    print("\n" + "-"*80)
    print(f"  {title}  ".center(80, "-"))
    print("-"*80)

def calculate_statistics(today_data, last_time_data):
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

def compare_rounds(req_url: str, dates: list, category: str, func: callable, extra_args=None) -> tuple[np.ndarray, np.ndarray]:
    """Compare data between election rounds for a category."""
    global LATEST_DATA
    last_time_data = np.zeros(len(dates))
    today_data = np.zeros(len(dates))

    # Clear the request data cache for each comparison to ensure fresh data
    global request_data_cache
    request_data_cache = {}
    
    # For tracking hourly increases
    prev_hour_data = 0
    
    print_table_header()

    for i, (day, hour) in enumerate(dates):
        if category == ROMANIA_NAME:
            # Pentru România avem nevoie de două URL-uri
            url_today_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_2025-05-{day:02d}_{hour:02d}-00.json"
            url_today_straini = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_sr_2025-05-{day:02d}_{hour:02d}-00.json"
            url_prev_total = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            url_prev_straini = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_sr_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            
            cached_today, total_today = func(url_today_total, url_today_straini)
            cached_prev, total_prev = func(url_prev_total, url_prev_straini)
        else:
            # Pentru restul categoriilor procesăm normal
            url_today = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/{req_url}_2025-05-{day:02d}_{hour:02d}-00.json"
            url_prev = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/{req_url}_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            
            if extra_args:
                cached_today, total_today = func(url_today, *extra_args)
                cached_prev, total_prev = func(url_prev, *extra_args)
            else:
                cached_today, total_today = func(url_today)
                cached_prev, total_prev = func(url_prev)
        
        # Calculate hourly increase
        hourly_increase = total_today - prev_hour_data if i > 0 else total_today
        prev_hour_data = total_today
        
        # Format the time string
        time_str = f"[{day:02d} {hour:02d}:01]"
        
        # Print the table row
        print_table_row(time_str, total_today, total_prev, hourly_increase, i)

        # Store the latest data for summary - using original case for category
        if category in LATEST_DATA:
            LATEST_DATA[category]['round1'] = total_prev
            LATEST_DATA[category]['round2'] = total_today
            LATEST_DATA[category]['hourly_increase'] = hourly_increase
            
        last_time_data[i] = total_prev
        today_data[i] = total_today
    
    print_table_footer()
    return today_data, last_time_data

def print_country_data(dates, country_name):
    """Process and print data for a specific country."""
    print_section_header(f"DATE PENTRU {country_name.upper()}")
    
    return compare_rounds(
        "data/json/simpv/presence/presence_sr", 
        dates, 
        country_name, 
        extract_country_data,
        [country_name]
    )

def plot_voting_data(ax, title, today_data, last_time_data, dates):
    """Create a plot for voting data."""
    ax.clear()
    ax.set_title(title)
    ax.plot(today_data, label="turul 2")
    ax.plot(last_time_data, label="turul 1")
    ax.plot(today_data - last_time_data, label="diferenta")
    ax.set_xticks(ticks=range(0, len(dates), 2))
    ax.set_xticklabels([f"{hour}" for _, hour in dates[::2]])
    ax.legend()

def plot_combined_stats(ax, delta_percents, hourly_increases, dates):
    """Create a combined plot for delta percentages and hourly increases."""
    ax.clear()
    ax_twin = ax.twinx()
    
    # Add title for the combined plot
    ax.set_title("Creștere procentuală (Delta %) și Creștere orară")
    
    # Add TOTAL delta percentage line on the main axis
    ax.plot(delta_percents["total"], label="TOTAL %", linewidth=4, color='darkblue')
    
    # Add TOTAL hourly increase line on the secondary axis
    ax_twin.plot(hourly_increases["total"], label="Creștere orară", linewidth=3, color='red', linestyle='--')
    
    # Set axis labels
    ax.set_xticks(ticks=range(0, len(dates), 2))
    ax.set_xticklabels([f"{hour}" for _, hour in dates[::2]])
    ax.set_ylabel('Creștere %')
    ax_twin.set_ylabel('Creștere orară (voturi)')
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Combine legends from both axes
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax_twin.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize='small')
    
    return ax_twin  # Return the twin axis for future reference

def print_summary_table(dates):
    """Print a summary table with the latest data."""
    print("\n" + "="*110)
    print("  REZUMAT DATE RECENTE  ".center(110, "="))
    print("="*110)
    
    last_day, last_hour = dates[-1]
    
    # Print header for the summary table
    print(f"┌{'─'*10}┬{'─'*27}┬{'─'*14}┬{'─'*14}┬{'─'*14}┬{'─'*16}┬{'─'*10}┐")
    print(f"│{' Data ':^10}│{' Țară ':^27}│{' Tur 2 ':^14}│{' Tur 1 ':^14}│{' Diferență ':^14}│{' Creștere orară ':^16}│{' Delta ':^10}│")
    print(f"├{'─'*10}┼{'─'*27}┼{'─'*14}┼{'─'*14}┼{'─'*14}┼{'─'*16}┼{'─'*10}┤")
    
    time_str = f"[{last_day:02d} {last_hour:02d}:00]"
    
    # Print individual countries
    for country in COUNTRIES:
        if country in LATEST_DATA:
            r1 = LATEST_DATA[country]['round1']
            r2 = LATEST_DATA[country]['round2']
            hourly = LATEST_DATA[country]['hourly_increase']

            # Shorten UK name for display
            display_country = "MAREA BRITANIE" if country == "REGATUL UNIT AL MARII BRITANII \u0218I AL IRLANDEI DE NORD" else country

            diff = r2 - r1
            delta = round(diff / r1 * 100, 2) if r1 > 0 else 0
            
            delta_str = f"{delta:+.2f}%" if r1 > 0 else "N/A"
            
            print(f"│{time_str:^10}│{display_country:^27}│{r2:>14,d}│{r1:>14,d}│{diff:>+14,d}│{hourly:>+16,d}│{delta_str:^10}│")
    
    # Print Romania (without abroad)
    print_summary_row(time_str, ROMANIA_NAME, ROMANIA_NAME)
    
    # Print the total votes
    print_summary_row(time_str, 'total', 'TOTAL')
    
    print(f"└{'─'*10}┴{'─'*27}┴{'─'*14}┴{'─'*14}┴{'─'*14}┴{'─'*16}┴{'─'*10}┘")

def print_summary_row(time_str, data_key, display_name):
    """Print a summary row for the given entity."""
    r1 = LATEST_DATA[data_key]['round1']
    r2 = LATEST_DATA[data_key]['round2']
    hourly = LATEST_DATA[data_key]['hourly_increase']
    diff = r2 - r1
    delta = round(diff / r1 * 100, 2) if r1 > 0 else 0
    
    delta_str = f"{delta:+.2f}%" if r1 > 0 else "N/A"
    
    print(f"│{time_str:^10}│{display_name:^27}│{r2:>14,d}│{r1:>14,d}│{diff:>+14,d}│{hourly:>+16,d}│{delta_str:^10}│")

def get_live_total():
    """Get live total votes data."""
    global request_data_cache
    request_data_cache = {}  # Clear cache to ensure fresh data
    _, live_total = extract_total(
        f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_now.json", 
        cache=False
    )
    return live_total

def update_data_and_plots(fig, ax1, ax2, ax3, ax4, selected_country):
    """Update data and refresh plots."""
    global cached, LATEST_DATA, request_data_cache
    
    # Clear the request data cache to ensure fresh data each update
    request_data_cache = {}
    
    # Clear the console before displaying new data
    os.system('clear')

    print("\n" + "="*80)
    print(f"  ACTUALIZARE DATE LA {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}  ".center(80, "="))
    print("="*80)
    
    # Încarcă datele din cache
    try: 
        with open(CACHE_FILE, "r") as f:
            cached = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print("Cache invalid sau lipsește, recreare...")
        cached = {}
    
    dates = get_dates()
    
    # Șterge conținutul graficelor anterioare
    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()
    
    # Creăm dicționare pentru stocarea delta procentelor și creșterilor orare pentru fiecare categorie
    delta_percents = {}
    hourly_increases = {}
    
    # Process selected country for plotting in ax1
    print_section_header(f"DATE PENTRU {selected_country.upper()}")
    today_selected_country, last_time_selected_country = print_country_data(dates, selected_country)
    
    # Calculăm statisticile pentru țara selectată
    delta_percents[selected_country], hourly_increases[selected_country] = calculate_statistics(
        today_selected_country, last_time_selected_country
    )
    
    # Plot data for selected country
    plot_voting_data(ax1, f"Voturi {selected_country}", 
                    today_selected_country, last_time_selected_country, dates)
    
    # Process remaining countries
    for country in COUNTRIES:
        if country != selected_country:
            today_country, last_time_country = print_country_data(dates, country)
            
            # Calculăm statisticile pentru acest country
            delta_percents[country], hourly_increases[country] = calculate_statistics(
                today_country, last_time_country
            )

    # Process Romania data
    print_section_header(f"DATE PENTRU {ROMANIA_NAME.upper()} (FĂRĂ STRĂINĂTATE)")
    
    today_romania, last_time_romania = compare_rounds(
        "", 
        dates, 
        ROMANIA_NAME, 
        extract_romania_data
    )
    
    # Calculăm statisticile pentru Romania
    delta_percents[ROMANIA_NAME], hourly_increases[ROMANIA_NAME] = calculate_statistics(
        today_romania, last_time_romania
    )
    
    # Plot Romania data
    plot_voting_data(ax2, f"Voturi {ROMANIA_NAME} (fără străinătate)", 
                    today_romania, last_time_romania, dates)

    # Process total votes data
    print_section_header("DATE PENTRU TOTAL VOTURI")
    
    today_total, last_time_total = compare_rounds(
        "data/json/simpv/presence/presence", 
        dates, 
        "total", 
        extract_total
    )

    # Calculăm statisticile pentru Total
    delta_percents["total"], hourly_increases["total"] = calculate_statistics(
        today_total, last_time_total
    )

    # Get and display live data
    print_section_header("DATE LIVE")
    live_total = get_live_total()
    print(f"TOTAL VOTURI: {live_total:,d} ({(int(live_total - today_total[-1])):+,d} FAȚĂ DE ULTIMA ORĂ)  ".center(80, "-"))

    # Plot total votes data
    plot_voting_data(ax3, "Total voturi", today_total, last_time_total, dates)
    
    # Plot combined statistics
    ax4_twin = plot_combined_stats(ax4, delta_percents, hourly_increases, dates)
    
    # Print the summary table
    print_summary_table(dates)
    
    # Adjust layout and save cache
    fig.set_constrained_layout(True)
    
    # Salvează cache-ul
    with open(CACHE_FILE, "w") as f:
        json.dump(cached, f, indent=4)
    
    fig.canvas.draw_idle()

def calculate_next_update_time():
    """Calculate the next update time."""
    now = datetime.now()
    
    # Calculează următoarea actualizare (ora următoare, min 01, sec 01)
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    next_update = next_hour.replace(minute=UPDATE_MINUTE, second=UPDATE_SECOND)
    
    # Dacă suntem după minutul UPDATE_MINUTE al orei curente, mergem la ora următoare
    if now.minute > UPDATE_MINUTE or (now.minute == UPDATE_MINUTE and now.second >= UPDATE_SECOND):
        wait_seconds = (next_update - now).total_seconds()
    else:
        # Altfel, actualizăm la minutul UPDATE_MINUTE și secunda UPDATE_SECOND a orei curente
        wait_seconds = (now.replace(minute=UPDATE_MINUTE, second=UPDATE_SECOND) - now).total_seconds()
        if wait_seconds < 0:
            wait_seconds = (next_update - now).total_seconds()
    
    return next_update, wait_seconds

def wait_until_next_update():
    """Așteaptă până la următoarea actualizare (ora X:01:01)"""
    next_update, wait_seconds = calculate_next_update_time()
    print(f"\nUrmatoarea actualizare la: {next_update.strftime('%H:%M:%S')} (peste {int(wait_seconds)} secunde)")
    return wait_seconds

def handle_auto_updates(fig, axes, selected_country):
    """Set up automatic updates for the plots."""
    # Unpacking the axes
    ax1, ax2, ax3, ax4 = axes
    
    # Variabilă pentru a urmări ora ultimei actualizări
    last_update_hour = datetime.now().hour
    
    def auto_update(frame):
        nonlocal last_update_hour
        
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_second = now.second
        
        # Verifică dacă este momentul pentru actualizare:
        # - dacă e ora diferită de ultima actualizare
        # - și suntem la minutul UPDATE_MINUTE, secunda UPDATE_SECOND sau mai mare
        if (current_hour != last_update_hour and 
            current_minute >= UPDATE_MINUTE and current_second >= UPDATE_SECOND):
            
            print(f"\nActualizare automată la {now.strftime('%H:%M:%S')}")
            update_data_and_plots(fig, ax1, ax2, ax3, ax4, selected_country)
            last_update_hour = current_hour
            
            # Calculează și afișează timpul până la următoarea actualizare
            wait_until_next_update()
    
    # Creează animația care va apela auto_update la fiecare secundă pentru verificare
    return FuncAnimation(fig, auto_update, interval=1000, cache_frame_data=False)

def main():
    global cached
    
    # Parse command line arguments
    args = parse_arguments()
    selected_country = args.country
    
    print(f"Țara selectată pentru primul grafic: {selected_country}")

    # Crează figura și axele cu aranjament vertical (4 rânduri, 1 coloană)
    fig, axes = plt.subplots(4, 1, figsize=FIGURE_SIZE, gridspec_kw=PLOT_SPACE, constrained_layout=True)
    ax1, ax2, ax3, ax4 = axes
    
    # Prima actualizare imediată
    update_data_and_plots(fig, ax1, ax2, ax3, ax4, selected_country)
    
    # Calculează și afișează timpul până la următoarea actualizare
    wait_until_next_update()
    
    # Set up automatic updates
    ani = handle_auto_updates(fig, axes, selected_country)
    
    plt.show()

if __name__ == "__main__":
    main()