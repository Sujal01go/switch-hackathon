"""Configuration settings for the Multi-Agent Software Engineering Team."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Switch server and communication settings
SWITCH_SERVER_URL = os.getenv("SWITCH_SERVER_URL", "http://localhost:55009")
SWITCH_ROOM_ID = os.getenv("SWITCH_ROOM_ID", "b58680a3-370e-468b-abf7-1e66a813599f")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-5449527038")
TELEGRAM_BOT_NAME = os.getenv("TELEGRAM_BOT_NAME", "@Cosmic_destroyer_bot")

# Connected agent executables
CODEX_BINARY_PATH = os.getenv("CODEX_BINARY_PATH", r"D:\Codex\bin\codex.EXE")
CURSOR_BINARY_PATH = os.getenv("CURSOR_BINARY_PATH", r"C:\Users\LENOVO\AppData\Local\cursor-agent\agent.CMD")
OPENCODE_BINARY_PATH = os.getenv("OPENCODE_BINARY_PATH", r"D:\OpenCode\node_modules\opencode-ai\bin\opencode.EXE")

# Storage & Database
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "tasks.db"))

# Target Repository (sample repo for testing)
DEFAULT_REPO_PATH = BASE_DIR / "sample_repo"

# Safety & Governance
MAX_REVIEW_CYCLES = int(os.getenv("MAX_REVIEW_CYCLES", "3"))
REQUIRE_HUMAN_APPROVAL = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() in ("true", "1", "yes")

# Optional GitHub Integration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

