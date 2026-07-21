# ============================================================
# assignment/Dockerfile  —  FastAPI ticket-assignment service
# Port: 8003  |  Health: GET /assign/health
# Server: gunicorn + uvicorn workers (ASGI — correct for FastAPI)
# ============================================================

FROM python:3.11-slim

WORKDIR /app

RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY assignment_service.py .
COPY secrets.py .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8003

CMD ["gunicorn", "assignment_service:app", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8003", "--workers", "2", "--timeout", "60"]
