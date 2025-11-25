from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configuration settings
# Prefer an explicit DATABASE_URL; fall back to SUPABASE_URL for backwards compatibility.
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")

# API key lists (comma separated) expected in .env
GEMINI_API_LIST = [i for i in os.getenv("GEMINI_API_LIST", "").split(",") if i]
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_TYPE", "gemini-2.5-flash")
OPENAI_API_LIST = [i for i in os.getenv("OPENAI_API_LIST", "").split(",") if i]
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_TYPE", "gpt-4o-mini")

ROOT = os.path.dirname(os.path.dirname(__file__))
