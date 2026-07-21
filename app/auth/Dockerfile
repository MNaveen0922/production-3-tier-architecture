# ============================================================
# auth/Dockerfile  —  FastAPI auth service
# Port: 8001  |  Health: GET /auth/health
# Server: gunicorn + uvicorn workers (ASGI — correct for FastAPI)
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY auth_service.py .
COPY secrets.py .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8001

CMD ["gunicorn", "auth_service:app", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8001", "--workers", "2", "--timeout", "60"]
