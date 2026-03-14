"""
Скрипт для проверки парсера Kad.arbitr через Camoufox.

Запуск:
    python scripts/test_kad_camoufox.py
    python scripts/test_kad_camoufox.py А32-28873/2024
    python scripts/test_kad_camoufox.py А32-28873/2024 --headed   # видимый браузер

Перед запуском: pip install camoufox[geoip] && camoufox fetch
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["USE_CAMOUFOX_PARSER"] = "true"
os.environ["SKIP_INITIAL_DELAY"] = "true"
if "--headed" in sys.argv:
    os.environ["HEADLESS"] = "false"

from src.parsers.kad_arbitr_camoufox import KadArbitrCamoufoxParser
from src.utils.agents import get_random_agent


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    case_number = args[0] if args else "А32-28873/2024"
    print(f"Парсинг Kad.arbitr (Camoufox) для дела: {case_number}")
    print("-" * 50)

    parser = KadArbitrCamoufoxParser(user_agent=get_random_agent())
    try:
        result = await parser.parse(case_number)
        print(f"№ дела:           {result.case_number}", flush=True)
        last_date_str = result.last_date.strftime("%d.%m.%Y") if result.last_date else "—"
        print(f"Последняя дата:   {last_date_str}", flush=True)
        doc_preview = (
            (result.document_name[:60] + "...")
            if result.document_name and len(result.document_name) > 60
            else (result.document_name or "—")
        )
        print(f"Наименование:     {doc_preview}", flush=True)
        print(f"Путь к PDF:       {result.document_path or '—'}", flush=True)
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(main())
