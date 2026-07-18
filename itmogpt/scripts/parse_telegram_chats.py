#!/usr/bin/env python3
"""
Parse Telegram chat export (JSON) and extract successful operator dialogs
into .md documents suitable for RAG ingestion.

Usage:
    python scripts/parse_telegram_chats.py <export.json> [--output-dir data/]

Telegram Desktop exports chats as result.json with structure:
{
  "messages": [
    {"id": 1, "type": "message", "from": "...", "text": "...", ...},
    ...
  ]
}

The script groups consecutive messages into dialogs (separated by >30 min gaps),
keeps only dialogs where an operator replied, and writes each dialog as a .md file.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

OPERATOR_MARKERS = [
    "оператор",
    "operator",
    "admin",
    "администратор",
    "поддержка",
    "support",
]

GAP_THRESHOLD = timedelta(minutes=30)


def _extract_text(msg: dict) -> str:
    text = msg.get("text", "")
    if isinstance(text, list):
        parts = []
        for chunk in text:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict):
                parts.append(chunk.get("text", ""))
        return "".join(parts)
    return str(text)


def _is_operator(msg: dict) -> bool:
    sender = (msg.get("from", "") or "").lower()
    for marker in OPERATOR_MARKERS:
        if marker in sender:
            return True
    from_id = msg.get("from_id", "")
    if isinstance(from_id, str) and from_id.startswith("channel"):
        return True
    return False


def _parse_date(msg: dict) -> datetime:
    raw = msg.get("date", "2000-01-01T00:00:00")
    return datetime.fromisoformat(raw)


def split_into_dialogs(messages: list[dict]) -> list[list[dict]]:
    dialogs: list[list[dict]] = []
    current: list[dict] = []

    for msg in messages:
        if msg.get("type") != "message":
            continue
        text = _extract_text(msg)
        if not text.strip():
            continue

        if current:
            prev_time = _parse_date(current[-1])
            curr_time = _parse_date(msg)
            if curr_time - prev_time > GAP_THRESHOLD:
                dialogs.append(current)
                current = []

        current.append(msg)

    if current:
        dialogs.append(current)

    return dialogs


def dialog_has_operator(dialog: list[dict]) -> bool:
    return any(_is_operator(m) for m in dialog)


def dialog_to_markdown(dialog: list[dict]) -> str:
    lines = []
    for msg in dialog:
        sender = msg.get("from", "Пользователь")
        text = _extract_text(msg)
        role = "Оператор" if _is_operator(msg) else "Студент"
        lines.append(f"**{role}** ({sender}):\n{text}\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse Telegram chat export into RAG documents")
    parser.add_argument("export_json", help="Path to Telegram export result.json")
    parser.add_argument("--output-dir", default="data", help="Output directory for .md files")
    parser.add_argument("--min-messages", type=int, default=2, help="Minimum messages in dialog")
    args = parser.parse_args()

    with open(args.export_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    if not messages:
        print("No messages found in export.")
        sys.exit(1)

    print(f"Total messages: {len(messages)}")

    dialogs = split_into_dialogs(messages)
    print(f"Total dialogs: {len(dialogs)}")

    successful = [d for d in dialogs if dialog_has_operator(d) and len(d) >= args.min_messages]
    print(f"Dialogs with operator response (>={args.min_messages} msgs): {len(successful)}")

    os.makedirs(args.output_dir, exist_ok=True)

    for i, dialog in enumerate(successful, 1):
        date_str = _parse_date(dialog[0]).strftime("%Y%m%d_%H%M")
        filename = f"tg_dialog_{date_str}_{i:04d}.md"
        filepath = os.path.join(args.output_dir, filename)
        md = dialog_to_markdown(dialog)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

    print(f"Written {len(successful)} dialog files to {args.output_dir}/")


if __name__ == "__main__":
    main()
