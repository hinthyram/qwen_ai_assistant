from pathlib import Path

APP_NAME = "Qwen AI Assistant"
MODEL = "qwen3.5:4b"

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

MEMORY_DB = BASE_DIR / "memory.db"

WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 760
