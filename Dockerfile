FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости ОС
RUN apt-get update && apt-get install -y \
    libpq-dev \
    python3-dev \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем нужные директории и даем права
RUN mkdir -p /app/media /app/static
RUN chmod -R 755 /app/media /app/static

# Копируем entrypoint.sh и даем права на исполнение
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Переменные окружения (пример, можно задавать через docker run или docker-compose)
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]

# Команда запуска (например, gunicorn)
CMD ["gunicorn", "yourproject.wsgi:application", "--bind", "0.0.0.0:8000"]
