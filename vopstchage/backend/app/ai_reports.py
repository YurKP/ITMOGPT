import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOG_DIR = os.getenv("LOG_DIR", "/var/log/vobshage")
LOG_FILE = os.path.join(LOG_DIR, "events.jsonl")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
YA_API_KEY = os.getenv("YA_API_KEY", "")
YA_FOLDER_ID = os.getenv("YA_FOLDER_ID", "")


async def _call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "yandex" and YA_API_KEY:
        return await _call_yandex(prompt)
    return await _call_openai(prompt)


async def _call_openai(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_yandex(prompt: str) -> str:
    model_uri = f"gpt://{YA_FOLDER_ID}/yandexgpt/latest"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={
                "Authorization": f"Api-Key {YA_API_KEY}",
                "Content-Type": "application/json",
                "x-folder-id": YA_FOLDER_ID,
            },
            json={
                "modelUri": model_uri,
                "completionOptions": {"stream": False, "temperature": 0.7, "maxTokens": 2000},
                "messages": [{"role": "user", "text": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        node = data.get("result", data)
        alts = node.get("alternatives", [])
        if alts:
            return alts[0].get("message", {}).get("text", "")
        return ""


def _parse_logs(hours: int = 24) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = []
    if not os.path.exists(LOG_FILE):
        return events
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry.get("ts", "2000-01-01T00:00:00+00:00"))
                if ts >= cutoff:
                    events.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue
    return events


async def _get_all_room_items(r: aioredis.Redis) -> Dict[str, List[Dict]]:
    rooms = {}
    keys = await r.keys("room:*:items")
    for key in keys:
        room_id = key.split(":")[1]
        raw = await r.get(key)
        if raw:
            items = json.loads(raw)
            rooms[room_id] = items
    return rooms


async def collect_dorm_stats(hours: int = 24) -> Dict[str, Any]:
    events = _parse_logs(hours)

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    room_items = await _get_all_room_items(r)
    global_stats_keys = await r.keys("room:*:users")
    online_by_floor: Dict[str, int] = defaultdict(int)
    for key in global_stats_keys:
        room_id = key.split(":")[1]
        floor = room_id.split("_")[0] if not room_id.startswith("floor_") else room_id.split("_")[1]
        count = await r.scard(key)
        online_by_floor[floor] += count
    await r.aclose()

    emoji_by_room: Dict[str, Counter] = defaultdict(Counter)
    for room_id, items in room_items.items():
        for item in items:
            emoji_by_room[room_id][item.get("emoji", "?")] += 1

    emoji_by_floor: Dict[str, Counter] = defaultdict(Counter)
    for room_id, counter in emoji_by_room.items():
        floor = room_id.split("_")[0] if not room_id.startswith("floor_") else room_id.split("_")[1]
        emoji_by_floor[floor] += counter

    event_counts = Counter(e.get("event") for e in events)
    interact_events = [e for e in events if e.get("event") == "interact"]
    emoji_placed = Counter(e.get("emoji") for e in interact_events if e.get("action") == "add_item")

    room_activity: Counter = Counter()
    for e in events:
        if e.get("room_id"):
            room_activity[e["room_id"]] += 1

    top_rooms = room_activity.most_common(10)
    top_emoji = emoji_placed.most_common(15)

    trash_emoji = {"💩", "🗑", "🧦", "🪳"}
    party_emoji = {"🎸", "🎉", "🔥", "❤️", "🍕"}
    water_emoji = {"💧", "🚿"}

    floor_issues: Dict[str, List[str]] = defaultdict(list)
    for floor, counter in emoji_by_floor.items():
        trash_count = sum(counter.get(e, 0) for e in trash_emoji)
        party_count = sum(counter.get(e, 0) for e in party_emoji)
        water_count = sum(counter.get(e, 0) for e in water_emoji)
        if trash_count > 5:
            floor_issues[floor].append(f"мусор ({trash_count} эмодзи)")
        if party_count > 5:
            floor_issues[floor].append(f"вечеринка ({party_count} эмодзи)")
        if water_count > 3:
            floor_issues[floor].append(f"жалобы на воду ({water_count} эмодзи)")

    room_ratings: Dict[str, Dict] = {}
    for room_id, items in room_items.items():
        hearts = sum(1 for i in items if i.get("emoji") == "❤️")
        trash = sum(1 for i in items if i.get("emoji") in trash_emoji)
        total = len(items)
        room_ratings[room_id] = {"hearts": hearts, "trash": trash, "total": total}

    top_rated = sorted(room_ratings.items(), key=lambda x: x[1]["hearts"], reverse=True)[:5]
    worst_rated = sorted(room_ratings.items(), key=lambda x: x[1]["trash"], reverse=True)[:5]

    return {
        "period_hours": hours,
        "total_events": len(events),
        "event_counts": dict(event_counts),
        "online_by_floor": dict(online_by_floor),
        "top_rooms_activity": top_rooms,
        "top_emoji": top_emoji,
        "floor_issues": dict(floor_issues),
        "top_rated_rooms": [(r, d) for r, d in top_rated if d["hearts"] > 0],
        "worst_rated_rooms": [(r, d) for r, d in worst_rated if d["trash"] > 0],
        "emoji_by_floor": {f: dict(c) for f, c in emoji_by_floor.items()},
        "room_ratings": room_ratings,
    }


ADMIN_REPORT_PROMPT = """Ты — AI-аналитик общежития ИТМО. Напиши краткую утреннюю сводку для коменданта.

Данные за последние {hours} часов:
- Всего событий: {total_events}
- Онлайн по этажам: {online_by_floor}
- Самые активные комнаты: {top_rooms}
- Популярные эмодзи: {top_emoji}
- Проблемные этажи: {floor_issues}
- Лучшие комнаты (❤️): {top_rated}
- Худшие комнаты (мусор): {worst_rated}

Напиши сводку в формате:
1. Общая обстановка (1-2 предложения)
2. Проблемные зоны (конкретные этажи/комнаты и что не так)
3. Позитивные моменты
4. Рекомендации для коменданта

Стиль: деловой, но дружелюбный. Используй эмодзи. Максимум 300 слов."""


NEWSPAPER_PROMPT = """Ты — шуточный AI-журналист общежития ИТМО. Напиши выпуск газеты «Слухи Общаги» 🗞️

Данные за последние {hours} часов:
- Самые активные комнаты: {top_rooms}
- Популярные эмодзи: {top_emoji}
- Лучшие комнаты по рейтингу (❤️): {top_rated}
- Худшие комнаты (мусор): {worst_rated}
- Эмодзи по этажам: {emoji_by_floor}
- Онлайн по этажам: {online_by_floor}

Напиши шуточную газету с разделами:
🔥 МОЛНИЯ! (главная новость — самое интересное событие)
📊 РЕЙТИНГ ДНЯ (кто поднялся, кто упал)
🕵️ РАССЛЕДОВАНИЕ (что происходит на проблемных этажах)
💕 СВЕТСКАЯ ХРОНИКА (кто кому ставил сердечки)
🏆 КОМНАТА ДНЯ

Стиль: весёлый, ироничный, студенческий. Без перехода на личности (используй номера комнат).
Используй эмодзи щедро. Максимум 400 слов. Пиши на русском."""


async def generate_admin_report(hours: int = 24) -> Dict[str, Any]:
    stats = await collect_dorm_stats(hours)
    prompt = ADMIN_REPORT_PROMPT.format(
        hours=hours,
        total_events=stats["total_events"],
        online_by_floor=json.dumps(stats["online_by_floor"], ensure_ascii=False),
        top_rooms=json.dumps(stats["top_rooms_activity"], ensure_ascii=False),
        top_emoji=json.dumps(stats["top_emoji"], ensure_ascii=False),
        floor_issues=json.dumps(stats["floor_issues"], ensure_ascii=False),
        top_rated=json.dumps(stats["top_rated_rooms"], ensure_ascii=False),
        worst_rated=json.dumps(stats["worst_rated_rooms"], ensure_ascii=False),
    )
    report_text = await _call_llm(prompt)
    return {
        "report": report_text,
        "stats": stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_newspaper(hours: int = 24) -> Dict[str, Any]:
    stats = await collect_dorm_stats(hours)
    prompt = NEWSPAPER_PROMPT.format(
        hours=hours,
        top_rooms=json.dumps(stats["top_rooms_activity"], ensure_ascii=False),
        top_emoji=json.dumps(stats["top_emoji"], ensure_ascii=False),
        top_rated=json.dumps(stats["top_rated_rooms"], ensure_ascii=False),
        worst_rated=json.dumps(stats["worst_rated_rooms"], ensure_ascii=False),
        emoji_by_floor=json.dumps(stats["emoji_by_floor"], ensure_ascii=False),
        online_by_floor=json.dumps(stats["online_by_floor"], ensure_ascii=False),
    )
    newspaper_text = await _call_llm(prompt)
    return {
        "newspaper": newspaper_text,
        "stats": stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_dorm_summary_for_itmogpt() -> Dict[str, Any]:
    stats = await collect_dorm_stats(24)
    return {
        "online_by_floor": stats["online_by_floor"],
        "top_rooms_activity": stats["top_rooms_activity"][:5],
        "top_emoji": stats["top_emoji"][:10],
        "floor_issues": stats["floor_issues"],
        "top_rated_rooms": stats["top_rated_rooms"][:5],
        "worst_rated_rooms": stats["worst_rated_rooms"][:5],
        "total_events_24h": stats["total_events"],
    }
