"""
Конфигурация приложения.

Поддерживает переключение между SQLite (по умолчанию) и PostgreSQL
через переменную окружения DATABASE_URL.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# База данных
_default_db_path = Path(__file__).parent.parent / "data" / "parser.db"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_default_db_path.as_posix()}",
)

# Парсинг
CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))
DELAY_BETWEEN_REQUESTS_MIN = float(os.getenv("DELAY_MIN", "8.0"))
DELAY_BETWEEN_REQUESTS_MAX = float(os.getenv("DELAY_MAX", "15.0"))
SKIP_INITIAL_DELAY = os.getenv("SKIP_INITIAL_DELAY", "false").lower() in ("1", "true", "yes")
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2.0"))
PAGE_TIMEOUT_MS = int(os.getenv("PAGE_TIMEOUT_MS", "30000"))
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")

# Обход блокировок (прокси, путь к Chrome в Docker)
PROXY_URL = os.getenv("PROXY_URL")  # http://user:pass@host:port или socks5://...
CHROME_BINARY_PATH = os.getenv("CHROME_BINARY_PATH", "").strip()  # /usr/bin/chromium в Docker

# Camoufox — Firefox-based anti-detect (рекомендуется при блокировках)
USE_CAMOUFOX_PARSER = os.getenv("USE_CAMOUFOX_PARSER", "false").lower() in ("1", "true", "yes")

# Tor + FlareSolverr (единый способ обхода блокировки fedresurs.ru)
USE_TOR_PARSER = os.getenv("USE_TOR_PARSER", "true").lower() in ("1", "true", "yes")
TOR_PROXY = os.getenv("TOR_PROXY", "socks5://127.0.0.1:9050")
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191/v1").rstrip("/")

# Пути
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DEFAULT_XLSX_PATH = DATA_DIR / "inns.xlsx"
KAD_ARBITR_DOWNLOADS_DIR = DATA_DIR / "downloaded_files"

# xlsx
XLSX_SHEET_NAME = os.getenv("XLSX_SHEET_NAME", "Sheet1")
XLSX_INN_COLUMN = os.getenv("XLSX_INN_COLUMN", "ИНН")
