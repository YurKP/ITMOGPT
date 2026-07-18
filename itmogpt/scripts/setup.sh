#!/usr/bin/env bash
set -euo pipefail

echo "=== ИТМО GPT — Setup ==="

if ! command -v python3 &>/dev/null; then
    echo "Installing Python 3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
fi

if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to re-login for group changes."
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get install -y docker-compose-plugin
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — edit it with your API keys!"
fi

mkdir -p data chroma_db

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run with Docker:  docker compose up -d --build"
echo "  3. Or run locally:"
echo "     python3 -m venv .venv"
echo "     source .venv/bin/activate"
echo "     pip install -r requirements.txt"
echo "     python run_web.py    # web on :8080"
echo "     python run_bot.py    # telegram bot"
echo ""
echo "  4. To parse Telegram chat exports:"
echo "     python scripts/parse_telegram_chats.py <export.json> --output-dir data/"
