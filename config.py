"""Configuration for the European Cross-Commodity Risk Pack."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_RAW = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"
LOGS_DIR = OUTPUT_DIR / "logs"

# Ensure directories exist
for d in [DATA_RAW, CHARTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- API keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Yahoo Finance tickers ---
TICKER_TTF = "TTF=F"
TICKER_EUA = "CO2.L"
TICKER_NBP = "NBP=F"

# --- GIE AGSI+ ---
GIE_API_URL = "https://agsi.gie.eu/api"

# --- SMARD (German power day-ahead) ---
SMARD_BASE_URL = "https://www.smard.de/app/chart_data"
# Filter 4169: Day-ahead price DE/LU
SMARD_FILTER_ID = 4169
SMARD_REGION = "DE-LU"
