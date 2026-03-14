# TZ Parser

Парсер данных по банкротству с сайтов [Fedresurs.ru](https://fedresurs.ru/) и [Kad.arbitr.ru](https://kad.arbitr.ru/).

## Назначение

Программа принимает список ИНН из xlsx-файла, для каждого ИНН:
1. Парсит Fedresurs.ru — получает № дела и последнюю дату (вкладка «Сведения о банкротстве»)
2. Парсит Kad.arbitr.ru по № дела — получает последнюю дату и наименование документа (вкладка «Электронное дело»)

Результаты сохраняются в две таблицы БД.

## Стек

- **Python 3.11+**
- **Camoufox** — Firefox-based anti-detect браузер (обход Cloudflare и тяжёлых антиботов)
- **SQLAlchemy 2.0** — ORM
- **PostgreSQL** / **SQLite** — БД (переключение через `DATABASE_URL`)
- **Docker + Docker Compose** — контейнеризация

## Установка и запуск

### Через Docker Compose (рекомендуется)

```bash
# Создать пример xlsx (если нет)
python scripts/create_sample_xlsx.py

# Запуск
docker-compose up --build
```

### Локально

```bash
# Установка зависимостей
pip install -r requirements.txt
camoufox fetch  # скачать браузер Camoufox

# Создать пример xlsx
python scripts/create_sample_xlsx.py

# Запуск (SQLite по умолчанию)
python -m src.main data/inns.xlsx

# Тест парсера
python scripts/test_camoufox.py 231138771115 --headed
```

## Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | URL БД (SQLite или PostgreSQL) | `sqlite:///data/parser.db` |
| `CONCURRENCY` | Макс. параллельных парсеров | `5` |
| `DELAY_MIN` / `DELAY_MAX` | Пауза между запросами (сек) | `8.0` / `15.0` |
| `PROXY_URL` | Прокси (http или socks5) | — |
| `HEADLESS` | Режим браузера | `true` |
| `XLSX_SHEET_NAME` | Имя листа в xlsx | `Sheet1` |
| `XLSX_INN_COLUMN` | Имя колонки с ИНН | `ИНН` |

## Структура xlsx

- Первая строка — заголовки
- Колонка `ИНН` (или `XLSX_INN_COLUMN`) — 10 или 12 цифр
- ИНН с пробелами нормализуются автоматически

## Докачка (Resume)

При повторном запуске программа пропускает ИНН и дела, уже обработанные. Для полной переобработки используйте `--no-resume`.

