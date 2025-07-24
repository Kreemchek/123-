FROM python:3.11

# Установка временной зоны
RUN apt-get update && apt-get install -y tzdata
ENV TZ=Europe/Moscow

# Остальные инструкции остаются без изменений
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    iputils-ping \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]