FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    python3-dev \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/static
RUN chmod -R 755 /app/media /app/static

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "real_estate_portal.wsgi:application", "--bind", "0.0.0.0:8080"]
