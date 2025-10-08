"""
Configuration module for the DB Analyst Agent application.

This module centralizes all application settings. It reads sensitive data
from environment variables and defines non-sensitive, application-wide
parameters. This provides a single source of truth for configuration.
"""
import os
from dotenv import load_dotenv

# Load environment variables from the .env file located in the project root
# The path is relative to where the script is run from (the project root)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- LLM Service Settings ---
# Secrets - should be in .env
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

# Non-secret parameters
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 4096

# --- Agent Settings ---
DB_PATH = "app/data/chatbot_analytics.db"
MAX_RETRIES_PER_STEP = 3

# --- Validation ---
# Ensure critical secrets are loaded, otherwise fail fast
if not GEMINI_API_KEY:
    raise ValueError(
        "Zorunlu ortam değişkeni bulunamadı: GOOGLE_API_KEY. "
        "Lütfen .env dosyanızı kontrol edin."
    )
if not GEMINI_MODEL_NAME:
    raise ValueError(
        "Zorunlu ortam değişkeni bulunamadı: GEMINI_MODEL_NAME. "
        "Lütfen .env dosyanızı kontrol edin."
    )