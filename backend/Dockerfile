# Backend image for hosting (Render, or anywhere that runs Docker).
FROM python:3.14-slim

# Tesseract is the OCR engine behind photo scanning.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first, so rebuilds that only change code reuse this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Don't run the server as root.
RUN useradd --create-home appuser
USER appuser

# The host tells us which port to listen on through $PORT (8000 locally).
# On every start: bring the database tables up to date, then run the API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
