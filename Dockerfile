# ----------------------------
# Backend Dockerfile (Python)
# ----------------------------
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies first (cache layer)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY backend/ .

# Sevalla expects apps to listen on $PORT
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Create an entrypoint script to switch between processes
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Default command → will be overridden in Sevalla process config
CMD ["/docker-entrypoint.sh"]
