"""
Парсер Fedresurs.ru — данные по банкротству по ИНН (Camoufox).

Алгоритм (из ТЗ):
1. Вставить ИНН в колонку поиска
2. Пройти по стрелочке «Вся информация»
3. На вкладке «Сведения о банкротстве» — № дела и последняя дата
"""
import logging
import random
import re
from datetime import date, datetime
from typing import NamedTuple, Optional

from src.parsers.base_camoufox import BaseCamoufoxParser
from src.utils.agents import get_random_agent

logger = logging.getLogger(__name__)

FEDRESURS_URL = "https://fedresurs.ru/"


class FedresursData(NamedTuple):
    """Результат парсинга Fedresurs."""

    inn: str
    case_number: Optional[str]
    last_date: Optional[date]


class FedresursParser(BaseCamoufoxParser):
    """Парсер Fedresurs.ru по ИНН (Camoufox)."""

    def __init__(self, user_agent: Optional[str] = None):
        super().__init__(user_agent=user_agent or get_random_agent())

    async def parse(self, inn: str) -> FedresursData:
        """Парсит данные по банкротству для указанного ИНН."""
        await self._delay_between_requests()
        return await self._retry(self._do_parse, inn)

    async def _do_search_and_click_all_info(self, page, inn: str) -> bool:
        """
        Выполняет поиск и клик «Вся информация».
        Возвращает True при успехе, False при неудаче (overlay перехватывает клик).
        """
        search_input_selector = "input[formcontrolname='searchString']"
        await self._human_type(page, search_input_selector, inn)
        await self._sleep(page, 1.5)

        await self._click_selector(page, ".el-button", timeout=15)
        await self._sleep(page, 2)

        # Ждём исчезновения overlay page-loading
        try:
            await page.locator(".page-loading").wait_for(state="hidden", timeout=15000)
        except Exception:
            pass
        await self._sleep(page, 1)

        el = await self._find_by_text(page, "Вся информация")
        if not el:
            return False
        await self._before_action(page)
        await el.scroll_into_view_if_needed()
        await self._sleep(page, 0.3)

        try:
            await el.click(timeout=10000)
            return True
        except Exception:
            return False

    async def _do_parse(self, inn: str) -> FedresursData:
        """Async реализация парсинга с Camoufox."""
        page = None
        try:
            browser = await self._get_browser()
            page = await browser.new_page()
            await page.goto(FEDRESURS_URL)
            await self._sleep(page, 1.5)

            # Поиск + клик «Вся информация»; при неудаче — обновить и повторить 1 раз
            ok = await self._do_search_and_click_all_info(page, inn)
            if not ok:
                logger.info("Overlay перехватил клик, обновляю страницу и повторяю 1 раз...")
                await page.goto(FEDRESURS_URL)
                await self._sleep(page, 2)
                ok = await self._do_search_and_click_all_info(page, inn)
            if not ok:
                raise ValueError("Элемент 'Вся информация' не найден или overlay блокирует клик")

            await self._sleep(page, 5)

            # Плавная хаотичная прокрутка к блоку банкротства
            await self._human_scroll_down(page, total_px=random.randint(600, 950))

            # Прокрутка к блоку банкротства
            bankruptcy_locator = page.locator("entity-card-bankruptcy-publication-wrapper")
            await bankruptcy_locator.first.wait_for(state="attached", timeout=60000)
            await bankruptcy_locator.first.scroll_into_view_if_needed()
            await self._sleep(page, 0.5)

            # № дела в <a class="underlined info-header">
            case_number_el = await self._find_element(page, "a.underlined.info-header")
            case_number = None
            if case_number_el:
                await case_number_el.scroll_into_view_if_needed()
                await self._sleep(page, 0.2)
                raw = await case_number_el.inner_text()
                case_number = (raw or "").strip() or None

            last_date = None
            wrappers = await self._find_elements(page, "entity-card-bankruptcy-publication-wrapper")
            if wrappers:
                first_wrapper = wrappers[0]
                await first_wrapper.scroll_into_view_if_needed()
                await self._sleep(page, 0.2)
                underlined = first_wrapper.locator("a.underlined")
                if await underlined.count() > 0:
                    raw_text = await underlined.first.inner_text()
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
        except Exception as e:
            err_msg = str(e).split("\n")[0] if str(e) else str(type(e).__name__)
            logger.warning("Номер дела не найден для ИНН %s: %s", inn, err_msg)
            return FedresursData(inn=inn, case_number=None, last_date=None)
        finally:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
