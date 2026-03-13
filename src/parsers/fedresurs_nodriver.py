"""
Парсер Fedresurs.ru на nodriver (резервный, когда USE_TOR_PARSER=false).
"""
import logging
import re
from datetime import date, datetime
from typing import NamedTuple, Optional

from src.parsers.base import BaseParser

logger = logging.getLogger(__name__)

FEDRESURS_URL = "https://fedresurs.ru/"


class FedresursData(NamedTuple):
    """Результат парсинга Fedresurs."""

    inn: str
    case_number: Optional[str]
    last_date: Optional[date]


class FedresursNodriverParser(BaseParser):
    """Парсер Fedresurs.ru по ИНН (nodriver, без Tor)."""

    async def parse(self, inn: str) -> FedresursData:
        """Парсит данные по банкротству для указанного ИНН."""
        await self._delay_between_requests()
        return await self._retry(self._do_parse, inn)

    async def _do_parse(self, inn: str) -> FedresursData:
        """Async реализация парсинга с nodriver."""
        try:
            browser = await self._create_browser()
            try:
                tab = await browser.get(FEDRESURS_URL)
                await tab

                try:
                    await tab.verify_cf()
                except Exception:
                    pass

                await tab.sleep(1.5)

                search_input_selector = "input[formcontrolname='searchString']"
                await self._human_type(tab, search_input_selector, inn)
                await tab.sleep(1.5)

                await self._click_selector(tab, ".el-button", timeout=15)
                await tab.sleep(3)

                el = await tab.find("Вся информация", best_match=True)
                if not el:
                    raise ValueError("Элемент 'Вся информация' не найден")
                await self._before_action(tab)
                await el.scroll_into_view()
                await tab.sleep(0.3)
                await el.click()
                await tab.sleep(2)

                await tab.select(".entity-card-bankruptcy-publication-wrapper", timeout=30)
                await tab

                case_number_el = await self._find_element(tab, ".underlined.info-header")
                case_number = (
                    (case_number_el.text or "").strip() or None
                    if case_number_el
                    else None
                )

                last_date = None
                wrappers = await self._find_elements(tab, ".entity-card-bankruptcy-publication-wrapper")
                if wrappers:
                    last_wrapper = wrappers[-1]
                    underlined = await last_wrapper.query_selector_all(".underlined")
                    if underlined:
                        raw_text = underlined[0].text
                        if raw_text:
                            raw_text = raw_text.strip()
                            match = re.search(r"(\d{2}\.\d{2}\.\d{4})", raw_text)
                            if match:
                                date_str = match.group(1)
                                try:
                                    last_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                                except ValueError:
                                    logger.warning(
                                        "Не удалось распарсить дату '%s' для ИНН %s",
                                        raw_text,
                                        inn,
                                    )

                return FedresursData(
                    inn=inn,
                    case_number=case_number,
                    last_date=last_date,
                )
            finally:
                browser.stop()
        except Exception as e:
            logger.warning("ИНН не найден или ошибка парсинга %s: %s", inn, e)
            return FedresursData(inn=inn, case_number=None, last_date=None)
