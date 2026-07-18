from typing import Dict, List

import numpy as np
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import cfg


class RankingAgent:
    def __init__(self, llm: BaseChatModel):
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.llm = llm

    def rank_bm25(self, papers: List[Dict], query: str, top_k: int = 50) -> List[Dict]:
        if not papers:
            return []
        docs = [f"{p['title']} {p['summary']}" for p in papers]
        tokenized = [d.lower().split() for d in docs]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query.lower().split())
        indices = np.argsort(scores)[::-1][:top_k]
        return [papers[i] for i in indices]

    def rank_embeddings(self, papers: List[Dict], query: str, top_k: int = 25) -> List[Dict]:
        if not papers:
            return []
        docs = [f"{p['title']} {p['summary'][:500]}" for p in papers]
        doc_embs = self.embedding_model.encode(docs)
        q_emb = self.embedding_model.encode([query])
        sims = cosine_similarity(q_emb, doc_embs)[0]
        indices = np.argsort(sims)[::-1][:top_k]
        return [papers[i] for i in indices]

    async def rank_with_llm(self, papers: List[Dict], query: str, top_k: int = 10) -> List[Dict]:
        if not papers or len(papers) <= top_k:
            return papers

        scored = []
        for paper in papers[:25]:
            prompt = (
                f"Оцени релевантность статьи запросу от 0 до 10.\n"
                f"Запрос: {query}\nНазвание: {paper['title']}\n"
                f"Аннотация: {paper['summary'][:500]}\n"
                f"Ответь только числом от 0 до 10."
            )
            try:
                resp = await self.llm.ainvoke([HumanMessage(content=prompt)])
                score = float(resp.content.strip())
            except (ValueError, Exception):
                score = 5.0
            entry = paper.copy()
            entry["relevance_score"] = score
            scored.append(entry)

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:top_k]

    async def multi_stage_ranking(self, papers: List[Dict], query: str) -> List[Dict]:
        stage1 = self.rank_bm25(papers, query, cfg.GOSTOMYSL_TOP_K_BM25)
        stage2 = self.rank_embeddings(stage1, query, cfg.GOSTOMYSL_TOP_K_EMBED)
        stage3 = await self.rank_with_llm(stage2, query, cfg.GOSTOMYSL_TOP_K_FINAL)
        return stage3
