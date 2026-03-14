"""
Сессии SQLAlchemy и инициализация БД.

Поддерживает SQLite и PostgreSQL через DATABASE_URL.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config import DATABASE_URL
from src.models.db_models import Base


def _migrate_document_path(engine):
    """Добавляет колонку document_path в kad_arbitr_results, если её нет."""
    with engine.connect() as conn:
        try:
            if "sqlite" in DATABASE_URL:
                result = conn.execute(text("PRAGMA table_info(kad_arbitr_results)"))
                columns = [row[1] for row in result]
            else:
                result = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'kad_arbitr_results'"
                    )
                )
                columns = [row[0] for row in result]
            if "document_path" not in columns:
                conn.execute(text("ALTER TABLE kad_arbitr_results ADD COLUMN document_path TEXT"))
                conn.commit()
        except Exception:
            pass


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
    try:
        _migrate_document_path(engine)
    except Exception:
        pass
