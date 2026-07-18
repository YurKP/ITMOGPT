from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def make_openai_chat(
    api_key: str,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> BaseChatModel:
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def make_openai_embeddings(
    api_key: str,
    model: str = "text-embedding-3-small",
    base_url: str = "https://api.openai.com/v1",
) -> Embeddings:
    return OpenAIEmbeddings(
        api_key=api_key,
        model=model,
        base_url=base_url,
    )
