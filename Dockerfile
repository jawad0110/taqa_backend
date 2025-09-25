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

# Create necessary directories
RUN mkdir -p /app/static/images/products

# Environment variables
ENV# Environment variables
ENV PORT=$PORT
ENV PYTHONUNBUFFERED=1
ENV MAX_WORKERS=4
ENV TIMEOUT=300
ENV BACKLOG=2048
ENV KEEPALIVE=65

# Expose port
EXPOSE $PORT

# Final command with connection handling settings
CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "$PORT", "--workers", "4", "--timeout", "300", "--backlog", "2048", "--proxy-headers", "--forwarded-allow-ips", "*", "--limit-concurrency", "1000", "--limit-max-requests", "10000", "--keepalive", "65"]
