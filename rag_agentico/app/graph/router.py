import logging
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.llm_factory import init_project_chat_model
from app.graph.state import Classification, RouterState

settings = get_settings()
_router_llm = init_project_chat_model(settings.router_model)
logger = logging.getLogger("rag_agentico.graph.router")


class RouteChoice(BaseModel):
    source: Literal["web", "knowledge_base", "pdf"]
    query: str = Field(
        description="Sub-pregunta optimizada para el agente seleccionado"
    )


class RouteSelection(BaseModel):
    routes: list[RouteChoice]


ROUTER_SYSTEM_PROMPT = """Eres un router de agentes.
Selecciona una o más rutas según la consulta:
- web: información pública y actualizada.
- knowledge_base: información interna que debe consultarse vía MCP.
- pdf: cuando el usuario pide explícitamente crear/generar/exportar un PDF.

Reglas:
1) Devuelve SOLO rutas relevantes.
2) Si el usuario combina objetivos, devuelve múltiples rutas.
3) Si hay duda, incluye web como ruta por defecto.
"""


def classify_query(state: RouterState) -> dict:
    trace_id = state.get("trace_id", "no-trace")
    logger.info("[%s] ▶ classify:start", trace_id)
    started = perf_counter()
    structured_llm = _router_llm.with_structured_output(RouteSelection)
    user_prompt = state["query"]
    if state.get("conversation_context"):
        user_prompt = (
            f"Contexto conversacional reciente:\n{state['conversation_context']}\n\n"
            f"Consulta actual:\n{state['query']}"
        )

    decision: RouteSelection = structured_llm.invoke(
        [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    classifications: list[Classification] = [
        {"source": route.source, "query": route.query} for route in (decision.routes or [])
    ]
    if not classifications:
        classifications = [{"source": "web", "query": state["query"]}]

    dedup: list[Classification] = []
    seen_sources: set[str] = set()
    for item in classifications:
        if item["source"] in seen_sources:
            continue
        dedup.append(item)
        seen_sources.add(item["source"])

    elapsed_s = perf_counter() - started
    logger.info(
        "[%s] ✅ classify:end elapsed_s=%.2f routes=%s",
        trace_id,
        elapsed_s,
        [item["source"] for item in dedup],
    )

    return {"classifications": dedup}
