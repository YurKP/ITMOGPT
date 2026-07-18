# ИТМО GPT — Полная инструкция по запуску

## Быстрый запуск (локально)

```bash
cd itmogpt

# 1. Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt
pip install "numpy<2"  # фикс для Python 3.9

# 3. Скопировать и заполнить .env
cp .env.example .env
nano .env  # вставить API ключ

# 4. Запустить веб-сервер
python run_web.py
# Сервер будет на http://localhost:8080
```

## Быстрый запуск (Docker)

```bash
cd itmogpt
cp .env.example .env
nano .env  # вставить API ключ
docker compose up -d --build
# Сервер будет на http://localhost:8080
```

---

## Настройка .env

### OpenAI (напрямую)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
```

### OpenRouter
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o-mini
OPENAI_EMBED_MODEL=openai/text-embedding-3-small
```

### YandexGPT
```env
LLM_PROVIDER=yandex
YA_API_KEY=ваш_ключ
YA_FOLDER_ID=ваш_folder_id
```

### Telegram-бот (опционально)
```env
BOT_TOKEN=123456:ABC-DEF...
ALLOWED_USERS=username1,username2
```

### Интеграция с Вобщаге (опционально)
```env
VOBSHAGE_API_URL=https://xn--80abcgk4c7d.fun
```

---

## Добавление данных для RAG

### Способ 1: Парсинг Telegram-чатов

1. Экспортируйте чат из **Telegram Desktop**:
   - Откройте чат → ⋮ → Export chat history → Format: JSON
   - Получите файл `result.json`

2. Запустите парсер:
```bash
source .venv/bin/activate
python scripts/parse_telegram_chats.py result.json --output-dir data/
```

3. Скрипт создаст `.md` файлы в `data/` — по одному на каждый диалог с ответом оператора.

4. Удалите старый индекс и перезапустите:
```bash
rm -rf chroma_db/
python run_web.py
```

### Способ 2: Ручное добавление документов

Положите любые `.md` файлы в папку `data/`:
```bash
echo "# Расписание экзаменов
Зимняя сессия начинается 15 января..." > data/raspisanie.md
```

Удалите `chroma_db/` и перезапустите — файлы будут проиндексированы автоматически.

### Способ 3: Автоматический парсинг сайтов ИТМО

```bash
source .venv/bin/activate
bash scripts/fetch_data.sh
```

Скрипт скачает контент с сайтов ИТМО (itmo.ru, student.itmo.ru и др.) в `data/`.

---

## Модули и как их вызывать

### 💬 Обычный чат (RAG)
Просто задайте вопрос:
- "Как получить стипендию?"
- "Где находится библиотека?"
- "Расскажи про общагу"

### 📚 Гостомысл (поиск статей + ГОСТ)
Ключевые слова: `список литературы`, `найди статьи`, `arxiv`, `библиография`, `ГОСТ`, `научные статьи`

Примеры:
- "Найди статьи про machine learning for NLP"
- "Составь список литературы по теме reinforcement learning"
- "Arxiv статьи про transformer architecture"

### 🧠 Выготский (графы знаний)
Ключевые слова: `граф знаний`, `путь обучения`, `что изучить`, `вакансия`, `навыки`

Примеры:
- "Что изучить для вакансии ML Engineer"
- "Граф знаний: Data Science | знаю Python и статистику"
- "Построй путь обучения для backend-разработчика"

Формат с указанием своих знаний: `тема | описание своих навыков`

### 🏠 Вобщаге (данные общежития)
Ключевые слова: `общага`, `общежитие`, `комната`, `этаж`, `кухня`, `сосед`, `где тусят`

Примеры:
- "Что сейчас происходит в общаге?"
- "Где самые крутые соседи?"
- "На каком этаже сейчас веселее всего?"

Требует `VOBSHAGE_API_URL` в `.env`.

---

## Запуск Telegram-бота

```bash
source .venv/bin/activate
python run_bot.py
```

Бот и веб-сервер могут работать одновременно (в разных терминалах).

---

## Деплой на Ubuntu VPS (Яндекс Облако)

```bash
# На сервере
sudo apt update && sudo apt install -y git docker.io docker-compose-plugin
git clone <repo-url> /opt/itmogpt
cd /opt/itmogpt

# Настройка
cp .env.example .env
nano .env

# Для HTTPS — задать домен
echo "DOMAIN=itmogpt.example.com" >> .env

# Запуск
docker compose up -d --build

# Логи
docker compose logs -f web
docker compose logs -f bot
```

Caddy автоматически получит SSL-сертификат для указанного домена.

---

## Структура данных

```
data/                          ← Документы для RAG (любые .md файлы)
├── itmo.ru.md                 ← Автоматически скачанные с сайтов ИТМО
├── student.itmo.ru_ru_scholarship_.md
├── tg_dialog_20240115_1430_0001.md  ← Из парсера Telegram
└── my_custom_doc.md           ← Ваши документы

chroma_db/                     ← Векторный индекс (генерируется автоматически)
```

При изменении файлов в `data/` — удалите `chroma_db/` и перезапустите.

---

## Полный скрипт запуска (copy-paste)

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")"

# Создаём venv если нет
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

# Устанавливаем зависимости
pip install -q -r requirements.txt
pip install -q "numpy<2"

# Проверяем .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Создан .env — заполните API ключи!"
    echo "   nano .env"
    exit 1
fi

# Создаём директории
mkdir -p data chroma_db

# Запускаем
echo "🚀 Запуск ИТМО GPT на http://localhost:8080"
python run_web.py
```
