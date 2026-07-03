from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from app.core.config import get_settings

settings = get_settings()


@tool
def search_web(query: str) -> str:
    """Busca información pública en internet usando Firecrawl search API."""
    if not settings.firecrawl_api_key:
        raise ValueError("FIRECRAWL_API_KEY no está configurada en el entorno.")

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("La consulta web no puede estar vacía.")

    base_url = settings.firecrawl_api_base_url.rstrip("/")
    response = httpx.post(
        f"{base_url}/v2/search",
        headers={
            "Authorization": f"Bearer {settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "query": normalized_query,
            "sources": ["web"],
            "categories": [],
            "limit": 10,
            "scrapeOptions": {
                "onlyMainContent": True,
                "maxAge": 172800000,
                "parsers": ["pdf"],
                "formats": [],
            },
        },
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        return f"Firecrawl reportó un error: {payload.get('error')}"

    raw_data = payload.get("data", []) if isinstance(payload, dict) else []
    data: list[dict] = []
    if isinstance(raw_data, list):
        data = [item for item in raw_data if isinstance(item, dict)]
    elif isinstance(raw_data, dict):
        if isinstance(raw_data.get("web"), list):
            data = [item for item in raw_data["web"] if isinstance(item, dict)]
        elif isinstance(raw_data.get("results"), list):
            data = [item for item in raw_data["results"] if isinstance(item, dict)]

    if not data:
        return f"Búsqueda completada para '{normalized_query}', sin resultados."

    lines: list[str] = []
    for item in data[:10]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("sourceURL") or item.get("sourceUrl") or "")
        title = str(item.get("title") or "")
        snippet = (
            str(item.get("markdown") or "")
            or str(item.get("content") or "")
            or str(item.get("description") or "")
            or str(item.get("extract") or "")
        )
        snippet = snippet.strip().replace("\n", " ")
        if len(snippet) > 600:
            snippet = f"{snippet[:600]}..."

        header = f"- {title}" if title else "- Resultado"
        if url:
            header = f"{header}\n  URL: {url}"
        if snippet:
            header = f"{header}\n  Resumen: {snippet}"
        lines.append(header)

    if not lines:
        return f"Búsqueda completada para '{normalized_query}', sin contenido textual útil."
    return "\n\n".join(lines)


@tool
def search_knowledge_base_via_mcp(query: str) -> str:
    """Consulta la base de conocimiento interna a través de un endpoint MCP."""
    if not settings.mcp_kb_endpoint:
        raise ValueError("MCP_KB_ENDPOINT no está configurado en el entorno.")

    headers: dict[str, str] = {}
    if settings.mcp_kb_token:
        headers["Authorization"] = f"Bearer {settings.mcp_kb_token}"

    response = httpx.post(
        settings.mcp_kb_endpoint,
        json={"query": query},
        headers=headers,
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()

    answer = payload.get("result") or payload.get("answer") or payload.get("content")
    if answer:
        return str(answer)
    return str(payload)


class BuildPdfInput(BaseModel):
    content: str = Field(..., description="Contenido para el PDF")
    filename: str = Field(
        default="respuesta.pdf",
        description="Nombre de archivo de salida",
    )


def _build_markdown_flowables(content: str) -> list:
    styles = getSampleStyleSheet()
    heading1 = styles["Heading1"]
    heading2 = styles["Heading2"]
    heading3 = styles["Heading3"]
    body = styles["BodyText"]
    body.leading = 15
    body.spaceAfter = 8
    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=9,
        leading=12,
        leftIndent=12,
        rightIndent=12,
        backColor=colors.whitesmoke,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=10,
    )

    flowables: list = []
    paragraph_lines: list[str] = []
    bullet_items: list[tuple[str, str]] = []
    code_lines: list[str] = []
    in_code_block = False
    normalized_content = content.replace("\\n", "\n").replace("\\t", "\t")

    def render_inline_markdown(text: str) -> str:
        escaped = escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<i>\1</i>", escaped)
        escaped = re.sub(
            r"`([^`]+)`",
            r"<font name='Courier'>\1</font>",
            escaped,
        )
        escaped = re.sub(r"\[(.+?)\]\((.+?)\)", r"<u><font color='blue'>\1</font></u>", escaped)
        return escaped

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        text = "<br/>".join(render_inline_markdown(line) for line in paragraph_lines).strip()
        if text:
            flowables.append(Paragraph(text, body))
        paragraph_lines.clear()

    def flush_bullets() -> None:
        if not bullet_items:
            return
        for bullet_text, item in bullet_items:
            flowables.append(
                Paragraph(
                    render_inline_markdown(item),
                    body,
                    bulletText=bullet_text,
                )
            )
        flowables.append(Spacer(1, 6))
        bullet_items.clear()

    def flush_code_block() -> None:
        if not code_lines:
            return
        flowables.append(Preformatted("\n".join(code_lines), style=code_style))
        code_lines.clear()

    for raw_line in normalized_content.splitlines() or ["(sin contenido)"]:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_bullets()
            if in_code_block:
                flush_code_block()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            flush_bullets()
            flowables.append(Spacer(1, 4))
            continue

        if stripped.startswith("#"):
            flush_paragraph()
            flush_bullets()
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            title = stripped[level:].strip() or "(sin título)"
            style = heading1 if level == 1 else heading2 if level == 2 else heading3
            flowables.append(Paragraph(render_inline_markdown(title), style))
            continue

        pseudo_bullet_match = re.match(r"^#\s*bullet\s*[:\-]?\s*(.*)$", stripped, re.IGNORECASE)
        if pseudo_bullet_match:
            flush_paragraph()
            bullet_items.append(("-", pseudo_bullet_match.group(1).strip() or "item"))
            continue

        bullet_match = re.match(r"^([-*]|\d+[.)])\s+(.*)$", stripped)
        if bullet_match:
            flush_paragraph()
            marker = bullet_match.group(1)
            text = bullet_match.group(2).strip() or "item"
            bullet_text = "-" if marker in ("-", "*") else marker
            bullet_items.append((bullet_text, text))
            continue

        paragraph_lines.append(stripped)

    flush_paragraph()
    flush_bullets()
    if in_code_block:
        flush_code_block()

    if not flowables:
        flowables.append(Paragraph("(sin contenido)", body))

    return flowables


@tool(args_schema=BuildPdfInput)
def build_pdf(content: str, filename: str = "respuesta.pdf") -> str:
    """Genera un PDF local renderizando contenido estilo Markdown."""
    output_dir = Path(settings.pdf_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    final_path = output_dir / f"{uuid4().hex}_{safe_name}"
    document = SimpleDocTemplate(
        str(final_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )
    document.build(_build_markdown_flowables(content))
    return f"PDF generado en: {final_path}"
