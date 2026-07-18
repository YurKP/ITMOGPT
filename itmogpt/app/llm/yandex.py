import asyncio
import json
from typing import Any, Dict, List, Optional, Union

import httpx
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

YC_COMPLETIONS_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YC_EMBEDDING_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"


def _msg_to_yc(msg: BaseMessage) -> Dict[str, str]:
    if isinstance(msg, SystemMessage):
        role = "system"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    else:
        role = "user"
    text = msg.content if isinstance(msg.content, str) else json.dumps(msg.content, ensure_ascii=False)
    return {"role": role, "text": text}


def _extract_text(resp: Dict[str, Any]) -> str:
    node = resp.get("result") or resp
    alts = node.get("alternatives")
    if isinstance(alts, list) and alts:
        alt = alts[0]
        msg = alt.get("message") if isinstance(alt, dict) else None
        if isinstance(msg, dict) and isinstance(msg.get("text"), str):
            return msg["text"]
        if isinstance(alt.get("text"), str):
            return alt["text"]
    for key in ("text", "answer", "content"):
        val = node.get(key)
        if isinstance(val, str):
            return val
    return json.dumps(resp, ensure_ascii=False)


class YandexChat(BaseChatModel):
    api_key: str
    folder_id: str
    model_uri: str
    completion_url: str = YC_COMPLETIONS_URL
    temperature: float = 0.3
    max_tokens: int = 1500
    timeout: float = 60.0

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
            "x-folder-id": self.folder_id,
        }

    def _payload(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        return {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": self.max_tokens,
            },
            "messages": [_msg_to_yc(m) for m in messages],
        }

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.completion_url, headers=self._headers(), json=self._payload(messages))
            resp.raise_for_status()
        text = _extract_text(resp.json())
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.completion_url, headers=self._headers(), json=self._payload(messages))
            resp.raise_for_status()
        text = _extract_text(resp.json())
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    @property
    def _llm_type(self) -> str:
        return "yandex-chat"


class YandexEmbeddings(Embeddings):
    api_key: str
    folder_id: str
    model_uri: str
    embedding_url: str = YC_EMBEDDING_URL
    timeout: float = 60.0

    def __init__(self, api_key: str, folder_id: str, model_uri: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.folder_id = folder_id
        self.model_uri = model_uri

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
            "x-folder-id": self.folder_id,
        }

    async def _aembed_one(self, client: httpx.AsyncClient, text: Union[str, dict]) -> List[float]:
        if isinstance(text, dict):
            text = text.get("question", text.get("text", str(text)))
        payload = {"modelUri": self.model_uri, "text": text}
        r = await client.post(self.embedding_url, headers=self._headers(), json=payload)
        r.raise_for_status()
        node = r.json().get("result", r.json())
        emb = node.get("embedding")
        if not emb:
            raise RuntimeError(f"Failed to extract embedding: {r.json()}")
        return emb

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            results = []
            for t in texts:
                emb = await self._aembed_one(client, t)
                results.append(emb)
                await asyncio.sleep(0.3)
            return results

    async def aembed_query(self, text: str) -> List[float]:
        res = await self.aembed_documents([text])
        return res[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        return asyncio.run(self.aembed_query(text))
