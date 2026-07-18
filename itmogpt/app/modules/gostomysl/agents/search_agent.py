import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

import arxiv

from app.config import cfg


class SearchAgent:
    def __init__(self, max_results: int = 0):
        self.max_results = max_results or cfg.ARXIV_MAX_RESULTS
        self.executor = ThreadPoolExecutor(max_workers=5)

    def search_arxiv(self, query: str, max_results: int = 30) -> List[Dict]:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers = []
        for paper in search.results():
            papers.append({
                "id": paper.entry_id,
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "summary": paper.summary,
                "published": paper.published,
                "updated": paper.updated,
                "categories": paper.categories,
                "pdf_url": paper.pdf_url,
                "doi": paper.doi,
                "journal_ref": paper.journal_ref,
            })
        return papers

    async def search_multiple(self, queries: List[str]) -> List[Dict]:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, self.search_arxiv, q, 30)
            for q in queries
        ]
        results = await asyncio.gather(*tasks)
        seen = {}
        for papers in results:
            for p in papers:
                if p["id"] not in seen:
                    seen[p["id"]] = p
        return list(seen.values())
