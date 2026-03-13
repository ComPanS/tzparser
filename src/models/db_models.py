"""
Модели SQLAlchemy 2.0 для хранения результатов парсинга.

Схема БД:
- fedresurs_results: ИНН, № дела, последняя дата (с Fedresurs.ru)
- kad_arbitr_results: № дела, последняя дата, наименование документа (с Kad.arbitr.ru)
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для моделей."""

    pass


class FedresursResult(Base):
    """
    Результат парсинга Fedresurs.ru.

    Уникальность: inn + parsed_at (избежание дублей при повторном запуске).
    """

    __tablename__ = "fedresurs_results"
    __table_args__ = (
        UniqueConstraint("inn", "parsed_at", name="uq_fedresurs_inn_parsed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    inn: Mapped[str] = mapped_column(primary_key=False, index=True)
    case_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class KadArbitrResult(Base):
    """
    Результат парсинга Kad.arbitr.ru.

    Уникальность: case_number + parsed_at.
    """

    __tablename__ = "kad_arbitr_results"
    __table_args__ = (
        UniqueConstraint(
            "case_number", "parsed_at", name="uq_kad_arbitr_case_parsed_at"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_number: Mapped[str] = mapped_column(index=True)
    last_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    document_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
