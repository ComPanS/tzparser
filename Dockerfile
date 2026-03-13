FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей: Chrome (Tor/FlareSolverr) + Firefox (Camoufox)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    chromium \
    libgtk-3-0 \
    libx11-xcb1 \
    libdbus-glib-1-2 \
    libxt6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Chrome: SeleniumBase скачивает chromedriver при первом запуске
# Camoufox: скачиваем браузер при сборке
RUN camoufox fetch

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

RUN mkdir -p /app/logs /app/data \
    && python scripts/create_sample_xlsx.py 2>/dev/null || true

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV CHROME_BINARY_PATH=/usr/bin/chromium

CMD ["python", "-m", "src.main", "/app/data/inns.xlsx"]
