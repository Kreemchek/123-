# Указываем переменную версии Python
ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python${PYTHON_VERSION}-dev \
 && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем только requirements.txt, чтобы закешировать слои
COPY requirements.txt .

# Установка зависимостей
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект (исключения указаны в .dockerignore)
COPY . .

# Копируем и даем права на entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Указываем точку входа
ENTRYPOINT ["/entrypoint.sh"]

# Команда по умолчанию (Gunicorn)
CMD ["gunicorn", "real_estate_portal.wsgi:application", "--bind", "0.0.0.0:8080"]
