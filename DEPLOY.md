# Деплой

## Сервер

Публичный IP **не нужен** — бот работает на long polling (только исходящий
трафик). Нужен outbound-доступ к `api.telegram.org`, `news.google.com`,
`iss.moex.com` и к твоему AI-провайдеру (`api.anthropic.com`, либо
`api.timeweb.ai`, если используешь шлюз). 1 ГБ RAM хватает; `cloud-init.sh`
добавляет 2 ГБ swap на случай тяжёлой сборки образа.

## Cloud-init (Ubuntu)

Содержимое [`cloud-init.sh`](cloud-init.sh) вставляется в поле «Cloud-init»
при создании сервера — оно поставит swap, Docker и склонирует проект в
`/opt/analysis_for_invest_bot`. Лог: `/var/log/cloud-init-output.log`.

После загрузки сервера:
```bash
cd /opt/analysis_for_invest_bot
nano .env                 # BOT_TOKEN + AI_PROVIDER и соответствующий ключ
docker compose up -d --build
docker compose logs -f
```

## Быстрый старт вручную (без cloud-init)

Нужен Docker с плагином Compose (`docker compose version`).

```bash
git clone https://github.com/keshtoim/analysis_for_invest_bot.git
cd analysis_for_invest_bot

cp .env.example .env
nano .env                 # вписать BOT_TOKEN и ключ AI-провайдера

docker compose up -d --build
docker compose logs -f    # смотрим, что поднялось
```

Всё. `restart: unless-stopped` поднимет контейнер после краша и ребута сервера.

## Переменные окружения (`.env`)

| Переменная | Обязательна | Что это |
|---|---|---|
| `BOT_TOKEN` | **да** | токен от @BotFather |
| `AI_PROVIDER` | **да** | `anthropic` (прямой Anthropic API) или `openai` (OpenAI SDK/совместимый шлюз, например Timeweb AI Gateway) |
| `ANTHROPIC_API_KEY` | если `AI_PROVIDER=anthropic` | ключ Anthropic |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | если `AI_PROVIDER=openai` | ключ/URL/модель шлюза |
| `CLAUDE_MODEL` | нет | модель для прямого Anthropic API, по умолчанию `claude-sonnet-5` |
| `DB_PATH` | нет | путь к SQLite-файлу, по умолчанию `data/bot.db` |
| `HEARTBEAT_PATH` | нет | путь к heartbeat-файлу для healthcheck, по умолчанию `data/heartbeat` |
| `CACHE_TTL_HOURS` | нет | сколько часов кэш данных о компании считается свежим, по умолчанию 6 |
| `ANTI_FLOOD_COOLDOWN_SECONDS` | нет | кулдаун между запросами анализа на юзера, по умолчанию 3 |

`.env` в `.gitignore` — не коммить.

## Данные

Всё состояние — в `./data` (в контейнере `/app/data`):

| Файл | Что |
|---|---|
| `bot.db` | SQLite: таблица `users` (кто писал боту) и `company_cache` (новости + MOEX + сектор по компании, с TTL) — единственное, что жаль потерять |
| `heartbeat` | отметка «бот жив», обновляется раз в минуту — на неё смотрит healthcheck |

Каталог переживает `docker compose down` и пересборку образа. Пропадает
только при удалении файлов руками.

**Бэкап.** Просто скопируй `data/bot.db` — это обычный файл, никакой
дополнительной магии не нужно:
```bash
cp data/bot.db backup/bot.$(date +%F).db
```

## Healthcheck

Бот раз в минуту пишет `data/heartbeat`; healthcheck в контейнере проверяет,
что отметке меньше 5 минут. `docker ps` покажет `healthy` / `unhealthy`.

Обычный `restart: unless-stopped` на `unhealthy` **не реагирует** (перезапускает
только упавший контейнер). Чтобы перезапускало и «зависший» — раскомментируй
сервис `autoheal` в `docker-compose.yml`.

Проверить руками:
```bash
docker compose exec bot python -m app.healthcheck; echo $?
```

## Обновление

```bash
git pull
docker compose up -d --build
```

Compose остановит старый контейнер и поднимет новый — второго инстанса не будет.

## Один инстанс

Telegram отдаёт `getUpdates` только одному процессу. Если запустить бота
дважды (локально при живом сервере, два контейнера) — оба получат
`Conflict: terminated by other getUpdates` и будут молотить вхолостую.
Для локальной разработки заведи **отдельного тестового бота** у @BotFather
с другим токеном.

## Перенос локального проекта на сервер

Если уже пользовался локально и не хочешь терять кэш/пользователей —
скопируй `data/bot.db` в `./data` на сервере перед первым запуском
(или останови контейнер, подмени файл, перезапусти):

```bash
scp data/bot.db server:/opt/analysis_for_invest_bot/data/bot.db
ssh server 'cd /opt/analysis_for_invest_bot && docker compose restart'
```

## Логи

```bash
docker compose logs -f bot          # хвост
docker compose logs --since 1h bot  # за час
```

Ротация настроена в `docker-compose.yml` (`max-size: 10m`, `max-file: 3`) —
диск не забьётся.

## Без Docker (venv + systemd)

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
```

`/etc/systemd/system/analysis-for-invest-bot.service`:

```ini
[Unit]
Description=analysis-for-invest-bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/analysis_for_invest_bot
EnvironmentFile=/opt/analysis_for_invest_bot/.env
ExecStart=/opt/analysis_for_invest_bot/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now analysis-for-invest-bot
journalctl -u analysis-for-invest-bot -f
```
