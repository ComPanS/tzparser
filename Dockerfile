FROM python:3.11-slim

WORKDIR /app

# Зависимости для Camoufox (Firefox)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 \
    libx11-xcb1 \
    libasound2 \
    libdbus-glib-1-2 \
    libxt6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN camoufox fetch

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

RUN mkdir -p /app/logs /app/data \
    && python scripts/create_sample_xlsx.py 2>/dev/null || true

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "src.main", "/app/data/inns.xlsx"]
