"""
Сессии SQLAlchemy и инициализация БД.

Поддерживает SQLite и PostgreSQL через DATABASE_URL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import DATABASE_URL
from src.models.db_models import Base


def get_engine():
    """Создаёт движок SQLAlchemy с учётом SQLite."""
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(DATABASE_URL, connect_args=connect_args, echo=False)


def get_session_factory():
    """Возвращает фабрику сессий."""
    engine = get_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Создаёт таблицы в БД."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
