FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Создаем директорию для логов аналитики
RUN mkdir -p /var/log/vobshage
# Запускаем через uvicorn с поддержкой websockets
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
