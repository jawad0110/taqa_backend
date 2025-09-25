FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment vars
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Sevalla injects $PORT dynamically
EXPOSE $PORT

# Start FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn src:app --host 0.0.0.0 --port $PORT --workers 4 --proxy-headers --forwarded-allow-ips '*'"]
