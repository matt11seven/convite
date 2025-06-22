FROM node:19-slim AS frontend-build

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./
RUN yarn build

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build from previous stage
COPY --from=frontend-build /app/frontend/build ./frontend/build

# Create directory for generated images
RUN mkdir -p /app/generated_images

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV STATIC_FILES_DIR=/app/frontend/build

# Create entrypoint script
RUN echo '#!/bin/sh\n\
cd /app\n\
exec uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8001}\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8001

# Run the application
CMD ["/app/entrypoint.sh"]
