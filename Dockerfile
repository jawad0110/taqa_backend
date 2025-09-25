FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Default run command (can be overridden in Sevalla if needed)
CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
