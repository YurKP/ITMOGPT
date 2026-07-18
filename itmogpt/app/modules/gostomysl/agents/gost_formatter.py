from datetime import datetime
from typing import Dict, List


class GOSTFormatter:
    @staticmethod
    def format_article(paper: Dict) -> str:
        authors = paper["authors"][:3]
        authors_str = f"{authors[0]} и др." if len(paper["authors"]) > 3 else ", ".join(authors)
        title = paper["title"].replace("\n", " ")
        year = paper["published"].year if paper.get("published") else datetime.now().year
        journal = paper.get("journal_ref") or "ArXiv preprint"
        url = f"URL: {paper['pdf_url']}" if paper.get("pdf_url") else ""
        doi = f"DOI: {paper['doi']}" if paper.get("doi") else ""

        citation = f"{authors_str} {title} // {journal}. — {year}."
        if doi:
            citation += f" — {doi}."
        if url:
            citation += f" — {url}"
        return citation

    @staticmethod
    def format_bibliography(papers: List[Dict]) -> str:
        lines = ["## Список литературы\n"]
        for i, p in enumerate(papers, 1):
            lines.append(f"{i}. {GOSTFormatter.format_article(p)}\n")
        return "\n".join(lines)

    @staticmethod
    def format_full_document(papers: List[Dict]) -> str:
        bib = GOSTFormatter.format_bibliography(papers)
        meta = (
            f"\n---\n"
            f"Дата создания: {datetime.now().strftime('%d.%m.%Y')}\n"
            f"Количество источников: {len(papers)}\n"
            f"---\n"
        )
        return meta + "\n" + bib
