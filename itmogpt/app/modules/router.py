from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableWithMessageHistory

from app.modules.gostomysl.workflow import GostomyslWorkflow
from app.modules.vobshage_client import fetch_dorm_summary, format_dorm_context
from app.modules.vygotsky.graph import VygotskyEngine

DORM_KEYWORDS = [
    "общаг", "общежити", "комнат", "этаж", "кухн", "сосед",
    "вобщаге", "шум", "вечеринк", "мусор", "рейтинг комнат",
    "где тусят", "где весело", "где тихо", "где грязно",
]


class ITMORouter:
    def __init__(
        self,
        llm: BaseChatModel,
        rag_chain: RunnableWithMessageHistory,
    ):
        self.llm = llm
        self.rag_chain = rag_chain
        self.gostomysl = GostomyslWorkflow(llm)
        self.vygotsky = VygotskyEngine(llm)

    def _detect_route(self, message: str) -> str:
        lower = message.lower()
        gost_keywords = [
            "гост", "список литературы", "библиография", "arxiv",
            "научн", "статьи", "литератур",
        ]
        vyg_keywords = [
            "граф знаний", "путь обучения", "что изучить",
            "вакансия", "навыки", "learning path",
        ]
        for kw in gost_keywords:
            if kw in lower:
                return "gostomysl"
        for kw in vyg_keywords:
            if kw in lower:
                return "vygotsky"
        return "chat"

    def _is_dorm_question(self, message: str) -> bool:
        lower = message.lower()
        return any(kw in lower for kw in DORM_KEYWORDS)

    async def route(
        self,
        message: str,
        session_id: str = "default",
        progress_cb: Any = None,
    ) -> Dict[str, Any]:
        route = self._detect_route(message)

        if route == "gostomysl":
            result = await self.gostomysl.run(message, progress_cb=progress_cb)
            answer = (
                "📚 **Гостомысл нашёл статьи!**\n\n"
                + (result.get("final_document") or "Не удалось сформировать документ.")
            )
            return {"route": "gostomysl", "answer": answer, "data": result}

        if route == "vygotsky":
            parts = message.split("|")
            target = parts[0].strip()
            user_desc = parts[1].strip() if len(parts) > 1 else "студент ИТМО, 2 курс бакалавриата"
            result = await self.vygotsky.full_analysis(target, user_desc)
            path_lines = []
            for step in result.get("learning_path", []):
                path_lines.append(
                    f"• **{step.get('label', step.get('id', '?'))}** — {step.get('reason', '')}"
                )
            answer = (
                "🧠 **Выготский построил путь обучения!**\n\n"
                + ("Что нужно изучить:\n" + "\n".join(path_lines) if path_lines else "Не удалось построить путь.")
            )
            return {"route": "vygotsky", "answer": answer, "data": result}

        dorm_context = ""
        if self._is_dorm_question(message):
            dorm_data = await fetch_dorm_summary()
            if dorm_data:
                dorm_context = format_dorm_context(dorm_data)

        question = message
        if dorm_context:
            question = f"{message}\n\n[Живые данные из общаги]:\n{dorm_context}"

        result = await self.rag_chain.ainvoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}},
        )
        return {"route": "chat", "answer": result["answer"], "data": None}
