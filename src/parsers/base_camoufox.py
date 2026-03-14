"""
Базовый класс парсера с Camoufox.

Camoufox — Firefox-based anti-detect браузер с Playwright API.
- Спофинг fingerprint'ов на уровне C++ (внутри движка Firefox)
- Имитация человеческого поведения (Bezier-кривая мыши, случайные задержки)
- Обход Cloudflare, DataDome, PerimeterX, Akamai

Реализует обёртку над Playwright API, совместимую с BaseParser.
"""

import asyncio
import logging
import random
from typing import Any, Optional
from urllib.parse import urlparse

from src.config import (
    DELAY_BETWEEN_REQUESTS_MIN,
    DELAY_BETWEEN_REQUESTS_MAX,
    HEADLESS,
    PROXY_URL,
    RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
    SKIP_INITIAL_DELAY,
)
from src.utils.agents import get_random_agent

logger = logging.getLogger(__name__)


def _parse_proxy(proxy_url: Optional[str]) -> Optional[dict]:
    """Парсит PROXY_URL в формат Playwright proxy."""
    if not proxy_url or not proxy_url.strip():
        return None
    try:
        parsed = urlparse(proxy_url)
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 80}"
        result: dict[str, Any] = {"server": server}
        if parsed.username:
            result["username"] = parsed.username
        if parsed.password:
            result["password"] = parsed.password
        return result
    except Exception:
        return None


class BaseCamoufoxParser:
    """Базовый класс парсера с Camoufox (Playwright API)."""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or get_random_agent()
        self._browser = None
        self._browser_cm = None

    def _get_camoufox_kwargs(self) -> dict:
        """Параметры для AsyncCamoufox."""
        kwargs: dict[str, Any] = {
            "humanize": True,
            "headless": HEADLESS,
        }
        proxy = _parse_proxy(PROXY_URL)
        if proxy:
            kwargs["proxy"] = proxy
            kwargs["geoip"] = True
        return kwargs

    def _create_browser(self):
        """Создаёт браузер Camoufox. Возвращает async context manager."""
        from camoufox.async_api import AsyncCamoufox

        return AsyncCamoufox(**self._get_camoufox_kwargs())

    async def _get_browser(self):
        """Возвращает браузер, создавая при первом вызове. Переиспользуется между parse()."""
        if self._browser is None:
            self._browser_cm = self._create_browser()
            self._browser = await self._browser_cm.__aenter__()
        return self._browser

    async def _sleep(self, page, seconds: float) -> None:
        """Задержка (Playwright использует миллисекунды)."""
        await page.wait_for_timeout(int(seconds * 1000))

    async def _wait_for_selector(self, page, selector: str, timeout: int = 30):
        """Ожидание появления элемента по CSS."""
        locator = page.locator(selector)
        await locator.wait_for(state="visible", timeout=timeout * 1000)
        return locator.first

    async def _wait_for_xpath(self, page, xpath: str, timeout: int = 30):
        """Ожидание появления элемента по XPath."""
        locator = page.locator(f"xpath={xpath}")
        await locator.wait_for(state="visible", timeout=timeout * 1000)
        return locator.first

    async def _find_element(self, page, selector: str):
        """Поиск элемента по CSS (возвращает None если не найден)."""
        try:
            locator = page.locator(selector)
            if await locator.count() > 0:
                return locator.first
        except Exception:
            pass
        return None

    async def _find_element_xpath(self, page, xpath: str):
        """Поиск элемента по XPath (возвращает None если не найден)."""
        try:
            locator = page.locator(f"xpath={xpath}")
            if await locator.count() > 0:
                return locator.first
        except Exception:
            pass
        return None

    async def _find_elements(self, page, selector: str):
        """Поиск всех элементов по CSS."""
        locator = page.locator(selector)
        count = await locator.count()
        return [locator.nth(i) for i in range(count)]

    async def _find_by_text(self, page, text: str, best_match: bool = True):
        """Поиск элемента по тексту."""
        locator = page.get_by_text(text)
        if await locator.count() > 0:
            return locator.first
        return None

    async def _before_action(self, page) -> None:
        """Случайные движения и скролл перед действием."""
        if random.random() < 0.4:
            delta = random.randint(-300, 300)
            if delta != 0:
                await page.mouse.wheel(0, delta)
        await page.wait_for_timeout(int(random.uniform(100, 400)))

    async def _human_scroll_down(self, page, total_px: int = 700) -> None:
        """
        Плавная прокрутка вниз — много мелких шагов для естественного движения.
        """
        steps = random.randint(18, 28)
        base_delta = total_px / steps
        for i in range(steps):
            delta = int(base_delta * random.uniform(0.7, 1.3))
            delta = max(12, min(55, delta))
            await page.mouse.wheel(0, delta)
            await page.wait_for_timeout(int(random.uniform(18, 45)))

    async def _human_type(self, page, selector: str, text: str) -> None:
        """Хаотичный ввод с задержками."""
        await self._before_action(page)
        el = await self._wait_for_selector(page, selector, timeout=30)
        if not el:
            raise ValueError(f"Элемент не найден: {selector}")
        await el.click()
        await page.wait_for_timeout(int(random.uniform(300, 800)))
        for char in text:
            await el.type(char, delay=random.randint(80, 350))
            if random.random() < 0.08:
                await page.wait_for_timeout(int(random.uniform(500, 1800)))
            elif random.random() < 0.15:
                await page.wait_for_timeout(int(random.uniform(200, 500)))

    async def _click_selector(self, page, selector: str, timeout: int = 30) -> None:
        """Клик по CSS селектору."""
        await self._before_action(page)
        el = await self._wait_for_selector(page, selector, timeout=timeout)
        if not el:
            raise ValueError(f"Элемент не найден: {selector}")
        await el.scroll_into_view_if_needed()
        await page.wait_for_timeout(300)
        await el.click()

    async def _click_xpath(self, page, xpath: str, timeout: int = 30) -> None:
        """Клик по XPath."""
        await self._before_action(page)
        el = await self._wait_for_xpath(page, xpath, timeout=timeout)
        if not el:
            raise ValueError(f"Элемент не найден: {xpath}")
        await el.scroll_into_view_if_needed()
        await page.wait_for_timeout(300)
        await el.click()

    async def _delay_between_actions(self) -> None:
        """Задержка между действиями внутри парсинга (1–3 сек)."""
        await asyncio.sleep(random.uniform(1.0, 3.0))

    async def _delay_between_requests(self) -> None:
        """Случайная пауза 8–15 сек + random. SKIP_INITIAL_DELAY=true — для тестов."""
        if SKIP_INITIAL_DELAY:
            return
        delay = random.uniform(
            DELAY_BETWEEN_REQUESTS_MIN,
            DELAY_BETWEEN_REQUESTS_MAX,
        )
        jitter = random.uniform(0, 3)
        await asyncio.sleep(delay + jitter)

    async def _retry(self, async_func, *args, **kwargs):
        """Выполняет async-функцию с retry."""
        last_error = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                return await async_func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if "captcha" in str(e).lower():
                    logger.warning("Обнаружена CAPTCHA или блокировка. Пауза 60 сек.")
                    await asyncio.sleep(60)
                if attempt < RETRY_ATTEMPTS - 1:
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Попытка %d/%d не удалась: %s. Повтор через %.1f сек.",
                        attempt + 1,
                        RETRY_ATTEMPTS,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
        raise last_error

    async def close(self) -> None:
        """Закрытие браузера (если был создан)."""
        if self._browser_cm is not None:
            try:
                await self._browser_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Ошибка при закрытии браузера: %s", e)
            finally:
                self._browser = None
                self._browser_cm = None
