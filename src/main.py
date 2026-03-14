"""
Точка входа и оркестрация парсинга.

Обрабатывает список ИНН из xlsx:
1. Fedresurs — получаем № дела и последнюю дату
2. Kad.arbitr — по каждому № дела получаем детали
Результаты сохраняются в две таблицы. Поддерживается докачка (resume).
"""
import argparse
import asyncio
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import (
    CONCURRENCY,
    DATA_DIR,
    DEFAULT_XLSX_PATH,
    LOGS_DIR,
)
from src.db.session import get_session_factory, init_db
from src.models.db_models import FedresursResult, KadArbitrResult
from src.parsers.fedresurs import FedresursParser
from src.parsers.kad_arbitr import KadArbitrParser
from src.utils.agents import get_random_agent
from src.utils.xlsx_reader import read_inns_from_xlsx


def setup_logging(log_dir: Optional[Path] = None) -> None:
    """Настраивает логирование в файл и stdout."""
    log_dir = log_dir or LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "parser.log"

    format_str = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(format_str)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def get_already_processed_inns(session: Session, today: date) -> Set[str]:
    """
    Возвращает множество ИНН, уже обработанных сегодня (для resume).
    """
    stmt = select(FedresursResult.inn).where(
        FedresursResult.parsed_at >= datetime.combine(today, datetime.min.time())
    )
    return set(session.scalars(stmt).all())


def get_already_processed_cases(session: Session, today: date) -> Set[str]:
    """Возвращает множество № дел, уже обработанных сегодня."""
    stmt = select(KadArbitrResult.case_number).where(
        KadArbitrResult.parsed_at >= datetime.combine(today, datetime.min.time())
    )
    return set(session.scalars(stmt).all())


async def process_inn(
    inn: str,
    fedresurs: FedresursParser,
    kad_arbitr: KadArbitrParser,
    session_factory,
    semaphore: asyncio.Semaphore,
    skip_fedresurs: Set[str],
    skip_kad: Set[str],
) -> None:
    """
    Обрабатывает один ИНН: Fedresurs -> Kad.arbitr, сохраняет в БД.
    """
    logger = logging.getLogger(__name__)
    async with semaphore:
        try:
            fed_data = await fedresurs.parse(inn)
            with session_factory() as session:
                session.add(
                    FedresursResult(
                        inn=fed_data.inn,
                        case_number=fed_data.case_number,
                        last_date=fed_data.last_date,
                    )
                )
                session.commit()
            logger.info("Fedresurs: ИНН %s -> № дела %s", inn, fed_data.case_number)

            if fed_data.case_number and fed_data.case_number not in skip_kad:
                kad_data = await kad_arbitr.parse(fed_data.case_number)
                with session_factory() as session:
                    session.add(
                        KadArbitrResult(
                            case_number=kad_data.case_number,
                            last_date=kad_data.last_date,
                            document_name=kad_data.document_name,
                            document_path=kad_data.document_path,
                        )
                    )
                    session.commit()
                doc_preview = (
                    (kad_data.document_name[:50] + "...")
                    if kad_data.document_name and len(kad_data.document_name) > 50
                    else (kad_data.document_name or "—")
                )
                logger.info("Kad.arbitr: № дела %s -> %s", fed_data.case_number, doc_preview)
        except Exception as e:
            logger.error("Ошибка при обработке ИНН %s: %s", inn, e, exc_info=True)


async def run_parser(xlsx_path: Path, resume: bool = True) -> None:
    """
    Запускает парсинг: читает ИНН, обрабатывает с ограничением конкурентности.
    """
    logger = logging.getLogger(__name__)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    inns = read_inns_from_xlsx(xlsx_path)
    if not inns:
        logger.warning("Список ИНН пуст")
        return

    session_factory = get_session_factory()
    skip_fedresurs: Set[str] = set()
    skip_kad: Set[str] = set()
    if resume:
        with session_factory() as session:
            today = date.today()
            skip_fedresurs = get_already_processed_inns(session, today)
            skip_kad = get_already_processed_cases(session, today)
        if skip_fedresurs:
            logger.info("Resume: пропуск %d уже обработанных ИНН", len(skip_fedresurs))

    inns_to_process = [i for i in inns if i not in skip_fedresurs]
    logger.info("К обработке: %d ИНН", len(inns_to_process))

    user_agent = get_random_agent()
    logger.info("Выбран User-Agent: %s...", user_agent[:50])

    fedresurs = FedresursParser(user_agent=user_agent)
    kad_arbitr = KadArbitrParser(user_agent=user_agent)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    try:
        tasks = [
            process_inn(
                inn,
                fedresurs,
                kad_arbitr,
                session_factory,
                semaphore,
                skip_fedresurs,
                skip_kad,
            )
            for inn in inns_to_process
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await fedresurs.close()
        await kad_arbitr.close()

    logger.info("Парсинг завершён")


def main() -> None:
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(description="Парсер данных по банкротству")
    parser.add_argument(
        "xlsx",
        nargs="?",
        default=str(DEFAULT_XLSX_PATH),
        help="Путь к xlsx файлу с ИНН",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Не использовать докачку (обработать все ИНН заново)",
    )
    parser.add_argument(
        "--log-dir",
        default=str(LOGS_DIR),
        help="Директория для логов",
    )
    args = parser.parse_args()

    setup_logging(Path(args.log_dir))
    xlsx_path = Path(args.xlsx)

    if not xlsx_path.exists():
        logging.getLogger(__name__).error("Файл не найден: %s", xlsx_path)
        sys.exit(1)

    asyncio.run(run_parser(xlsx_path, resume=not args.no_resume))


if __name__ == "__main__":
    main()
