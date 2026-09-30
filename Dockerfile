# ===== Базовый образ =====
FROM python:3.11-slim

# ===== Настройки Python =====
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ===== Рабочая директория =====
WORKDIR /app

# ===== Системные зависимости =====
# libffi-dev нужен bcrypt/cryptography для сборки (если нет wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# ===== Зависимости Python =====
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ===== Код приложения =====
COPY app/ ./app/

# ===== Папка для загрузок =====
RUN mkdir -p /app/uploads/avatars \
             /app/uploads/chip_images \
             /app/uploads/news_images \
             /app/uploads/user_photos \
             /app/uploads/feedback_images \
             /app/data

# ===== Порт =====
EXPOSE 8053

# ===== Запуск =====
CMD ["gunicorn", "app.main:app", \
     "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8053", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]