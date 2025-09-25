FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Sevalla injects $PORT dynamically
EXPOSE 8000

# Shell form CMD lets $PORT expand properly
CMD uvicorn src:app --host 0.0.0.0 --port $PORT --workers 4 --proxy-headers --forwarded-allow-ips "*"
