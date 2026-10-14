# Deribit Crypto Price Tracker & FastAPI Service

Сервис для периодического сбора цен криптовалют (`btc_usd`, `eth_usd`) с биржи [Deribit](https://docs.deribit.com/) в фоновом режиме через **Celery** и предоставления внешнего REST API на **FastAPI** с сохранением данных в **PostgreSQL**.

---

## 📋 Содержание

- [Стек технологий](#стек-технологий)
- [Архитектура проекта](#архитектура-проекта)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт (Docker Compose)](#быстрый-старт-docker-compose)
- [Локальный запуск без Docker](#локальный-запуск-без-docker)
- [Документация API](#документация-api)
- [Запуск тестов](#запуск-тестов)
- [Design Decisions (Обоснование принятых решений)](#design-decisions)

---

## 🛠 Стек технологий

- **Язык**: Python 3.11 / 3.9+
- **Веб-фреймворк**: [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- **База данных**: [PostgreSQL 16](https://www.postgresql.org/)
- **ORM & Миграции**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async Engine + asyncpg) + [Alembic](https://alembic.sqlalchemy.org/)
- **Фоновые задачи & Планировщик**: [Celery](https://docs.celeryq.dev/) + Celery Beat + [Redis](https://redis.io/)
- **HTTP-клиент**: [aiohttp](https://docs.aiohttp.org/) (с поддержкой connection pooling, retries и тайм-аутов)
- **Валидация и настройки**: [Pydantic v2](https://docs.pydantic.dev/) + Pydantic Settings
- **Контейнеризация**: Docker + Docker Compose
- **Тестирование**: Pytest + Pytest-Asyncio + Httpx + aiosqlite (in-memory test DB)

---

## 🏛 Архитектура проекта

Проект спроектирован по принципам **Clean Architecture** и **SOLID**:
1. **API Layer (Presentation)** (`app/api/`): HTTP контроллеры FastAPI, валидация входящих параметров, документация OpenAPI/Swagger.
2. **Service Layer (Domain Logic)** (`app/services/`): Бизнес-логика, валидация и нормализация тикеров, валидация временных диапазонов.
3. **Repository Layer (Data Access)** (`app/repositories/`): Абстракция доступа к данным (паттерн Repository). Изолирует SQL-запросы от бизнес-логики.
4. **Client Layer (External Integration)** (`app/clients/`): Клиент биржи Deribit на `aiohttp`, наследующий абстрактный интерфейс `BaseCryptoClient`.
5. **Task Layer (Background Workers)** (`app/tasks/`): Celery задачи и расписание Celery Beat для сбора данных каждую минуту.

### Отсутствие глобальных переменных:
- Все зависимости внедряются через **Dependency Injection** (`fastapi.Depends`).
- Сессии БД управляются контекстным менеджером и генератором сессий `get_db`.
- Конфигурация инкапсулирована в `Settings` через синглтон-фабрику `@lru_cache`.

---

## 📂 Структура репозитория

```
.
├── app/
│   ├── api/
│   │   ├── deps.py               # Dependency injection (get_db, get_price_service, etc.)
│   │   └── v1/
│   │       └── endpoints.py      # Маршруты API (все методы GET, обязательный ticker)
│   ├── clients/
│   │   ├── base.py               # Абстрактный базовый класс BaseCryptoClient и исключения
│   │   └── deribit.py            # Асинхронный клиент Deribit на aiohttp с повторными попытками
│   ├── models/
│   │   └── price.py              # SQLAlchemy модель PriceRecord (индексы, типизация Mapped)
│   ├── repositories/
│   │   ├── base.py               # Интерфейс BasePriceRepository
│   │   └── price_repository.py   # SQLAlchemy Async реализация репозитория
│   ├── schemas/
│   │   └── price.py              # Pydantic схемы ответов и валидации диапазонов дат
│   ├── services/
│   │   └── price_service.py      # Бизнес-логика цен и нормализации
│   ├── tasks/
│   │   ├── celery_app.py         # Инициализация Celery и настройка Celery Beat (каждую минуту)
│   │   └── price_tasks.py        # Периодическая задача polling'а Deribit и записи в БД
│   ├── config.py                 # Pydantic-Settings конфигурация приложения
│   ├── database.py               # Настройка SQLAlchemy async engine и сессий
│   └── main.py                   # Точка входа FastAPI, CORS, healthcheck, lifespan
├── alembic/                      # Миграции базы данных
│   ├── env.py
│   └── versions/
│       └── 001_initial_price_records.py
├── tests/                        # Набор тестов (30 тестов)
│   ├── conftest.py               # Фикстуры, in-memory sqlite async db, тестовый клиент
│   ├── test_api.py               # Интеграционные тесты всех эндпоинтов API
│   ├── test_client.py            # Unit-тесты клиента Deribit на aiohttp (retries, errors)
│   ├── test_repository.py        # Unit-тесты репозитория SQLAlchemy
│   ├── test_service.py           # Unit-тесты сервисного слоя
│   └── test_tasks.py             # Тесты Celery задач
├── .env.example                  # Пример конфигурации переменных окружения
├── .gitignore                    # Исключения для git
├── .gitlab-ci.yml                # GitLab CI пайплайн (тесты и сборка)
├── alembic.ini                   # Конфигурация Alembic
├── Dockerfile                    # Multi-stage production-ready Dockerfile
├── docker-compose.yml            # 2-контейнерный запуск (App + PostgreSQL)
├── docker-compose.microservices.yml # Альтернативный микросервисный запуск
├── entrypoint.sh                 # Скрипт ожидания БД, применения миграций и запуска
├── requirements.txt              # Зависимости Python
└── README.md                     # Документация проекта
```

---

## 🚀 Быстрый старт (Docker Compose)

По требованию тестового задания приложение сконфигурировано для развертывания **в двух контейнерах** (`app` и `db`):

```bash
# 1. Клонируйте репозиторий
git clone <URL_РЕПОЗИТОРИЯ>
cd <ПАПКА_ПРОЕКТА>

# 2. Создайте файл переменных окружения из примера
cp .env.example .env

# 3. Запустите двухконтейнерную сборку
docker compose up --build
```

### Что происходит при старте:
1. Поднимается контейнер `db` с PostgreSQL 16.
2. Контейнер `app` дожидается готовности PostgreSQL (через healthcheck и `nc`).
3. Применяются миграции Alembic (`alembic upgrade head`).
4. Внутри контейнера `app` стартуют встроенный брокер, воркер Celery, планировщик Celery Beat и веб-сервер FastAPI на порту `8000`.
5. Каждую минуту Celery Beat запускает задачу опроса Deribit для `btc_usd` и `eth_usd` и сохраняет цены в PostgreSQL.

API доступно по адресу: **http://localhost:8000**  
Интерактивная документация Swagger: **http://localhost:8000/docs**

---

## 💻 Локальный запуск без Docker

Если вы хотите запустить проект локально в виртуальном окружении:

### 1. Подготовка окружения
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Запуск PostgreSQL и Redis
Убедитесь, что локально запущены PostgreSQL и Redis:
```bash
# Пример с локальным запуском через brew (macOS):
brew services start postgresql@16
brew services start redis
```

### 3. Применение миграций БД
```bash
alembic upgrade head
```

### 4. Запуск компонентов сервиса (в отдельных терминалах):

**Терминал 1: Celery Worker**
```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info
```

**Терминал 2: Celery Beat (планировщик)**
```bash
celery -A app.tasks.celery_app.celery_app beat --loglevel=info
```

**Терминал 3: FastAPI Web Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📡 Документация API

Все методы являются **`GET`** и содержат обязательный query-параметр **`ticker`** (регистронезависимый: `btc_usd`, `BTC_USD`).

### 1. Получение всех сохраненных данных по валюте
- **Метод**: `GET /api/v1/prices` (также доступен алиас `/api/v1/prices/all`)
- **Query-параметры**:
  - `ticker` (обязательный, `str`): символ тикера (например, `btc_usd`, `eth_usd`)
  - `limit` (опциональный, `int`, default: 1000): ограничение количества записей
  - `offset` (опциональный, `int`, default: 0): смещение для пагинации

**Пример запроса**:
```bash
curl -X GET "http://localhost:8000/api/v1/prices?ticker=btc_usd"
```

**Пример ответа (200 OK)**:
```json
[
  {
    "id": 42,
    "ticker": "btc_usd",
    "price": 83874.15,
    "timestamp": 1791965782,
    "created_at": "2026-10-14T08:16:22.123456Z"
  },
  {
    "id": 41,
    "ticker": "btc_usd",
    "price": 83820.50,
    "timestamp": 1791965722,
    "created_at": "2026-10-14T08:15:22.654321Z"
  }
]
```

---

### 2. Получение последней цены валюты
- **Метод**: `GET /api/v1/prices/latest`
- **Query-параметры**:
  - `ticker` (обязательный, `str`): символ тикера (`btc_usd`, `eth_usd`)

**Пример запроса**:
```bash
curl -X GET "http://localhost:8000/api/v1/prices/latest?ticker=btc_usd"
```

**Пример ответа (200 OK)**:
```json
{
  "id": 42,
  "ticker": "btc_usd",
  "price": 83874.15,
  "timestamp": 1791965782,
  "created_at": "2026-10-14T08:16:22.123456Z"
}
```

Если по данному тикеру данных в базе еще нет — возвращается **404 Not Found**:
```json
{
  "detail": "No price records found for ticker 'btc_usd'"
}
```

---

### 3. Получение цены валюты с фильтром по дате
- **Метод**: `GET /api/v1/prices/filter` (также доступны алиасы `/api/v1/prices/date-range` и `/api/v1/prices/by-date`)
- **Query-параметры**:
  - `ticker` (обязательный, `str`): символ тикера (`btc_usd`, `eth_usd`)
  - `start_date` (опциональный, ISO 8601, например: `2026-10-14T00:00:00Z` или `2026-10-14`)
  - `end_date` (опциональный, ISO 8601, например: `2026-10-14T23:59:59Z` или `2026-10-14`)
  - `start_timestamp` (опциональный, `int`): UNIX timestamp начала диапазона
  - `end_timestamp` (опциональный, `int`): UNIX timestamp конца диапазона
  - `limit` (опциональный, `int`, default: 1000)
  - `offset` (опциональный, `int`, default: 0)

**Пример запроса по датам ISO 8601**:
```bash
curl -X GET "http://localhost:8000/api/v1/prices/filter?ticker=btc_usd&start_date=2026-10-14T00:00:00Z&end_date=2026-10-14T12:00:00Z"
```

**Пример запроса по UNIX timestamp**:
```bash
curl -X GET "http://localhost:8000/api/v1/prices/filter?ticker=eth_usd&start_timestamp=1791960000&end_timestamp=1791970000"
```

**Пример валидации**: Если `start_date > end_date`, API возвращает понятную ошибку **400 Bad Request**:
```json
{
  "detail": "Start date (1791970000) cannot be greater than end date (1791960000)"
}
```

---

### 4. Проверка состояния системы (Healthcheck)
- **Метод**: `GET /health`
- **Ответ**:
```json
{
  "status": "healthy",
  "service": "Deribit Price Tracker API",
  "version": "1.0.0"
}
```

---

## 🧪 Запуск тестов

Тестовый набор покрывает все уровни системы (клиент `DeribitClient`, `PriceRepository`, `PriceService`, контроллеры `FastAPI`, периодические задачи `Celery`):

```bash
pytest -v
```

Тесты выполняются изолированно в оперативной памяти с использованием `sqlite+aiosqlite` и моков внешнего API, не требуя запущенных экземпляров PostgreSQL и Redis.

---

## 💡 Design Decisions (Обоснование принятых решений)

В данном разделе подробно описаны архитектурные и технические решения, принятые при разработке сервиса.

### 1. Архитектура и разделение ответственности (Clean Architecture)
- **Проблема**: В небольших тестовых заданиях код часто пишут в одном файле `main.py` или смешивают SQL-запросы прямо в роутах FastAPI.
- **Решение**: Проект структурирован по слоям с четким разграничением ответственности:
  - `models/`: Декларативные сущности SQLAlchemy.
  - `schemas/`: DTO и валидация входящих/исходящих данных на Pydantic v2.
  - `repositories/`: Инкапсуляция всех запросов к БД (паттерн Repository).
  - `services/`: Чистая бизнес-логика (нормализация тикеров, валидация дат).
  - `api/`: Контроллеры FastAPI, преобразующие HTTP-запросы в вызовы сервисов.
  - `clients/`: Сетевые клиенты ко внешним биржам.
  - `tasks/`: Очереди задач и планировщик Celery.
- **Преимущество**: Высокая тестируемость (мокирование любого слоя), расширяемость (легко подключить новую биржу, например Binance или Bybit, реализовав `BaseCryptoClient`) и читаемость кода.

### 2. Реализация клиента на `aiohttp` и использование в Celery
- **Решение**: Клиент `DeribitClient` написан на `aiohttp` с наследованием от абстрактного интерфейса `BaseCryptoClient`.
- **Особенности клиента**:
  - Поддержка контекстного менеджера (`async with DeribitClient() as client:`).
  - Настраиваемый пул соединений (`ClientSession`) и таймауты (`ClientTimeout`).
  - Механизм повторных попыток (retries) с экспоненциальной задержкой при временных сбоях сети или тайм-аутах.
  - Иерархия кастомных исключений: `DeribitAPIError`, `DeribitConnectionError`, `DeribitInvalidResponseError`.
- **Интеграция с Celery**: Внутри периодической задачи Celery вызывается `asyncio.run(_async_fetch_and_store_prices())`. Это позволяет использовать один и тот же асинхронный стек (`aiohttp` + `asyncpg` + `SQLAlchemy AsyncSession`) без дублирования синхронного кода, сохраняя максимальную производительность.

### 3. Полное отсутствие глобальных переменных и Dependency Injection
- **Решение**: В приложении нет глобальных изменяемых состояний.
- **Как устроено**:
  - Подключение к БД передается через механизм зависимостей FastAPI: `Depends(get_db)`.
  - Репозиторий и сервис инстанцируются фабричными функциями-зависимостями: `Depends(get_price_service)`.
  - Настройки приложения считываются через `pydantic-settings` и кэшируются через `@lru_cache` фабрику `get_settings()`.
  - Все сетевые сессии и соединения с БД изолированы в рамках одного запроса/задачи и гарантированно закрываются в блоках `try...finally`.

### 4. Выбор ORM и библиотеки работы с PostgreSQL
- **Решение**: Использован **SQLAlchemy 2.0** в асинхронном режиме с драйвером **`asyncpg`** для веб-сервера FastAPI и синхронным драйвером `psycopg2` для миграций Alembic.
- **Преимущество**: `asyncpg` является самым быстрым драйвером PostgreSQL для Python. Синтаксис SQLAlchemy 2.0 (`select(...)`, `Mapped[...]`, `mapped_column[...]`) обеспечивает строгую статическую типизацию и исключает SQL-инъекции.

### 5. Схема базы данных и оптимизация индексов
- Таблица `price_records`:
  - `id`: Первичный ключ `BigInteger` (с автоинкрементом).
  - `ticker`: Символ тикера (`varchar(32)`), нормализуется к нижнему регистру перед сохранением.
  - `price`: Число с плавающей точкой (`Float` / `Double Precision`).
  - `timestamp`: Целочисленный UNIX timestamp (`BigInteger`) в секундах, как требуется в ТЗ.
  - `created_at`: Метка времени добавления записи с таймзоной (`TIMESTAMPTZ`, default `now()`).
- **Индексы**:
  - `ix_price_records_ticker_timestamp` (`ticker`, `timestamp`) — для мгновенного выполнения запросов с фильтрацией по диапазону дат.
  - `ix_price_records_ticker_timestamp_desc` (`ticker`, `timestamp DESC`) — для мгновенного получения последней цены (`LIMIT 1`).

### 6. Стратегия двухконтейнерного развертывания
- **Требование ТЗ**: *"Развернуть приложение в двух контейнерах для приложения и базы данных."*
- **Решение**: В стандартном микросервисном подходе требуется 5 контейнеров (Postgres, Redis, Web, Worker, Beat). Чтобы в точности выполнить требование о **двух контейнерах**:
  - **Контейнер 1 (`db`)**: Официальный легковесный образ `postgres:16-alpine`.
  - **Контейнер 2 (`app`)**: Образ приложения, в котором скрипт `entrypoint.sh` автоматически:
    1. Ждет доступности порта PostgreSQL.
    2. Применяет миграции схемы через Alembic.
    3. Поднимает легковесный локальный брокер Redis в фоне.
    4. Запускает Celery Worker в фоне для обработки очереди сбора цен.
    5. Запускает Celery Beat в фоне для генерации поминутных тиков.
    6. Запускает сервер FastAPI с Uvicorn в основном потоке (foreground).
- **Гибкость**: Для промышленного продакшена также подготовлен файл `docker-compose.microservices.yml`, разделяющий сервисы на отдельные контейнеры.

### 7. Изоляция ошибок в фоновом сборщике
- Если вызов Deribit для одного из тикеров (например, `btc_usd`) возвращает ошибку или тайм-аут, сбор цен для второго тикера (`eth_usd`) **не прерывается**. Ошибка логируется с полным трейсбеком, а успешные обновления надежно коммитятся в базу данных.

---

## 👨‍💻 Автор и сдача задания
- Выполнено в строгом соответствии с требованиями для позиции Junior Backend Developer.
- Код готов к пушу в GitLab с настроенным CI пайплайном (`.gitlab-ci.yml`).
