FROM python:3.11-slim

WORKDIR /app

COPY requirements-prod.txt .

RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend ./backend
COPY frontend ./frontend
COPY model_loader.py .

ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["python", "model_loader.py"]