"""
Простой JSONL-логгер для аналитики ВОБЩАГЕ.

Пишет в файл /var/log/vobshage/events.jsonl (в Docker)
или ./logs/events.jsonl (локально).

Каждая строка — JSON-объект. Парсить:
  cat events.jsonl | jq .
  grep '"event":"login"' events.jsonl | jq .
  grep '"ip":"1.2.3.4"' events.jsonl
  cat events.jsonl | jq 'select(.event=="login")' | jq -s 'length'
  cat events.jsonl | jq 'select(.event=="connect") | .ip' | sort -u | wc -l
"""

import json
import os
import time
from datetime import datetime, timezone

# Путь к файлу логов — Docker volume или локальная папка
LOG_DIR = os.getenv("LOG_DIR", "/var/log/vobshage")
LOG_FILE = os.path.join(LOG_DIR, "events.jsonl")

# Создаем директорию если нет
os.makedirs(LOG_DIR, exist_ok=True)

# Открываем файл в append-режиме
_log_file = open(LOG_FILE, "a", encoding="utf-8", buffering=1)  # line-buffered


def log(event: str, **kwargs):
    """
    Записывает одну строку JSON в лог-файл.
    
    Примеры:
      log("connect", sid="abc", ip="1.2.3.4")
      log("login", sid="abc", ip="1.2.3.4", nickname="Дикий Пупсик", skin="🤡")
      log("join_room", sid="abc", nickname="Дикий Пупсик", room_id="5_501")
      log("interact", sid="abc", nickname="Дикий Пупсик", action="add_item", emoji="🍕")
      log("disconnect", sid="abc", nickname="Дикий Пупсик", ip="1.2.3.4")
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    entry.update(kwargs)
    
    line = json.dumps(entry, ensure_ascii=False, default=str)
    _log_file.write(line + "\n")
    # Также дублируем в stdout для docker logs
    print(f"[LOG] {line}")
