"""
Базовый класс парсера с nodriver.

nodriver — преемник undetected-chromedriver.
- Без chromedriver и Selenium, чистый CDP
- Свежий профиль каждый запуск (user_data_dir=None)
- Нет WebDriver-меток
- tab.verify_cf() для Cloudflare
- Полностью async

Реализует:
- uc.start() с browser_args против детекции
- Retry с экспоненциальной задержкой
- Поддержку прокси, пути к Chrome
"""

import asyncio
import logging
import random
import sys
from typing import Optional

import nodriver as uc

from src.config import (
    CHROME_BINARY_PATH,
    DELAY_BETWEEN_REQUESTS_MIN,
    DELAY_BETWEEN_REQUESTS_MAX,
    HEADLESS,
    PROXY_URL,
    RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
)
from src.utils.agents import get_random_agent

logger = logging.getLogger(__name__)

# Реалистичные viewport'ы
VIEWPORTS = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
]


class BaseParser:
    """Базовый класс парсера с nodriver (CDP, без Selenium)."""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or get_random_agent()

    async def _create_browser(self) -> uc.Browser:
        """Создаёт браузер nodriver (свежий профиль, anti-detection)."""
        vp = random.choice(VIEWPORTS)
        browser_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            f"--window-size={vp[0]},{vp[1]}",
        ]
        if self.user_agent:
            browser_args.append(f"--user-agent={self.user_agent}")

        if PROXY_URL:
            browser_args.append(f"--proxy-server={PROXY_URL}")

        kwargs = {
            "headless": HEADLESS,
            "browser_args": browser_args,
            "user_data_dir": None,  # свежий профиль каждый запуск
        }
        if CHROME_BINARY_PATH:
            kwargs["browser_executable_path"] = CHROME_BINARY_PATH
        return await uc.start(**kwargs)

    async def _wait_for_selector(self, tab: uc.Tab, selector: str, timeout: int = 30):
        """Ожидание появления элемента по CSS."""
        return await tab.select(selector, timeout=timeout)

    async def _wait_for_xpath(self, tab: uc.Tab, xpath: str, timeout: int = 30):
        """Ожидание появления элемента по XPath."""
        return await tab.xpath(xpath, timeout=timeout)

    async def _find_element(self, tab: uc.Tab, selector: str):
        """Поиск элемента по CSS (возвращает None если не найден)."""
        try:
            return await tab.select(selector, timeout=2)
        except Exception:
            return None

    async def _find_element_xpath(self, tab: uc.Tab, xpath: str):
        """Поиск элемента по XPath (возвращает None если не найден)."""
        try:
            return await tab.xpath(xpath, timeout=2)
        except Exception:
            return None

    async def _find_elements(self, tab: uc.Tab, selector: str):
        """Поиск всех элементов по CSS."""
        return await tab.select_all(selector)

    async def _find_by_text(self, tab: uc.Tab, text: str, best_match: bool = True):
        """Поиск элемента по тексту."""
        return await tab.find(text, best_match=best_match)

    async def _before_action(self, tab: uc.Tab) -> None:
        """Случайные движения и скролл перед действием."""
        if random.random() < 0.4:
            delta = random.randint(-300, 300)
            if delta != 0:
                await tab.scroll_down(delta)
        await tab.sleep(random.uniform(0.1, 0.4))

    async def _human_type(self, tab: uc.Tab, selector: str, text: str) -> None:
        """Хаотичный ввод с задержками."""
        await self._before_action(tab)
        el = await self._wait_for_selector(tab, selector, timeout=30)
        if not el:
            raise ValueError(f"Элемент не найден: {selector}")
        await el.click()
        await tab.sleep(random.uniform(0.3, 0.8))
        for char in text:
            await el.send_keys(char)
            await tab.sleep(random.uniform(0.08, 0.35))
            if random.random() < 0.08:
                await tab.sleep(random.uniform(0.5, 1.8))
            elif random.random() < 0.15:
                await tab.sleep(random.uniform(0.2, 0.5))

    async def _click_selector(
        self, tab: uc.Tab, selector: str, timeout: int = 30
    ) -> None:
        """Клик по CSS селектору."""
        await self._before_action(tab)
        el = await self._wait_for_selector(tab, selector, timeout=timeout)
        if not el:
            raise ValueError(f"Элемент не найден: {selector}")
        await el.scroll_into_view()
        await tab.sleep(0.3)
        await el.click()

    async def _click_xpath(self, tab: uc.Tab, xpath: str, timeout: int = 30) -> None:
        """Клик по XPath."""
        await self._before_action(tab)
        el = await self._wait_for_xpath(tab, xpath, timeout=timeout)
        if not el:
            raise ValueError(f"Элемент не найден: {xpath}")
        await el.scroll_into_view()
        await tab.sleep(0.3)
        await el.click()

    async def _delay_between_actions(self) -> None:
        """Задержка между действиями внутри парсинга (1–3 сек)."""
        await asyncio.sleep(random.uniform(1.0, 3.0))

    async def _delay_between_requests(self) -> None:
        """Случайная пауза 8–15 сек + random."""
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
        """Закрытие ресурсов (no-op: каждый browser создаётся и закрывается в parse)."""
        pass
