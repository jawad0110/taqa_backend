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
ENV PORT=$PORT
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MAX_WORKERS=4

# Expose Sevalla’s dynamic port
EXPOSE $PORT

# Final command — Uvicorn only, no --timeout
CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
