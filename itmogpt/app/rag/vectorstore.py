import os

import httpx
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from trafilatura import extract, fetch_url

from app.config import cfg

URLS_TO_PARSE = [
    "https://itmo.ru",
    "https://habr.com/ru/companies/spbifmo/news/742522/",
    "https://itmo.ru/ru/viewperson/1/vasilev_vladimir_nikolaevich.htm",
    "https://student.itmo.ru/ru/dormitory/",
    "https://student.itmo.ru/ru/booking/",
    "https://student.itmo.ru/ru/scholarship/",
    "https://lib.itmo.ru",
    "https://books.ifmo.ru",
    "https://mathdep.itmo.ru",
    "https://student.itmo.ru/ru/organization/",
    "https://student.itmo.ru/ru/kronbars/",
    "https://se.ifmo.ru/courses/programming",
    "https://abit.itmo.ru/program/master/ai_systems",
    "https://itmo.ru/ru/viewperson/971/kustarev_pavel_valerevich.htm",
    "https://itmo.ru/ru/viewperson/1654/isaev_ilya_vladimirovich.htm",
    "https://itmo.ru/ru/viewperson/2135/kugaevskih_aleksandr_vladimirovich.htm",
]

RAW_CONTENT_URLS = [
    "https://raw.githubusercontent.com/whytrall/is-faq/master/docs/study/grants.md",
    "https://raw.githubusercontent.com/whytrall/is-faq/master/docs/study/session.md",
    "https://raw.githubusercontent.com/whytrall/is-faq/master/docs/study/evaluation.md",
]


def _url_to_filename(url: str) -> str:
    return url.strip("/").replace("https://", "").replace("http://", "").replace("/", "_") + ".md"


def fetch_knowledge_base():
    os.makedirs(cfg.DATA_DIR, exist_ok=True)

    for url in URLS_TO_PARSE:
        dest = os.path.join(cfg.DATA_DIR, _url_to_filename(url))
        if os.path.exists(dest):
            continue
        try:
            content = extract(fetch_url(url), include_comments=True, include_tables=False)
            if content:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            print(f"[fetch] skip {url}: {e}")

    for url in RAW_CONTENT_URLS:
        dest = os.path.join(cfg.DATA_DIR, _url_to_filename(url))
        if os.path.exists(dest):
            continue
        try:
            content = httpx.get(url, timeout=30).text
            if content:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            print(f"[fetch] skip {url}: {e}")


async def build_vectorstore(emb: Embeddings) -> Chroma:
    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    os.makedirs(cfg.CHROMA_DIR, exist_ok=True)

    fetch_knowledge_base()

    try:
        vs = Chroma(
            collection_name="itmogpt_rag",
            embedding_function=emb,
            persist_directory=cfg.CHROMA_DIR,
        )
        if vs._collection.count() > 0:
            return vs
    except Exception:
        pass

    loader = DirectoryLoader(
        cfg.DATA_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        show_progress=True,
        loader_kwargs={"encoding": "utf-8"},
    )
    raw_docs = loader.load()
    if not raw_docs:
        print(f"[rag] {cfg.DATA_DIR} is empty. Place .md files for RAG there.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    docs = splitter.split_documents(raw_docs)

    vs = Chroma(
        collection_name="itmogpt_rag",
        embedding_function=emb,
        persist_directory=cfg.CHROMA_DIR,
    )
    if docs:
        await vs.aadd_documents(docs)
    return vs
