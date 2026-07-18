from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import cfg
from app.llm.openai_compat import make_openai_chat, make_openai_embeddings
from app.llm.yandex import YandexChat, YandexEmbeddings


def get_chat_llm() -> BaseChatModel:
    if cfg.LLM_PROVIDER == "yandex":
        return YandexChat(
            api_key=cfg.YA_API_KEY,
            folder_id=cfg.YA_FOLDER_ID,
            model_uri=cfg.ya_chat_model_uri(),
        )
    return make_openai_chat(
        api_key=cfg.OPENAI_API_KEY,
        model=cfg.OPENAI_MODEL,
        base_url=cfg.OPENAI_BASE_URL,
    )


def get_embeddings() -> Embeddings:
    if cfg.LLM_PROVIDER == "yandex":
        return YandexEmbeddings(
            api_key=cfg.YA_API_KEY,
            folder_id=cfg.YA_FOLDER_ID,
            model_uri=cfg.ya_embed_model_uri(),
        )
    return make_openai_embeddings(
        api_key=cfg.OPENAI_API_KEY,
        model=cfg.OPENAI_EMBED_MODEL,
        base_url=cfg.OPENAI_BASE_URL,
    )
