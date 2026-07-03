import logging
from time import perf_counter

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents.specialists import knowledge_base_agent, pdf_agent, web_agent
from app.core.config import get_settings
from app.core.llm_factory import init_project_chat_model
from app.graph.router import classify_query
from app.graph.state import AgentInput, RouterState

settings = get_settings()
_synthesizer_model = init_project_chat_model(settings.openai_model)
logger = logging.getLogger("rag_agentico.graph.workflow")

_AGENTS = {
    "web": web_agent,
    "knowledge_base": knowledge_base_agent,
    "pdf": pdf_agent,
}


def _extract_answer(agent_response: dict) -> str:
    messages = agent_response.get("messages", [])
    if not messages:
        return ""

    content = messages[-1].content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                blocks.append(str(part["text"]))
        return "\n".join(blocks)
    return str(content)


def _run_agent(source: str):
    agent = _AGENTS[source]

    def _node(state: AgentInput) -> dict:
        trace_id = state.get("trace_id", "no-trace")
        logger.info("[%s] ▶ %s:start", trace_id, source)
        started = perf_counter()
        query = state["query"]
        if state.get("conversation_context"):
            query = (
                f"Contexto conversacional reciente:\n{state['conversation_context']}\n\n"
                f"Tarea actual:\n{state['query']}"
            )
        result = agent.invoke({"messages": [{"role": "user", "content": query}]})
        elapsed_s = perf_counter() - started
        logger.info("[%s] ✅ %s:end elapsed_s=%.2f", trace_id, source, elapsed_s)
        return {"results": [{"source": source, "result": _extract_answer(result)}]}

    return _node


def _route_to_agents(state: RouterState) -> list[Send]:
    trace_id = state.get("trace_id", "no-trace")
    logger.info(
        "[%s] ↪ route:selected=%s",
        trace_id,
        [route["source"] for route in state["classifications"]],
    )
    return [
        Send(
            route["source"],
            {
                "trace_id": state.get("trace_id", "no-trace"),
                "query": route["query"],
                "conversation_context": state.get("conversation_context", ""),
            },
        )
        for route in state["classifications"]
    ]


def _synthesize_results(state: RouterState) -> dict:
    trace_id = state.get("trace_id", "no-trace")
    logger.info("[%s] ▶ synthesize:start", trace_id)
    started = perf_counter()
    if not state.get("results"):
        elapsed_s = perf_counter() - started
        logger.info("[%s] ⚠ synthesize:end elapsed_s=%.2f no_results=true", trace_id, elapsed_s)
        return {"final_answer": "No se obtuvieron resultados de los agentes."}

    formatted_results = "\n\n".join(
        f"[{item['source']}]\n{item['result']}" for item in state["results"]
    )
    response = _synthesizer_model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "Sintetiza la respuesta final en español, de forma clara y útil. "
                    "Si hay salida de PDF, incluye explícitamente la ruta. "
                    "Si faltan datos, indícalo sin inventar."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Contexto:\n{state.get('conversation_context', '(sin contexto)')}\n\n"
                    f"Pregunta original:\n{state['query']}\n\n"
                    f"Resultados de agentes:\n{formatted_results}"
                ),
            },
        ]
    )
    elapsed_s = perf_counter() - started
    logger.info(
        "[%s] ✅ synthesize:end elapsed_s=%.2f results=%d",
        trace_id,
        elapsed_s,
        len(state["results"]),
    )
    return {"final_answer": str(response.content)}


def build_workflow():
    graph = StateGraph(RouterState)
    graph.add_node("classify", classify_query)
    graph.add_node("web", _run_agent("web"))
    graph.add_node("knowledge_base", _run_agent("knowledge_base"))
    graph.add_node("pdf", _run_agent("pdf"))
    graph.add_node("synthesize", _synthesize_results)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        _route_to_agents,
        ["web", "knowledge_base", "pdf"],
    )
    graph.add_edge("web", "synthesize")
    graph.add_edge("knowledge_base", "synthesize")
    graph.add_edge("pdf", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


workflow = build_workflow()
