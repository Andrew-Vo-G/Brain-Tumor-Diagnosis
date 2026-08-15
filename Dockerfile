FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# backend/main.py nằm trong app/, nên phải cd vào đó để uvicorn tìm thấy đúng module
WORKDIR /app/app

ENV PRELOAD_AI_ASYNC=1
ENV FAST_INFERENCE=1
ENV YOLO_OFFLINE=1

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]