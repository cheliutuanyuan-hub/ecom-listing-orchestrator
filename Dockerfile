# Project A: ecom-listing-orchestrator
# Default wiring uses fully-functional MOCK adapters -> runs with no network.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LISTING_AUTO_APPROVE=false

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY demo.py .

RUN mkdir -p /data
EXPOSE 8000

# Default: run the end-to-end verification (offline). Override CMD to serve the API:
#   CMD ["sh","-c","PYTHONPATH=src python -m ecom_orchestrator api --host 0.0.0.0 --port 8000"]
CMD ["sh","-c","PYTHONPATH=src python demo.py"]
