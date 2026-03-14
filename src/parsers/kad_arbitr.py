"""
Парсер Kad.arbitr.ru — данные по электронному делу по № дела.

Алгоритм (из ТЗ):
1. Вставить № дела в колонку поиска
2. Перейти по № дела
3. На вкладке «Электронное дело» — последняя дата, документ, наименование документа
"""
import logging
from datetime import date, datetime
from typing import NamedTuple, Optional

from src.parsers.base import BaseParser

logger = logging.getLogger(__name__)

KAD_ARBITR_URL = "https://kad.arbitr.ru/"


class KadArbitrData(NamedTuple):
    """Результат парсинга Kad.arbitr."""

    case_number: str
    last_date: Optional[date]
    document_name: Optional[str]
    document_path: Optional[str] = None


class KadArbitrParser(BaseParser):
    """Парсер Kad.arbitr.ru по № дела."""

    async def parse(self, case_number: str) -> KadArbitrData:
        """
        Парсит данные по электронному делу.

        Returns:
            KadArbitrData с last_date и document_name
        """
        await self._delay_between_requests()
        return await self._retry(self._do_parse, case_number)

    async def _do_parse(self, case_number: str) -> KadArbitrData:
        """Async реализация парсинга с nodriver."""
        try:
            browser = await self._create_browser()
            try:
                tab = await browser.get(KAD_ARBITR_URL)
                await tab

                try:
                    await tab.verify_cf()
                except Exception:
                    pass

                await tab.sleep(1.5)

                # Поле поиска № дела
                el = None
                for sel in [
                    "input[placeholder*='Номер дела']",
                    "input[name*='number']",
                    "input",
                ]:
                    el = await self._find_element(tab, sel)
                    if el:
                        break
                if not el:
                    el = await self._wait_for_selector(tab, "input", timeout=15)
                await el.clear_input()
                await el.send_keys(case_number)
                await tab.sleep(1)

                # Кнопка поиска
                search_btn = await tab.find("Найти", best_match=True)
                if not search_btn:
                    raise ValueError("Кнопка 'Найти' не найдена")
                await self._before_action(tab)
                await search_btn.click()
                await tab.sleep(3)

                # Ссылка на дело (по XPath)
                case_link = await tab.xpath(f"//a[contains(text(),'{case_number}')]", timeout=15)
                if not case_link:
                    raise ValueError(f"Дело {case_number} не найдено")
                await self._before_action(tab)
                await case_link.click()
                await tab.sleep(3)

                # Вкладка "Электронное дело"
                electronic_tab = await tab.find("Электронное дело", best_match=True)
                if not electronic_tab:
                    raise ValueError("Вкладка 'Электронное дело' не найдена")
                await self._before_action(tab)
                await electronic_tab.click()
                await tab.sleep(2)

                # Последняя дата
                last_date_el = await self._find_element(tab, "table tr:last-child td:first-child")
                last_date_str = (last_date_el.text or "").strip() if last_date_el else None
                last_date = None
                if last_date_str:
                    try:
                        last_date = datetime.strptime(last_date_str, "%d.%m.%Y").date()
                    except ValueError:
                        logger.warning(
                            "Не удалось распарсить дату '%s' для дела %s",
                            last_date_str,
                            case_number,
                        )

                # Наименование документа
                document_el = await self._find_element(tab, "table tr:last-child td:nth-child(2)")
                document_name = (
                    (document_el.text or "").strip() or None
                    if document_el
                    else None
                )

                return KadArbitrData(
                    case_number=case_number,
                    last_date=last_date,
                    document_name=document_name,
                    document_path=None,
                )
            finally:
                browser.stop()
        except Exception as e:
            logger.warning(
                "Дело не найдено или ошибка парсинга %s: %s",
                case_number,
                e,
            )
            return KadArbitrData(
                case_number=case_number,
                last_date=None,
                document_name=None,
                document_path=None,
            )
