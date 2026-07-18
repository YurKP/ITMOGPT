from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, List, Optional

import aiofiles
import aiohttp
import fitz
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger("gostomysl.summary")

SUMMARY_PROMPT = (
    "Создай краткую суммаризацию научной статьи на русском языке.\n\n"
    "Название: {title}\nАвторы: {authors}\nТекст статьи:\n{text}\n\n"
    "Суммаризация должна включать:\n"
    "1. Основную проблему/задачу\n"
    "2. Предложенный метод/подход\n"
    "3. Основные результаты\n"
    "4. Практическая значимость\n\n"
    "Ответ на русском языке, максимум 200 слов."
)


class SummaryAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    @staticmethod
    async def extract_full_text(paper_url: str) -> str | None:
        try:
            if "/abs/" in paper_url:
                pdf_url = paper_url.replace("/abs/", "/pdf/") + ".pdf"
            else:
                pdf_url = paper_url

            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as resp:
                    resp.raise_for_status()
                    content = await resp.read()

            tmp_path = f"/tmp/{uuid.uuid4()}.pdf"
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(content)

            try:
                loop = asyncio.get_running_loop()
                doc = await loop.run_in_executor(None, fitz.open, tmp_path)
                text = ""
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
            finally:
                import os
                os.unlink(tmp_path)

            return text.strip() if text.strip() else None
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return None

    async def summarize_paper(self, paper: Dict) -> Dict:
        full_text = await self.extract_full_text(paper["id"])
        text_for_prompt = full_text[:4000] if full_text else paper["summary"]

        prompt = SUMMARY_PROMPT.format(
            title=paper["title"],
            authors=", ".join(paper["authors"][:3]),
            text=text_for_prompt,
        )
        resp = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return {**paper, "ru_summary": resp.content}

    async def summarize_papers(self, papers: List[Dict]) -> List[Dict]:
        tasks = [self.summarize_paper(p) for p in papers]
        return await asyncio.gather(*tasks)
