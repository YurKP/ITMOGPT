# ИТМО GPT

Экосистема студенческих инструментов Университета ИТМО.

> Как пройти в библиотеку? Насколько препод лайтовый? Где брать БСК? Когда уже в общагу вернут тёплую воду? На все эти и многие другие вопросы ответ знает великий и неповторимый ИТМО GPT!

## Модули

| Модуль | Описание | Статус |
|--------|----------|--------|
| **ИТМО GPT** (чат) | RAG-бот поверх университетских документов и ответов из чатов | ✅ |
| **Гостомысл** | Поиск научных статей на ArXiv + ГОСТ-библиография | ✅ |
| **Выготский** | Графы знаний и персональные пути обучения | ✅ |
| **Вобщаге** | Интерактивная карта общежития (отдельное приложение на [вобщаге.fun](https://xn--80abcgk4c7d.fun)) | 🔗 |

## Быстрый старт

### 1. Подготовка

```bash
git clone <repo-url> itmogpt
cd itmogpt
bash scripts/setup.sh
```

### 2. Настройка

Отредактируйте `.env`:

```bash
nano .env
```

Минимально нужно задать:
- `LLM_PROVIDER` — `openai` или `yandex`
- Ключи API для выбранного провайдера
- `BOT_TOKEN` — токен Telegram-бота (если нужен бот)

### 3. Запуск через Docker

```bash
docker compose up -d --build
```

Сайт будет доступен на порту 8080 (или через Caddy на 80/443 если задан `DOMAIN`).

### 4. Запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Веб-сервер
python run_web.py

# Telegram-бот (в отдельном терминале)
python run_bot.py
```

## Парсинг чатов Telegram

Экспортируйте чат из Telegram Desktop (JSON-формат), затем:

```bash
python scripts/parse_telegram_chats.py result.json --output-dir data/
```

Скрипт извлечёт диалоги с ответами операторов и сохранит их как `.md` файлы для RAG.

## Структура проекта

```
itmogpt/
├── app/
│   ├── config.py              # Конфигурация
│   ├── llm/
│   │   ├── factory.py         # Фабрика LLM/Embeddings
│   │   ├── yandex.py          # Клиент YandexGPT
│   │   └── openai_compat.py   # Клиент OpenAI
│   ├── rag/
│   │   ├── vectorstore.py     # Построение векторного хранилища
│   │   └── chain.py           # RAG-цепочка с историей
│   ├── modules/
│   │   ├── router.py          # Маршрутизатор запросов
│   │   ├── gostomysl/         # Модуль Гостомысл
│   │   │   ├── workflow.py
│   │   │   └── agents/
│   │   └── vygotsky/          # Модуль Выготский
│   │       └── graph.py
│   ├── bot/
│   │   └── telegram.py        # Telegram-бот
│   └── web/
│       ├── api.py             # FastAPI backend
│       ├── templates/
│       └── static/
├── scripts/
│   ├── setup.sh               # Установка зависимостей
│   ├── fetch_data.sh           # Скачивание базы знаний
│   └── parse_telegram_chats.py # Парсер чатов Telegram
├── data/                       # Документы для RAG
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.bot
├── requirements.txt
├── run_web.py
├── run_bot.py
└── .env.example
```

## Деплой на Ubuntu VPS (Яндекс Облако)

```bash
# На сервере
sudo apt update && sudo apt install -y git
git clone <repo-url> /opt/itmogpt
cd /opt/itmogpt
bash scripts/setup.sh
nano .env  # заполнить ключи
docker compose up -d --build
```

Для HTTPS задайте `DOMAIN=yourdomain.ru` в `.env` — Caddy автоматически получит сертификат.

## Провайдеры LLM

| Провайдер | `LLM_PROVIDER` | Что нужно |
|-----------|----------------|-----------|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| YandexGPT | `yandex` | `YA_API_KEY`, `YA_FOLDER_ID` |

Можно использовать любой OpenAI-совместимый API (Ollama, vLLM и т.д.) через `OPENAI_BASE_URL`.
