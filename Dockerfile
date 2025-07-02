# Базовый образ
FROM python:3.10-slim

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Рабочая директория
WORKDIR /app

# Установим системные зависимости сразу
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt для кеширования установки зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальной проект
COPY . .

# Создаём нужные директории с правильными правами
RUN install -d -m 755 /app/media /app/static

# Собираем статику
RUN python manage.py collectstatic --noinput

# Копируем и даём права на entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Команда запуска
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "real_estate_portal.wsgi:application", "--bind", "0.0.0.0:8080"]
