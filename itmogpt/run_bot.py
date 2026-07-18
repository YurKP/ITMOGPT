#!/usr/bin/env python3
import asyncio
import logging

from app.bot.telegram import ITMOBot
from app.config import cfg
from app.llm.factory import get_chat_llm, get_embeddings
from app.modules.router import ITMORouter
from app.rag.chain import build_rag_chain
from app.rag.vectorstore import build_vectorstore

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def init_router() -> ITMORouter:
    llm = get_chat_llm()
    emb = get_embeddings()
    vs = await build_vectorstore(emb)
    retriever = vs.as_retriever(search_kwargs={"k": 4})
    rag_chain = build_rag_chain(llm, retriever)
    return ITMORouter(llm=llm, rag_chain=rag_chain)


def main():
    if not cfg.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    router = asyncio.get_event_loop().run_until_complete(init_router())
    bot = ITMOBot(router)
    bot.run()


if __name__ == "__main__":
    main()
