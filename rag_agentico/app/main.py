import logging

from fastapi import FastAPI

from app.api.router import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
logging.getLogger("rag_agentico.tools.search").setLevel(logging.WARNING)

app = FastAPI(
    title="rag_agentico",
    version="0.1.0",
    description=(
        "Chat conversacional con FastAPI + LangChain + LangGraph, "
        "orquestado por patrón Router con agentes especializados"
    ),
)

app.include_router(api_router, prefix="/api/v1")
