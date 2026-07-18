import json
from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

GRAPH_GEN_SYSTEM = (
    "Ты — эксперт по построению графов знаний для образования. "
    "По заданной теме (вакансия, образовательная программа или область знаний) "
    "построй граф знаний в виде списка вершин (топиков) и направленных рёбер (зависимостей). "
    "Каждое ребро означает: чтобы изучить target, нужно сначала знать source.\n\n"
    "Ответ строго в JSON:\n"
    '{\n'
    '  "nodes": [{"id": "topic_1", "label": "Название темы", "level": "beginner|intermediate|advanced"}],\n'
    '  "edges": [{"source": "topic_1", "target": "topic_2"}]\n'
    '}'
)


class VygotskyEngine:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def generate_knowledge_graph(self, description: str) -> Dict[str, Any]:
        resp = await self.llm.ainvoke([
            SystemMessage(content=GRAPH_GEN_SYSTEM),
            HumanMessage(content=f"Построй граф знаний для: {description}"),
        ])
        text = resp.content.strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {"nodes": [], "edges": [], "raw": resp.content}

    async def assess_user_knowledge(
        self, graph: Dict[str, Any], user_description: str
    ) -> List[str]:
        graph_str = json.dumps(graph, ensure_ascii=False, indent=2)
        system = (
            "Ты — эксперт по оценке знаний. По описанию навыков пользователя "
            "(его образовательная программа, курс, перечисленные навыки или результаты теста) "
            "определи, какие топики из предоставленного графа знаний пользователь уже знает.\n\n"
            "Граф знаний:\n" + graph_str + "\n\n"
            'Ответ строго в JSON:\n'
            '{"known_topics": ["topic_id_1", "topic_id_2"]}'
        )
        resp = await self.llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Описание пользователя: {user_description}"),
        ])
        text = resp.content.strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        try:
            data = json.loads(text)
            return data.get("known_topics", [])
        except (json.JSONDecodeError, ValueError):
            return []

    async def compute_learning_path(
        self, graph: Dict[str, Any], known_topics: List[str]
    ) -> List[Dict[str, str]]:
        graph_str = json.dumps(graph, ensure_ascii=False, indent=2)
        known_str = json.dumps(known_topics, ensure_ascii=False)
        system = (
            "Ты — эксперт по построению учебных планов. "
            "Дан граф знаний и список уже известных пользователю топиков. "
            "Определи последовательность топиков, которые нужно изучить, "
            "учитывая зависимости (топологическая сортировка). "
            "Исключи уже известные топики.\n\n"
            "Граф:\n" + graph_str + "\n\n"
            "Известные топики: " + known_str + "\n\n"
            'Ответ строго в JSON:\n'
            '{"learning_path": [{"id": "topic_id", "label": "Название", "reason": "Почему нужно изучить"}]}'
        )
        resp = await self.llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content="Построй путь обучения."),
        ])
        text = resp.content.strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        try:
            data = json.loads(text)
            return data.get("learning_path", [])
        except (json.JSONDecodeError, ValueError):
            return []

    async def full_analysis(
        self,
        target_description: str,
        user_description: str,
    ) -> Dict[str, Any]:
        graph = await self.generate_knowledge_graph(target_description)
        known = await self.assess_user_knowledge(graph, user_description)
        path = await self.compute_learning_path(graph, known)
        return {
            "knowledge_graph": graph,
            "known_topics": known,
            "learning_path": path,
        }
