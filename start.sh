#!/bin/sh
echo "Starting FastAPI on port ${PORT}..."
uvicorn src:app --host 0.0.0.0 --port ${PORT} --workers 4 --proxy-headers --forwarded-allow-ips "*"
