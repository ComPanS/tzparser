"""
Скрипт для проверки парсера Fedresurs через Camoufox.

Запуск:
    python scripts/test_camoufox.py
    python scripts/test_camoufox.py 231138771115
    python scripts/test_camoufox.py 231138771115 --headed   # видимый браузер

Перед запуском: pip install camoufox[geoip] && camoufox fetch
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Без паузы 8–15 сек перед стартом (для быстрого теста)
os.environ["SKIP_INITIAL_DELAY"] = "true"
# Включить видимый браузер (если передан --headed)
if "--headed" in sys.argv:
    os.environ["HEADLESS"] = "false"

from src.parsers.fedresurs import FedresursParser
from src.utils.agents import get_random_agent


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    inn = args[0] if args else "231138771115"
    print(f"Парсинг Fedresurs (Camoufox) для ИНН: {inn}")
    print("-" * 40)

    parser = FedresursParser(user_agent=get_random_agent())
    try:
        result = await parser.parse(inn)
        print(f"ИНН:            {result.inn}", flush=True)
        print(f"№ дела:         {result.case_number}", flush=True)
        last_date_str = result.last_date.strftime("%d.%m.%Y") if result.last_date else "—"
        print(f"Последняя дата: {last_date_str}", flush=True)
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(main())
