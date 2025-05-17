# Configuration constants
CACHE_FILE = "cache.json"
SSL_CERT_PATH = '/etc/ssl/certs/ca-certificates.crt'
USER_AGENT = "Mozilla/5.0"

# Election specific constants
# Default countries list (used as fallback if API fails)
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
FIGURE_SIZE = (9, 12)
PLOT_PADDING = {'pad': 1.0, 'h_pad': 0.5}
PLOT_SPACE = {'hspace': 0.3}

# UI Constants
WINDOW_TITLE = "Election Vote Monitor"
WINDOW_SIZE = "1000x800"

# Frame constants
CONTROL_PADDING = "10"
CONSOLE_PADDING = "10"
FRAME_PADDING = 10
BUTTON_PADDING = 10

# Text widget constants
TEXT_HEIGHT = 25
FIRST_TEXT_BOX_RATIO = 0.45
TEXT_WRAP = "word"
TEXT_FONT = ("Courier", 10, "normal")

# Console layout constants
CONSOLE_EXPAND_RATIO = 0.5
PLOT_EXPAND_RATIO = 0.5

# Plot constants
PLOT_FIGURE_SIZE = (9, 8)
PLOT_GRID_SIZE = (2, 2)

# Table formatting constants
TABLE_HEADER_LEN = 80
TABLE_DIVIDER_CHAR = "-"
TABLE_SUMMARY_DIVIDER_CHAR = "="
TABLE_SUMMARY_HEADER_LEN = 110
TABLE_COL_WIDTHS = {
    "time": 10,
    "country": 27,
    "round": 14,
    "diff": 14,
    "hourly": 16,
    "delta": 10
}