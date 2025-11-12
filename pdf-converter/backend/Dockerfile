FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
RUN mkdir -p logs

RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

# Use multiple workers for concurrent request handling
# Workers = (2 x CPU cores) + 1 is a good starting point
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
