FROM python:3.12-slim

# tzdata — чтобы TZ и системное время в контейнере были московскими (для логов;
# MOEX и большинство новостей по РФ-компаниям живут по этому часовому поясу).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Moscow

WORKDIR /app

# Зависимости — отдельным слоем: переустанавливаются только при смене requirements.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# SQLite (users, кэш компаний) и heartbeat переживают пересборку образа
VOLUME /app/data

# Бот раз в минуту пишет data/heartbeat; здесь проверяем свежесть отметки.
# Полноценный авто-рестарт по unhealthy — через autoheal (см. docker-compose.yml).
HEALTHCHECK --interval=2m --timeout=10s --start-period=90s --retries=3 \
    CMD ["python", "-m", "app.healthcheck"]

CMD ["python", "main.py"]
