#!/usr/bin/env bash
set -euo pipefail

echo "=== Fetching ITMO knowledge base ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q trafilatura httpx

python3 -c "
from app.rag.vectorstore import fetch_knowledge_base
fetch_knowledge_base()
print('Knowledge base fetched into data/')
"

echo "=== Done ==="
