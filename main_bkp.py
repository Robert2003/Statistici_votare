#!/usr/bin/env python3
# Copyright (c) 2025 Alexandru Sima (332CA) - Tema 3 PCLP 1

from datetime import datetime
import json

import requests

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CACHE_FILE = "cache.json"
cached = {}

def get_dates() -> list:
    timestamp = (15, 22)
    VOTE_END = (18, 21)

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


def extract_moldova(url: str) -> tuple[bool, int]:
    global cached
    if url in cached:
        return True, cached[url]
    
    response = requests.get(url, headers={ "User-Agent": "Mozilla/5.0" }, verify='/etc/ssl/certs/ca-certificates.crt')
    response = response.json()

    data = pd.json_normalize(response["precinct"])

    moldova = data[data["uat.name"] == "REPUBLICA MOLDOVA"]
    total = moldova["LT"].sum()

    cached[url] = int(total)
    return False, total


def extract_total(url: str, cache=True) -> tuple[bool, int]:
    global cached
    if cache and url in cached:
        return True, cached[url]

    response = requests.get(url, headers={ "User-Agent": "Mozilla/5.0" }, verify='/etc/ssl/certs/ca-certificates.crt')
    response = response.json()

    data = pd.json_normalize(response["county"])
    total = data["LT"].sum()

    if cache:
        cached[url] = int(total)
    return False, total


def compare_rounds(req_url: str, dates: list, category: str, func: callable) -> tuple[np.ndarray, np.ndarray]:
    DATE_DIFF = 14

    last_time_data = np.zeros(len(dates))
    today_data = np.zeros(len(dates))

    for i, (day, hour) in enumerate(dates):
        url_today = f"https://prezenta.roaep.ro/prezidentiale18052025/{req_url}_2025-05-{day:02d}_{hour:02d}-00.json"
        url_prev = f"https://prezenta.roaep.ro/prezidentiale04052025/{req_url}_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"

        cached_today, total_today = func(url_today)
        cached_prev, total_prev = func(url_prev)
        print(f"[{day:02d} {hour:02d}:00] {category} tur 2{" (CACHED)" if cached_today else ""}:", total_today, f"\t{category} tur 1{" (CACHED)" if cached_prev else ""}:", total_prev, "\tdiferenta:", total_today - total_prev, "\tdelta (%):", round((total_today - total_prev) / total_prev * 100, 2))

        last_time_data[i] = total_prev
        today_data[i] = total_today

    return today_data, last_time_data


def main():
    global cached

    try: 
        with open(CACHE_FILE, "r") as f:
            cached = json.load(f)
    except json.JSONDecodeError:
        print("Cache invalid, recreating...")
        cached = {}
    except FileNotFoundError:
        cached = {}

    dates = get_dates()

    # ======================================================================= #

    today_moldova, last_time_moldova = compare_rounds("data/json/simpv/presence/presence_sr", dates, "moldova", extract_moldova)

    plt.title("Voturi Rep. Moldova")
    plt.plot(today_moldova, label="turul 2")
    plt.plot(last_time_moldova, label="turul 1")
    plt.plot(today_moldova - last_time_moldova, label="diferenta")
    plt.xticks(ticks=range(0, len(dates), 2), labels=[hour for _, hour in dates[::2]])
    plt.legend()
    plt.show()

    # ======================================================================= #

    today_total, last_time_total = compare_rounds("data/json/simpv/presence/presence", dates, "total", extract_total)

    print()
    _, live_total = extract_total("https://prezenta.roaep.ro/prezidentiale18052025/data/json/simpv/presence/presence_now.json", cache=False)
    print("[LIVE] total:", live_total, f"({(int(live_total - today_total[-1])):+d} fata de ultima ora)")

    plt.title("Total voturi")
    plt.plot(today_total, label="turul 2")
    plt.plot(last_time_total, label="turul 1")
    plt.plot(today_total - last_time_total, label="diferenta")
    plt.xticks(ticks=range(0, len(dates), 2), labels=[hour for _, hour in dates[::2]])
    plt.legend()
    plt.show()


    with open(CACHE_FILE, "w") as f:
        json.dump(cached, f, indent=4)

if __name__ == "__main__":
    main()
