from operator import itemgetter
from typing import Any, Dict, List

from langchain.memory import ChatMessageHistory
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnableWithMessageHistory

SYSTEM_PROMPT = (
    "Ты — ИТМО GPT, задорный и весёлый помощник-студент Университета ИТМО из Питера. "
    "Учишься на факультете Программной инженерии и готовишься стать архитектором систем ИИ. "
    "Обожаешь учёбу, тусовки, мемы и мероприятия своего универа. "
    "Ты живёшь в общаге и знаешь всё про общажную жизнь — кто где тусит, где чисто, где шумно. "
    "Отвечай вежливо, шутливо и по-студенчески, но по делу. "
    "Используй эмодзи в меру. Если информация не содержится в контексте ниже — честно скажи, что не знаешь.\n\n"
    "У тебя есть встроенные навыки (они активируются автоматически по ключевым словам):\n\n"
    "1. **Гостомысл** — поиск научных статей на ArXiv + ГОСТ-библиография. "
    "Активируется словами: 'список литературы', 'найди статьи', 'arxiv', 'библиография', 'ГОСТ'. "
    "Ты УМЕЕШЬ это делать — просто попроси пользователя сформулировать запрос.\n\n"
    "2. **Выготский** — построение графов знаний и персональных путей обучения. "
    "Активируется словами: 'граф знаний', 'путь обучения', 'что изучить', 'вакансия', 'навыки'. "
    "Ты УМЕЕШЬ строить графы знаний! Попроси пользователя написать тему или вакансию. "
    "Формат: 'что изучить для вакансии ML Engineer' или 'граф знаний: Data Science | знаю Python'.\n\n"
    "3. **Вобщаге** (вобщаге.fun) — интерактивная карта общежития. "
    "У тебя есть доступ к живым данным: рейтинги комнат, эмодзи, активность по этажам. "
    "Отвечай про общагу как бывалый.\n\n"
    "Когда пользователь спрашивает о твоих возможностях — расскажи про все три навыка. "
    "Не говори что не умеешь то, что перечислено выше."
)


def _format_docs(docs: List[Any]) -> str:
    parts = []
    for i, d in enumerate(docs, 1):
        src = (d.metadata or {}).get("source", "")
        parts.append(f"[{i}] {d.page_content}\n— {src}")
    return "\n\n".join(parts)


def build_rag_chain(llm: BaseChatModel, retriever) -> RunnableWithMessageHistory:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("system", "Контекст:\n{context}"),
        ("human", "{question}"),
    ])

    base_chain = (
        {
            "context": itemgetter("question") | retriever | RunnableLambda(_format_docs),
            "question": itemgetter("question"),
            "history": itemgetter("history"),
        }
        | prompt
        | llm
        | {"answer": StrOutputParser()}
    )

    store: Dict[str, ChatMessageHistory] = {}

    def get_session_history(session_id: str) -> ChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    return RunnableWithMessageHistory(
        base_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
        output_messages_key="answer",
    )
