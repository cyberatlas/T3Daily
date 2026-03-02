FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ backend/
COPY alembic.ini .

# Create data directories (will be overridden by volume mounts)
RUN mkdir -p data/db data/garmin_tokens data/plan

EXPOSE 8000

# Run migrations then start the server
CMD alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
