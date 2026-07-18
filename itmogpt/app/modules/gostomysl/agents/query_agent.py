import json
from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

QUERY_SYSTEM = (
    "Ты — эксперт по научному поиску. Улучши и расширь поисковый запрос пользователя. "
    "Сгенерируй 3-5 улучшенных вариантов запроса для поиска научных статей на ArXiv. "
    "Включи синонимы, связанные термины и английские переводы.\n\n"
    "Ответ строго в JSON:\n"
    '{"enhanced_queries": ["..."], "arxiv_queries": ["..."], "keywords": ["..."]}'
)


class QueryAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def process_query(self, user_query: str) -> Dict:
        language = "русский" if any(ord(c) > 127 for c in user_query) else "английский"
        prompt = f"Исходный запрос: {user_query}\nЯзык запроса: {language}"

        resp = self.llm.invoke([
            SystemMessage(content=QUERY_SYSTEM),
            HumanMessage(content=prompt),
        ])
        text = resp.content.strip().strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {
                "enhanced_queries": [user_query],
                "arxiv_queries": [user_query],
                "keywords": user_query.split(),
            }
