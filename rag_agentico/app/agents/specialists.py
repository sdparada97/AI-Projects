from langchain.agents import create_agent

from app.core.config import get_settings
from app.core.llm_factory import init_project_chat_model
from app.tools import build_pdf, search_knowledge_base_via_mcp, search_web

settings = get_settings()
_model = init_project_chat_model(settings.openai_model)

web_agent = create_agent(
    model=_model,
    tools=[search_web],
    system_prompt=(
        "Eres un analista web. Usa la herramienta search_web para buscar "
        "información actualizada y cita de forma breve lo encontrado."
    ),
)

knowledge_base_agent = create_agent(
    model=_model,
    tools=[search_knowledge_base_via_mcp],
    system_prompt=(
        "Eres un analista de base de conocimiento. Usa exclusivamente "
        "search_knowledge_base_via_mcp para responder consultas internas."
    ),
)

pdf_agent = create_agent(
    model=_model,
    tools=[build_pdf],
    system_prompt=(
        "Eres un asistente de documentos. Si el usuario solicita un PDF, "
        "usa build_pdf con contenido claro y un nombre de archivo apropiado."
    ),
)
