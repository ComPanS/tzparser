# TZ Parser

Парсер данных по банкротству с сайтов [Fedresurs.ru](https://fedresurs.ru/) и [Kad.arbitr.ru](https://kad.arbitr.ru/).

## Назначение

Программа принимает список ИНН из xlsx-файла, для каждого ИНН:
1. Парсит Fedresurs.ru — получает № дела и последнюю дату (вкладка «Сведения о банкротстве»)
2. Парсит Kad.arbitr.ru по № дела — получает последнюю дату и наименование документа (вкладка «Электронное дело»)

Результаты сохраняются в две таблицы БД.

## Стек

- **Python 3.11+**
- **Tor + FlareSolverr + undetected-chromedriver** — обход блокировки fedresurs.ru (curl_cffi → uc → FlareSolverr)
- **nodriver** — резервный парсер (USE_TOR_PARSER=false)
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

# Или в фоне
docker-compose up -d --build
```

Логи и данные: `./logs/`, `./data/`

### Локально

```bash
# Установка зависимостей
pip install -r requirements.txt
# Chrome/Chromium должен быть установлен; SeleniumBase скачивает chromedriver при первом запуске

# Создать пример xlsx
python scripts/create_sample_xlsx.py

# Запуск (SQLite по умолчанию)
python -m src.main data/inns.xlsx

# С указанием файла
python -m src.main path/to/inns.xlsx

# Без докачки (обработать все заново)
python -m src.main data/inns.xlsx --no-resume
```

## Обход блокировки fedresurs.ru (Tor + FlareSolverr)

Единый способ: Tor + curl_cffi + undetected-chromedriver + FlareSolverr.

### Шаг 1: Установка Tor

```bash
# Linux (Ubuntu/Debian)
sudo apt install tor
sudo nano /etc/tor/torrc   # SOCKSPort 9050, ControlPort 9051, CookieAuthentication 1
sudo systemctl start tor

# Windows: скачать с https://www.torproject.org/download/
```

### Шаг 2: FlareSolverr (Docker)

```bash
docker run -d --name=flaresolverr -p 8191:8191 --restart=unless-stopped flaresolverr/flaresolverr
```

### Шаг 3: Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `USE_TOR_PARSER` | Использовать Tor-парсер | `true` |
| `TOR_PROXY` | Прокси Tor | `socks5://127.0.0.1:9050` |
| `TOR_CONTROL_PORT` | Порт управления Tor | `9051` |
| `FLARESOLVERR_URL` | URL FlareSolverr | `http://localhost:8191/v1` |

### Проверка

```bash
curl --socks5 127.0.0.1:9050 https://check.torproject.org/
curl http://localhost:8191/health
```

## Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | URL БД (SQLite или PostgreSQL) | `sqlite:///data/parser.db` |
| `CONCURRENCY` | Макс. параллельных парсеров | `5` |
| `DELAY_MIN` / `DELAY_MAX` | Пауза между запросами (сек) | `8.0` / `15.0` |
| `RETRY_ATTEMPTS` | Попыток при ошибке | `3` |
| `RETRY_BASE_DELAY` | Базовая задержка retry (сек) | `2.0` |
| `XLSX_SHEET_NAME` | Имя листа в xlsx | `Sheet1` |
| `XLSX_INN_COLUMN` | Имя колонки с ИНН | `ИНН` |

## Структура xlsx

- Первая строка — заголовки
- Колонка `ИНН` (или `XLSX_INN_COLUMN`) — 10 или 12 цифр
- ИНН с пробелами нормализуются автоматически

## Пример использования

```bash
# Docker
docker-compose run --rm parser python -m src.main /app/data/inns.xlsx

# Локально
python -m src.main data/inns.xlsx
```

## Докачка (Resume)

При повторном запуске программа пропускает ИНН и дела, уже обработанные сегодня. Для полной переобработки используйте `--no-resume`.

## Обработка ошибок

- Retry с экспоненциальной задержкой при сетевых сбоях
- ИНН не найден — логирование, продолжение работы
- CAPTCHA/блокировка — пауза 60 сек, повтор
- Логи: `logs/parser.log` и stdout

## Файл CHANGES_REQUIRED.md

Перед первым запуском ознакомьтесь с [CHANGES_REQUIRED.md](CHANGES_REQUIRED.md) — в нём перечислены селекторы и другие параметры, которые нужно уточнить для работы парсера на реальных сайтах.
