"""
Парсер Kad.arbitr.ru — данные по электронному делу по № дела (Camoufox).
"""

import logging
import random
from datetime import date, datetime
from typing import NamedTuple, Optional
from urllib.parse import urljoin

from src.parsers.base_camoufox import BaseCamoufoxParser

logger = logging.getLogger(__name__)

KAD_ARBITR_URL = "https://kad.arbitr.ru/"
KAD_ARBITR_BASE = "https://kad.arbitr.ru"


class KadArbitrData(NamedTuple):
    """Результат парсинга Kad.arbitr."""

    case_number: str
    last_date: Optional[date]
    document_name: Optional[str]
    document_path: Optional[str] = None


class KadArbitrParser(BaseCamoufoxParser):
    """Парсер Kad.arbitr.ru по № дела (Camoufox)."""

    def _get_camoufox_kwargs(self) -> dict:
        """Параметры для Kad.arbitr (block_webgl/webrtc для обхода защиты)."""
        kwargs = super()._get_camoufox_kwargs()
        kwargs["block_webgl"] = True
        kwargs["block_webrtc"] = True
        return kwargs

    async def parse(self, case_number: str) -> KadArbitrData:
        """
        Парсит данные по электронному делу.

        Returns:
            KadArbitrData с last_date, document_name и document_path
        """
        await self._delay_between_requests()
        return await self._retry(self._do_parse, case_number)

    async def _do_parse(self, case_number: str) -> KadArbitrData:
        """Async реализация парсинга с Camoufox."""
        page = None
        target_page = None
        try:
            browser = await self._get_browser()
            page = await browser.new_page()
            await page.goto(KAD_ARBITR_URL)
            await self._sleep(page, 1.5)

            # Поле поиска № дела в div#sug-cases
            el = await self._find_element(page, "#sug-cases input")
            if not el:
                el = await self._wait_for_selector(page, "#sug-cases input", timeout=15)
            await el.scroll_into_view_if_needed()
            await self._sleep(page, random.uniform(0.2, 0.5))
            await el.hover()
            await self._sleep(page, random.uniform(0.3, 0.7))
            await el.click()
            await page.wait_for_timeout(int(random.uniform(200, 500)))
            await el.fill("")
            await page.wait_for_timeout(int(random.uniform(150, 400)))
            for char in case_number:
                await el.type(char, delay=random.randint(60, 280))
                if random.random() < 0.1:
                    await page.wait_for_timeout(int(random.uniform(400, 1200)))
                elif random.random() < 0.2:
                    await page.wait_for_timeout(int(random.uniform(150, 450)))
            await self._sleep(page, random.uniform(0.5, 1.2))

            # === Таблица результатов: первый tr -> первый td -> a -> переход по ссылке ===
            await self._before_action(page)
            await el.press("Enter")
            await self._sleep(page, 3)

            await page.locator("#b-cases tbody tr").first.wait_for(
                state="visible", timeout=15000
            )
            case_link = (
                page.locator("#b-cases tbody tr")
                .first.locator("td")
                .first.locator("a")
                .first
            )
            await self._before_action(page)
            await case_link.hover()
            await page.wait_for_timeout(int(random.uniform(200, 500)))

            # Клик по ссылке — ждём навигацию или новую вкладку
            target_page = page
            link_target = await case_link.get_attribute("target")
            if link_target == "_blank":
                async with page.expect_popup(timeout=15000) as popup_info:
                    await case_link.click()
                target_page = await popup_info.value
            else:
                try:
                    async with page.expect_navigation(timeout=15000):
                        await case_link.click()
                except Exception:
                    # Таймаут — возможно SPA, клик уже выполнен
                    pass

            await target_page.wait_for_load_state("domcontentloaded", timeout=20000)
            await self._sleep(target_page, 5)

            # Вкладка "Электронное дело" — ищем по тексту
            electronic_tab = target_page.get_by_text("Электронное дело", exact=False).first
            if await electronic_tab.count() == 0:
                # Возможно контент в iframe
                for frame in target_page.frames:
                    if frame != target_page.main_frame:
                        electronic_tab = frame.get_by_text("Электронное дело", exact=False).first
                        if await electronic_tab.count() > 0:
                            target_page = frame
                            break
            await electronic_tab.wait_for(state="visible", timeout=15000)
            await self._before_action(target_page)
            await electronic_tab.click()
            await self._sleep(target_page, 2)

            # ul.b-case-chrono-ed.js-case-chrono-ed — первый li с [Подписано]
            ul = target_page.locator("ul.b-case-chrono-ed.js-case-chrono-ed")
            await ul.wait_for(state="visible", timeout=15000)
            li_count = await ul.locator("li").count()
            target_li = None
            for i in range(li_count):
                li = ul.locator("li").nth(i)
                sign_span = li.locator("span.g-valid_sign.js-signers-rollover")
                if await sign_span.count() > 0:
                    text = await sign_span.first.inner_text()
                    if text and "Подписано" in text:
                        target_li = li
                        break

            if not target_li:
                logger.warning(
                    "Документ с [Подписано] не найден для дела %s",
                    case_number,
                )
                return KadArbitrData(
                    case_number=case_number,
                    last_date=None,
                    document_name=None,
                    document_path=None,
                )

            # Дата из первого p
            last_date = None
            p_el = target_li.locator("p").first
            if await p_el.count() > 0:
                raw = await p_el.inner_text()
                last_date_str = (raw or "").strip()
                if last_date_str:
                    try:
                        last_date = datetime.strptime(last_date_str, "%d.%m.%Y").date()
                    except ValueError:
                        logger.warning(
                            "Не удалось распарсить дату '%s' для дела %s",
                            last_date_str,
                            case_number,
                        )

            # Наименование документа из текста ссылки, href — для document_path
            doc_link = target_li.locator("a[href]").first
            document_name = None
            href = None
            if await doc_link.count() > 0:
                raw = await doc_link.inner_text()
                document_name = (raw or "").strip() or None
                href = await doc_link.get_attribute("href")

            # Ссылка на документ (без скачивания)
            document_path = None
            if href:
                document_path = urljoin(KAD_ARBITR_BASE, href)

            return KadArbitrData(
                case_number=case_number,
                last_date=last_date,
                document_name=document_name,
                document_path=document_path,
            )
        except Exception as e:
            err_msg = str(e).split("\n")[0] if str(e) else str(type(e).__name__)
            logger.warning(
                "Дело не найдено или ошибка парсинга %s: %s",
                case_number,
                err_msg,
            )
            return KadArbitrData(
                case_number=case_number,
                last_date=None,
                document_name=None,
                document_path=None,
            )
        finally:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
            # Закрыть вкладку-попап, если открылась
            if (
                target_page is not None
                and target_page != page
                and hasattr(target_page, "close")
            ):
                try:
                    await target_page.close()
                except Exception:
                    pass
