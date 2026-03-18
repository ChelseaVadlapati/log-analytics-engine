FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install fastapi uvicorn[standard] pydantic pydantic-settings \
    python-dotenv httpx elasticsearch[async] sqlalchemy \
    psycopg2-binary redis structlog prometheus-client

# Copy application code
COPY api/ ./api/

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]