"""
Парсер Fedresurs.ru — данные по банкротству по ИНН.

USE_CAMOUFOX_PARSER=true: Camoufox (Firefox-based anti-detect, рекомендуется).
USE_TOR_PARSER=true: Tor + FlareSolverr + undetected-chromedriver.
USE_TOR_PARSER=false: nodriver (резерв).

Алгоритм (из ТЗ):
1. Вставить ИНН в колонку поиска
2. Пройти по стрелочке «Вся информация»
3. На вкладке «Сведения о банкротстве» — № дела и последняя дата
"""
import asyncio
import logging
from datetime import date
from typing import NamedTuple, Optional

from src.config import (
    CHROME_BINARY_PATH,
    FLARESOLVERR_URL,
    HEADLESS,
    TOR_CONTROL_PORT,
    TOR_PROXY,
    USE_CAMOUFOX_PARSER,
    USE_TOR_PARSER,
)
from src.utils.agents import get_random_agent

logger = logging.getLogger(__name__)


class FedresursData(NamedTuple):
    """Результат парсинга Fedresurs."""

    inn: str
    case_number: Optional[str]
    last_date: Optional[date]


def _create_parser(user_agent: Optional[str] = None):
    """Создаёт парсер в зависимости от USE_CAMOUFOX_PARSER и USE_TOR_PARSER."""
    agent = user_agent or get_random_agent()
    if USE_CAMOUFOX_PARSER:
        from src.parsers.fedresurs_camoufox import FedresursCamoufoxParser

        return FedresursCamoufoxParser(user_agent=agent), False
    elif USE_TOR_PARSER:
        from src.parsers.fedresurs_tor import FedresursTorParser

        return FedresursTorParser(
            tor_proxy=TOR_PROXY,
            tor_control_port=TOR_CONTROL_PORT,
            flaresolverr_url=FLARESOLVERR_URL,
            headless=HEADLESS,
            chrome_path=CHROME_BINARY_PATH or None,
            user_agent=agent,
        ), True
    else:
        from src.parsers.fedresurs_nodriver import FedresursNodriverParser

        return FedresursNodriverParser(user_agent=agent), False


class FedresursParser:
    """
    Парсер Fedresurs.ru по ИНН.

    USE_CAMOUFOX_PARSER=true: Camoufox (рекомендуется при блокировках).
    USE_TOR_PARSER=true: Tor + curl_cffi + undetected-chromedriver + FlareSolverr.
    USE_TOR_PARSER=false: nodriver (резерв).
    """

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or get_random_agent()
        self._parser, self._use_tor = _create_parser(self.user_agent)

    async def parse(self, inn: str) -> FedresursData:
        """Парсит данные по банкротству для указанного ИНН."""
        if self._use_tor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._parser.parse, inn)
            return FedresursData(
                inn=result["inn"],
                case_number=result["case_number"],
                last_date=result["last_date"],
            )
        else:
            return await self._parser.parse(inn)

    async def close(self) -> None:
        """Закрытие ресурсов."""
        if hasattr(self._parser, "close"):
            await self._parser.close()
