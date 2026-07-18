from __future__ import annotations

import asyncio
import datetime
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from trafilatura import extract, fetch_url

from app.config import cfg
from app.llm.factory import get_chat_llm, get_embeddings
from app.modules.router import ITMORouter
from app.modules.vobshage_client import fetch_dorm_summary
from app.rag.chain import build_rag_chain
from app.rag.vectorstore import build_vectorstore

logger = logging.getLogger("itmogpt.web")

app = FastAPI(title="ИТМО GPT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
templates = Jinja2Templates(directory="app/web/templates")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "web_default"


class ChatResponse(BaseModel):
    answer: str
    route: str


class VygotskyRequest(BaseModel):
    content: str
    user_skills: str = ""


class UrlParseRequest(BaseModel):
    url: str


# --- Caches ---
_sidebar_cache: Dict[str, Any] = {}


def _cache_get(key: str, ttl: int) -> Optional[Any]:
    entry = _sidebar_cache.get(key)
    if entry and time.time() - entry["ts"] < ttl:
        return entry["data"]
    return None


def _cache_set(key: str, data: Any):
    _sidebar_cache[key] = {"data": data, "ts": time.time()}


@app.on_event("startup")
async def on_startup():
    llm = get_chat_llm()
    emb = get_embeddings()
    vectorstore = await build_vectorstore(emb)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    rag_chain = build_rag_chain(llm, retriever)
    router = ITMORouter(llm=llm, rag_chain=rag_chain)

    app.state.router = router
    app.state.llm = llm
    logger.info("ITMO GPT backend ready.")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat", response_model=ChatResponse)
async def chat_api(req: ChatRequest):
    router: ITMORouter = app.state.router
    result = await router.route(req.message, session_id=req.session_id)
    return ChatResponse(answer=result["answer"], route=result["route"])


@app.get("/api/chat")
async def chat_get(text: str, session_id: str = "web_default"):
    router: ITMORouter = app.state.router
    result = await router.route(text, session_id=session_id)
    return {"answer": result["answer"], "route": result["route"]}


# --- Vygotsky endpoints ---

@app.post("/api/vygotsky/analyze")
async def vygotsky_analyze(req: VygotskyRequest):
    router: ITMORouter = app.state.router
    try:
        graph = await router.vygotsky.generate_knowledge_graph(req.content)
        user_desc = req.user_skills if req.user_skills else "студент ИТМО, 2 курс бакалавриата"
        known = await router.vygotsky.assess_user_knowledge(graph, user_desc)
        path = await router.vygotsky.compute_learning_path(graph, known)
        return {
            "knowledge_graph": graph,
            "known_topics": known,
            "learning_path": path,
        }
    except Exception as e:
        logger.error(f"Vygotsky error: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/vygotsky/parse-url")
async def vygotsky_parse_url(req: UrlParseRequest):
    try:
        downloaded = fetch_url(req.url)
        text = extract(downloaded, include_comments=False, include_tables=True) if downloaded else ""
        return {"text": text or "", "url": req.url}
    except Exception as e:
        return {"text": "", "error": str(e)}


@app.post("/api/vygotsky/parse-pdf")
async def vygotsky_parse_pdf(file: UploadFile = File(...)):
    try:
        import fitz
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return {"text": text.strip()}
    except Exception as e:
        return {"text": "", "error": str(e)}


# --- Sidebar endpoints ---

@app.get("/api/sidebar/stats")
async def sidebar_stats():
    cached = _cache_get("dorm_stats", 300)
    if cached:
        return cached
    data = await fetch_dorm_summary()
    if data:
        _cache_set("dorm_stats", data)
        return data
    return {"error": "unavailable"}


@app.get("/api/sidebar/newspaper")
async def sidebar_newspaper():
    cached = _cache_get("newspaper_preview", 3600)
    if cached:
        return cached
    if not cfg.VOBSHAGE_API_URL:
        result = {"preview": "Подключи Вобщаге для свежих слухов! 🗞️"}
        _cache_set("newspaper_preview", result)
        return result
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{cfg.VOBSHAGE_API_URL.rstrip('/')}/api/newspaper?hours=24")
            resp.raise_for_status()
            data = resp.json()
            preview = (data.get("newspaper") or "")[:300]
            if len(data.get("newspaper", "")) > 300:
                preview += "..."
            result = {"preview": preview}
    except Exception:
        result = {"preview": "Газета временно недоступна 📰"}
    _cache_set("newspaper_preview", result)
    return result


@app.get("/api/sidebar/fact")
async def sidebar_fact():
    cached = _cache_get("fact_of_day", 86400)
    if cached:
        return cached
    try:
        llm = app.state.llm
        resp = await llm.ainvoke([
            {"role": "user", "content":
             "Расскажи один интересный факт про Университет ИТМО в Санкт-Петербурге. "
             "Максимум 2 предложения. Факт должен быть необычным и малоизвестным."}
        ])
        fact = resp.content.strip()
    except Exception:
        fact = "ИТМО — единственный вуз в мире, чьи команды побеждали на ICPC 7 раз! 🏆"
    result = {"fact": fact}
    _cache_set("fact_of_day", result)
    return result


# --- Gostomysl WebSocket ---

def _json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@app.websocket("/ws/gostomysl")
async def gostomysl_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=120)
            query_data = json.loads(data)
            user_query = query_data["query"]

            async def progress_cb(stage, status, data=None):
                msg = {"stage": stage, "status": status}
                if data is not None:
                    msg["data"] = data
                await websocket.send_text(json.dumps(msg, default=_json_serial, ensure_ascii=False))

            router: ITMORouter = app.state.router
            result = await router.gostomysl.run(user_query, progress_cb=progress_cb)

            await websocket.send_text(json.dumps({
                "stage": "complete",
                "status": "Research complete",
                "data": {
                    "document": result.get("final_document"),
                    "papers_count": len(result.get("ranked_papers", [])),
                },
            }, default=_json_serial, ensure_ascii=False))

    except WebSocketDisconnect:
        logger.info("Gostomysl WebSocket closed.")
    except Exception as e:
        logger.error(f"Gostomysl WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"stage": "error", "status": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/health")
async def health():
    return {"status": "ok"}
