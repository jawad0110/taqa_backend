FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Sevalla injects $PORT, so we must bind to it
ENV PORT=$PORT
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden in Sevalla Processes tab if needed)
CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
