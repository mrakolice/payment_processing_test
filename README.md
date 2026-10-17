# Payment Processing Service

Асинхронный микросервис обработки платежей: принимает запрос на оплату через
HTTP, кладёт событие в очередь (через Outbox pattern), эмулирует обработку во
отдельном consumer'е и уведомляет клиента результатом через webhook.

## Сервисы в `docker-compose.yml`:

| Сервис | Что делает|
|---|---|
| `postgres` | БД |
| `rabbitmq` | брокер сообщений |
| `migrate` | разовый прогон `alembic upgrade head` при старте | 
| `api` | FastAPI |
| `outbox` | публикует события в RabbitMQ |
| `consumer` | обрабатывает платёж |

`api`, `outbox`, `consumer` и `migrate` — это **один и тот же образ** (общий
код и зависимости), различается только команда запуска в compose-файле. Так
проще держать код синхронным между процессами и не дублировать сборку.

## Dead Letter Queue

Нативного «после N попыток — в DLQ» в RabbitMQ нет из коробки, поэтому
собрана стандартная схема из трёх очередей `app/core/brokers.py`:

## Единый образ для api/consumer/outbox/migrate

У них общий набор зависимостей и общий код моделей/конфига — технически
можно было бы собирать 3 разных образа, но тогда любое изменение модели
нужно было бы синхронизировать между образами руками. Один `Dockerfile`,
разные команды запуска в `docker-compose.yml`

### Аутентификация

Статический `X-API-Key` навешан как dependency на уровне роутера
(`fastapi.APIRouter(dependencies=[...])` в `views.py`) — применяется ко
**всем** эндпоинтам пакета `payments` автоматически, не нужно добавлять
проверку в каждый хендлер руками

## Структура репозитория

```
app/
  web_app.py            # точка входа FastAPI (api)
  consumer_app.py        # точка входа FastStream (consumer)
  outbox_app.py           # точка входа поллера outbox
  dependencies.py         # DI: сессия БД, X-API-Key
  api/
    main.py, v1/main.py    # сборка роутеров (/api/v1/...)
    v1/payments/
      views.py             # POST / GET /payments
      requests.py           # Pydantic-схема тела запроса
      responses.py           # Pydantic-схемы ответов
  core/
    config.py              # pydantic-settings, читает .env
    database.py             # engine/session, get_db() dependency
    brokers.py               # RabbitBroker + топология очередей (DLQ)
    enums.py                  # Currency, PaymentStatus
    models/payments.py         # SQLModel: Payment, Outbox
  tests/                        # pytest (см. раздел "Тесты")
migrations/                      # Alembic
system_sql/                       # SQL для ручной инициализации БД (локально)
docker-compose.yml                 # postgres, rabbitmq, migrate, api, outbox, consumer
docker-compose.override.yml         # дев-оверрайд: live-reload, подключается сам
Dockerfile                           # общий образ для api/consumer/outbox/migrate
Makefile                              # команды для локальной разработки и Docker
```

## Переменные окружения

Один файл `.env` в корне репозитория (копия — `.env.example`), читается и
локальным запуском, и Docker Compose.

| Переменная | Назначение |
|---|---|
| `DATABASE__NAME`, `__USER`, `__PASSWORD`, `__HOST`, `__PORT` | подключение к Postgres |
| `DATABASE__DRIVER` | `postgresql+asyncpg` (приложение) |
| `RABBITMQ__HOST`, `__PORT`, `__USER`, `__PASSWORD`, `__NAME` | подключение к RabbitMQ |
| `SERVER__LISTEN_ADDRESS`, `__PORT` | куда биндится uvicorn |
| `SERVER__ALLOWED_ORIGINS` | CORS |
| `SERVER__API_KEY` | статический ключ, ожидается в заголовке `X-API-Key` на всех эндпоинтах |

`DATABASE__HOST`/`RABBITMQ__HOST` в `.env` — `localhost` (для запуска без
Docker). В `docker-compose.yml` они переопределены на `postgres`/`rabbitmq`
(имена сервисов) через `environment:` — внутри docker-сети `localhost`
указывал бы на сам контейнер.

## Запуск в Docker

```bash
docker compose up -d --build
```

Это поднимет postgres + rabbitmq, прогонит миграции (`migrate`, разовый
сервис) и запустит `api`/`outbox`/`consumer`. `docker-compose.override.yml`
подключается автоматически (без доп. флагов) и даёт live-reload — код из
`./app` примонтирован в контейнеры, пересобирать образ на каждую правку не
нужно (подробнее — его собственные комментарии). Для запуска без
live-reload:

```bash
docker compose -f docker-compose.yml up -d --build
```

Проверить, что всё поднялось:

```bash
curl http://localhost:8000/health
```

API доступен на `http://localhost:8000`, RabbitMQ management UI — на
`http://localhost:15673` (guest/guest), Postgres снаружи — на порту `5433`.

Применить новую миграцию вручную (без пересоздания всего стека):

```bash
make migrate-docker
```

## Запуск локально без Docker

Нужны локально запущенные Postgres и RabbitMQ (адреса/порты — из `.env`).

```bash
uv sync
make init-database        # создаёт БД/роль из system_sql/database_init.sql
uv run alembic upgrade head
make run-server            # api, localhost:8056
make run-tasks              # consumer, в отдельном терминале
uv run python -m app.outbox_app   # outbox-поллер, в третьем терминале
```

## API

Все запросы требуют заголовок `X-API-Key: <SERVER__API_KEY из .env>`.

### Создать платёж

```bash
curl -i -X POST http://localhost:8000/api/v1/payments/ \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: order-42" \
  -H "Content-Type: application/json" \
  -d '{
        "amount": "199.99",
        "currency": "RUB",
        "description": "Order #42",
        "metadata": {"order_id": "42"},
        "webhook_url": "https://example.com/webhooks/payments"
      }'
```

Повторный запрос с тем же `Idempotency-Key` (даже с другим телом) вернёт тот
же `payment_id` — новый платёж не создастся.

### Получить платёж

```bash
curl http://localhost:8000/api/v1/payments/1 -H "X-API-Key: $API_KEY"
```

## Тесты

```bash
make tests              # всё, включая медленный интеграционный (~20с)
make tests-fast          # без него (быстрый прогон при разработке)
```

Тесты используют ту же БД, что настроена в `.env` (это обычная БД
разработки — для реальной изоляции можно подставить отдельную через
`system_sql/test_database_init.sql`). Перед каждым тестом `payments` и
`outbox` очищаются автоматически (`app/tests/conftest.py`).

## Команды Makefile

| Команда | Что делает |
|---|---|
| `make run-server` / `make run-tasks` | api / consumer локально |
| `make init-database` / `make reset-database` | локальная БД (без Docker) |
| `make migrate-docker` | `alembic upgrade head` в контейнере `migrate` |
| `make makemigrations-docker msg="..."` | `alembic revision --autogenerate` в контейнере, файл появляется в `./migrations` на хосте |
| `make tests` / `make tests-fast` | тесты |
| `make lint` / `make format` | ruff |

## Известные ограничения

- Тесты делят БД с локальной разработкой, а не отдельную тестовую БД
- `payments.new.retry`/`payments.new.dlq` объявляются при старте
  `consumer_app` (`@app.after_startup`); если перед первым запуском кто-то успеет опубликовать в `payments.new` 
без того, чтобы очередь уже существовала с нужными DLX-аргументами — RabbitMQ создаст её
  с настройками по умолчанию.
- Нет мониторинга размера `payments.new.dlq` — попавшие туда сообщения
  нужно смотреть руками (RabbitMQ management UI) или дочитывать отдельным
  скриптом/алертом.
