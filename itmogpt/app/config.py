from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    YA_API_KEY: str = os.getenv("YA_API_KEY", "")
    YA_FOLDER_ID: str = os.getenv("YA_FOLDER_ID", "")
    YA_GPT_MODEL: str = os.getenv("YA_GPT_MODEL", "yandexgpt/latest")
    YA_EMBED_MODEL: str = os.getenv("YA_EMBED_MODEL", "text-search-doc/latest")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ALLOWED_USERS: list[str] = [
        u.strip().lower()
        for u in os.getenv("ALLOWED_USERS", "").split(",")
        if u.strip()
    ]

    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./chroma_db")

    ARXIV_MAX_RESULTS: int = int(os.getenv("ARXIV_MAX_RESULTS", "100"))
    GOSTOMYSL_TOP_K_BM25: int = int(os.getenv("GOSTOMYSL_TOP_K_BM25", "50"))
    GOSTOMYSL_TOP_K_EMBED: int = int(os.getenv("GOSTOMYSL_TOP_K_EMBED", "25"))
    GOSTOMYSL_TOP_K_FINAL: int = int(os.getenv("GOSTOMYSL_TOP_K_FINAL", "10"))

    VOBSHAGE_API_URL: str = os.getenv("VOBSHAGE_API_URL", "")

    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))

    @classmethod
    def ya_chat_model_uri(cls) -> str:
        return f"gpt://{cls.YA_FOLDER_ID}/{cls.YA_GPT_MODEL}"

    @classmethod
    def ya_embed_model_uri(cls) -> str:
        return f"emb://{cls.YA_FOLDER_ID}/{cls.YA_EMBED_MODEL}"


cfg = Config()
