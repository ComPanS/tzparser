"""
Tor + FlareSolverr + undetected-chromedriver — единый способ обхода блокировки fedresurs.ru.

Три метода последовательно:
1. curl_cffi — самый быстрый, без браузера
2. undetected-chromedriver — полноценный браузер через Tor
3. FlareSolverr — обход Cloudflare и сложного JS
"""
import logging
import random
import re
import time
from datetime import date, datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

FEDRESURS_BASE = "https://fedresurs.ru"
FEDRESURS_SEARCH = "https://fedresurs.ru/search/entity"


class FedresursTorParser:
    """
    Парсер Fedresurs с обходом блокировки через Tor.

    Методы: curl_cffi → undetected_chrome → FlareSolverr.
    При неудаче — смена IP через Tor и повтор.
    """

    def __init__(
        self,
        tor_proxy: str = "socks5://127.0.0.1:9050",
        tor_control_port: int = 9051,
        flaresolverr_url: str = "http://localhost:8191/v1",
        headless: bool = True,
        chrome_path: Optional[str] = None,
        user_agent: Optional[str] = None,
        max_retries: int = 3,
    ):
        self.tor_proxy = {
            "http": tor_proxy,
            "https": tor_proxy,
        }
        self.tor_proxy_str = tor_proxy
        self.tor_control_port = tor_control_port
        self.flaresolverr_url = flaresolverr_url.rstrip("/")
        if not self.flaresolverr_url.endswith("/v1"):
            self.flaresolverr_url = f"{self.flaresolverr_url.rstrip('/')}/v1"
        self.headless = headless
        self.chrome_path = chrome_path
        self.user_agent = user_agent
        self.max_retries = max_retries

    def _renew_tor_ip(self) -> None:
        """Смена IP через Tor."""
        try:
            from stem import Signal
            from stem.control import Controller

            with Controller.from_port(port=self.tor_control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                logger.info("IP Tor изменён")
                time.sleep(5)
        except Exception as e:
            logger.warning("Ошибка смены IP Tor: %s", e)

    def _method_1_curl_cffi(self, url: str) -> Optional[str]:
        """Метод 1: curl_cffi (самый быстрый, без браузера)."""
        logger.info("Метод 1: curl_cffi...")
        try:
            from curl_cffi import requests as curl_requests

            response = curl_requests.get(
                url,
                impersonate="chrome120",
                proxies=self.tor_proxy,
                timeout=30,
            )
            if response.status_code == 200:
                logger.info("curl_cffi успешно получил страницу")
                return response.text
            logger.warning("curl_cffi вернул код %d", response.status_code)
        except ImportError:
            logger.warning("curl_cffi не установлен")
        except Exception as e:
            logger.warning("Ошибка curl_cffi: %s", e)
        return None

    def _method_2_undetected_chrome(self, inn: str) -> Optional[str]:
        """Метод 2: undetected-chromedriver (полноценный браузер через Tor)."""
        logger.info("Метод 2: undetected Chrome...")
        driver = None
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            options = uc.ChromeOptions()
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"--proxy-server={self.tor_proxy_str}")

            if self.headless:
                options.add_argument("--headless=new")

            if self.user_agent:
                options.add_argument(f"--user-agent={self.user_agent}")

            kwargs: Dict[str, Any] = {"options": options}
            if self.chrome_path:
                kwargs["browser_executable_path"] = self.chrome_path

            driver = uc.Chrome(**kwargs)

            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            driver.get(FEDRESURS_BASE)
            time.sleep(random.uniform(3, 6))

            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight * 0.3);"
            )
            time.sleep(random.uniform(1, 2))

            search_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[formcontrolname='searchString']")
                )
            )
            search_input.click()
            time.sleep(random.uniform(0.3, 0.8))
            for char in inn:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.08, 0.25))

            time.sleep(random.uniform(1, 2))

            search_btn = driver.find_element(By.CSS_SELECTOR, ".el-button")
            search_btn.click()
            time.sleep(random.uniform(3, 5))

            try:
                link = driver.find_element(
                    By.XPATH, "//*[contains(text(), 'Вся информация')]"
                )
                link.click()
                time.sleep(random.uniform(2, 4))
            except Exception:
                pass

            time.sleep(2)

            html = driver.page_source
            logger.info("undetected Chrome успешно получил страницу")
            return html

        except ImportError:
            logger.warning("undetected-chromedriver не установлен")
        except Exception as e:
            logger.warning("Ошибка undetected Chrome: %s", e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        return None

    def _method_3_flaresolverr(self, url: str) -> Optional[str]:
        """Метод 3: FlareSolverr (обход Cloudflare и сложного JS)."""
        logger.info("Метод 3: FlareSolverr...")
        try:
            import requests

            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000,
                "proxy": {"url": self.tor_proxy_str},
            }

            response = requests.post(
                self.flaresolverr_url,
                json=payload,
                timeout=120,
            )
            data = response.json()

            solution = data.get("solution", {})
            if solution.get("status") == 200:
                logger.info("FlareSolverr успешно получил страницу")
                return solution.get("response")
            logger.warning("FlareSolverr вернул ошибку: %s", data)
        except Exception as e:
            logger.warning("Ошибка FlareSolverr: %s", e)
        return None

    def _extract_data(self, html: str, inn: str) -> Dict[str, Any]:
        """Извлечение данных из HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        case_number = None
        case_elem = soup.select_one(".underlined.info-header")
        if case_elem:
            case_number = case_elem.get_text(strip=True)

        last_date = None
        wrappers = soup.select(".entity-card-bankruptcy-publication-wrapper")
        if wrappers:
            last_wrapper = wrappers[-1]
            underlined = last_wrapper.select(".underlined")
            if underlined:
                text = underlined[0].get_text(strip=True)
                match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
                if match:
                    try:
                        last_date = datetime.strptime(
                            match.group(1), "%d.%m.%Y"
                        ).date()
                    except ValueError:
                        pass

        return {
            "inn": inn,
            "case_number": case_number,
            "last_date": last_date,
        }

    def _is_valid_page(self, html: str) -> bool:
        """Проверка, что страница не блокировка."""
        if not html:
            return False
        bad = ("403", "Forbidden", "Access denied", "blocked")
        return not any(b in html for b in bad)

    def parse(self, inn: str) -> Dict[str, Any]:
        """
        Основной метод парсинга.

        Returns:
            dict с ключами inn, case_number, last_date
        """
        search_url = f"{FEDRESURS_SEARCH}?code={inn}"

        for attempt in range(self.max_retries):
            logger.info("Попытка %d/%d", attempt + 1, self.max_retries)

            html = self._method_1_curl_cffi(search_url)

            if not html:
                html = self._method_2_undetected_chrome(inn)

            if not html:
                html = self._method_3_flaresolverr(search_url)

            if html and self._is_valid_page(html):
                data = self._extract_data(html, inn)
                if data["case_number"] or data["last_date"]:
                    logger.info("Данные успешно получены")
                    return data
                logger.warning("Страница загружена, но данные не найдены")
            elif html:
                logger.warning("Получена страница с ошибкой (403/Forbidden)")

            if attempt < self.max_retries - 1:
                logger.info("Смена IP через Tor...")
                self._renew_tor_ip()
                time.sleep(random.uniform(10, 20))

        logger.warning("Все попытки исчерпаны для ИНН %s", inn)
        return {"inn": inn, "case_number": None, "last_date": None}
