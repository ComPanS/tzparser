"""
Скрипт для проверки только парсера Fedresurs.

Запуск:
    python scripts/test_fedresurs.py
    python scripts/test_fedresurs.py 231138771115
    python scripts/test_fedresurs.py 231138771115 --headed   # видимый браузер
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Включить видимый браузер (до импорта, если передан --headed)
if "--headed" in sys.argv:
    os.environ["HEADLESS"] = "false"

from src.parsers.fedresurs import FedresursParser
from src.utils.agents import get_random_agent


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    inn = args[0] if args else "231138771115"
    print(f"Парсинг Fedresurs для ИНН: {inn}")
    print("-" * 40)

    parser = FedresursParser(user_agent=get_random_agent())
    try:
        result = await parser.parse(inn)
        print(f"ИНН:         {result.inn}")
        print(f"№ дела:      {result.case_number}")
        print(f"Последняя дата: {result.last_date}")
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(main())
