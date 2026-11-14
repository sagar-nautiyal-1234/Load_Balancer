"""Shared constants: palette, fonts and defaults."""

# --- green / black palette ---
BG = "#000000"
PANEL = "#030d05"
GRID = "#04160a"
DIM = "#0a6b26"
MID = "#14b84a"
BRIGHT = "#00ff41"
GLOW = "#0c4d1c"
WARN = "#c8ff00"
DEAD = "#ff3b3b"

# --- fonts ---
FONT = ("Consolas", 10)
FONT_B = ("Consolas", 10, "bold")
FONT_S = ("Consolas", 9)
FONT_XS = ("Consolas", 8)
FONT_T = ("Consolas", 16, "bold")

# --- simulation defaults ---
HOST = "127.0.0.1"
DEFAULT_WEIGHTS = [1, 2, 3, 2]      # one backend per entry
CLIENT_COUNT = 5
CLIENT_SUBNET_BASE = "192.168.1.10"
DEFAULT_RPS = 4
HEALTH_INTERVAL = 1.0               # seconds between PINGs
CONNECT_TIMEOUT = 3.0