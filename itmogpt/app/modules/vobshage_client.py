import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import cfg

logger = logging.getLogger("itmogpt.vobshage")


async def fetch_dorm_summary() -> Optional[Dict[str, Any]]:
    if not cfg.VOBSHAGE_API_URL:
        return None
    url = f"{cfg.VOBSHAGE_API_URL.rstrip('/')}/api/dorm-summary"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch dorm summary: {e}")
        return None


def format_dorm_context(data: Dict[str, Any]) -> str:
    lines = ["Актуальные данные из общежития (Вобщаге):"]

    online = data.get("online_by_floor", {})
    if online:
        total = sum(int(v) for v in online.values())
        lines.append(f"Сейчас онлайн: {total} чел.")
        top_floors = sorted(online.items(), key=lambda x: int(x[1]), reverse=True)[:3]
        if top_floors:
            lines.append("Самые тусовые этажи: " + ", ".join(f"{f}-й ({c} чел.)" for f, c in top_floors))

    top_rooms = data.get("top_rooms_activity", [])
    if top_rooms:
        room_strs = [f"{r[0]} ({r[1]} событий)" for r in top_rooms[:5]]
        lines.append("Самые активные комнаты: " + ", ".join(room_strs))

    top_emoji = data.get("top_emoji", [])
    if top_emoji:
        emoji_strs = [f"{e[0]}×{e[1]}" for e in top_emoji[:7]]
        lines.append("Популярные эмодзи: " + " ".join(emoji_strs))

    issues = data.get("floor_issues", {})
    if issues:
        for floor, problems in issues.items():
            lines.append(f"⚠️ Этаж {floor}: {', '.join(problems)}")

    top_rated = data.get("top_rated_rooms", [])
    if top_rated:
        rated_strs = [f"{r[0]} (❤️{r[1]['hearts']})" for r in top_rated[:3]]
        lines.append("Лучшие комнаты: " + ", ".join(rated_strs))

    worst = data.get("worst_rated_rooms", [])
    if worst:
        worst_strs = [f"{r[0]} (мусор:{r[1]['trash']})" for r in worst[:3]]
        lines.append("Проблемные комнаты: " + ", ".join(worst_strs))

    return "\n".join(lines)
