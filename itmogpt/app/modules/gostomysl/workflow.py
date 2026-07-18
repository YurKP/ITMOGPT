from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from app.modules.gostomysl.agents.gost_formatter import GOSTFormatter
from app.modules.gostomysl.agents.query_agent import QueryAgent
from app.modules.gostomysl.agents.ranking_agent import RankingAgent
from app.modules.gostomysl.agents.search_agent import SearchAgent
from app.modules.gostomysl.agents.summary_agent import SummaryAgent


class GostomyslWorkflow:
    def __init__(self, llm: BaseChatModel):
        self.query_agent = QueryAgent(llm)
        self.search_agent = SearchAgent()
        self.ranking_agent = RankingAgent(llm)
        self.summary_agent = SummaryAgent(llm)
        self.formatter = GOSTFormatter()

    async def run(self, user_query: str, progress_cb: Any = None) -> Dict:
        state: Dict[str, Any] = {"user_query": user_query, "status": "started"}

        if progress_cb:
            await progress_cb("query_processing", "Processing query...")

        enhanced = self.query_agent.process_query(user_query)
        state["enhanced_queries"] = enhanced

        if progress_cb:
            await progress_cb("query_processing", "Complete", enhanced)

        if progress_cb:
            await progress_cb("searching", "Searching ArXiv...")

        papers = await self.search_agent.search_multiple(enhanced["arxiv_queries"])
        state["raw_papers"] = papers

        if progress_cb:
            await progress_cb("searching", "Complete", {"count": len(papers)})

        if progress_cb:
            await progress_cb("ranking", "Ranking papers...")

        ranked = await self.ranking_agent.multi_stage_ranking(papers, user_query)
        state["ranked_papers"] = ranked

        if progress_cb:
            await progress_cb("ranking", "Complete", {"top": len(ranked)})

        if progress_cb:
            await progress_cb("summarizing", "Creating summaries...")

        summarized = await self.summary_agent.summarize_papers(ranked)
        state["summarized_papers"] = summarized

        if progress_cb:
            await progress_cb("summarizing", "Complete")

        if progress_cb:
            await progress_cb("formatting", "Formatting document...")

        document = self.formatter.format_full_document(summarized)
        state["final_document"] = document

        if progress_cb:
            await progress_cb("formatting", "Complete")

        state["status"] = "complete"
        return state
