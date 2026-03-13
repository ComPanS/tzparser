"""
Парсер Kad.arbitr.ru на Camoufox (USE_CAMOUFOX_PARSER=true).

Camoufox — Firefox-based anti-detect, обходит Cloudflare и тяжёлые антиботы.
"""
import logging
import random
from datetime import date, datetime
from typing import NamedTuple, Optional

from src.parsers.base_camoufox import BaseCamoufoxParser

logger = logging.getLogger(__name__)

KAD_ARBITR_URL = "https://kad.arbitr.ru/"


class KadArbitrData(NamedTuple):
    """Результат парсинга Kad.arbitr."""

    case_number: str
    last_date: Optional[date]
    document_name: Optional[str]


class KadArbitrCamoufoxParser(BaseCamoufoxParser):
    """Парсер Kad.arbitr.ru по № дела (Camoufox)."""

    async def parse(self, case_number: str) -> KadArbitrData:
        """
        Парсит данные по электронному делу.

        Returns:
            KadArbitrData с last_date и document_name
        """
        await self._delay_between_requests()
        return await self._retry(self._do_parse, case_number)

    async def _do_parse(self, case_number: str) -> KadArbitrData:
        """Async реализация парсинга с Camoufox."""
        page = None
        try:
            browser = await self._get_browser()
            page = await browser.new_page()
            await page.goto(KAD_ARBITR_URL)
            await self._sleep(page, 1.5)

            # Поле поиска № дела
            el = None
            for sel in [
                "input[placeholder*='Номер дела']",
                "input[name*='number']",
                "input",
            ]:
                el = await self._find_element(page, sel)
                if el:
                    break
            if not el:
                el = await self._wait_for_selector(page, "input", timeout=15)
            await el.fill("")
            await el.type(case_number, delay=random.randint(80, 200))
            await self._sleep(page, 1)

            # Кнопка поиска
            search_btn = await self._find_by_text(page, "Найти")
            if not search_btn:
                raise ValueError("Кнопка 'Найти' не найдена")
            await self._before_action(page)
            await search_btn.click()
            await self._sleep(page, 3)

            # Ссылка на дело (по XPath)
            case_link = await self._wait_for_xpath(
                page, f"//a[contains(text(),'{case_number}')]", timeout=15
            )
            if not case_link:
                raise ValueError(f"Дело {case_number} не найдено")
            await self._before_action(page)
            await case_link.click()
            await self._sleep(page, 3)

            # Вкладка "Электронное дело"
            electronic_tab = await self._find_by_text(page, "Электронное дело")
            if not electronic_tab:
                raise ValueError("Вкладка 'Электронное дело' не найдена")
            await self._before_action(page)
            await electronic_tab.click()
            await self._sleep(page, 2)

            # Последняя дата
            last_date_el = await self._find_element(page, "table tr:last-child td:first-child")
            last_date_str = None
            if last_date_el:
                raw = await last_date_el.inner_text()
                last_date_str = (raw or "").strip() or None
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
            document_el = await self._find_element(page, "table tr:last-child td:nth-child(2)")
            document_name = None
            if document_el:
                raw = await document_el.inner_text()
                document_name = (raw or "").strip() or None

            return KadArbitrData(
                case_number=case_number,
                last_date=last_date,
                document_name=document_name,
            )
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
            )
        finally:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
