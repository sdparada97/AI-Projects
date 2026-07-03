import base64
import logging
import re
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.graph.workflow import workflow
from app.memory.conversation_store import conversation_store
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("rag_agentico.api.chat")
_PDF_OUTPUT_DIR = Path(settings.pdf_output_dir).resolve()
_PDF_PATH_PATTERN = re.compile(
    r"(?:PDF generado en:|Puedes descargarlo aquí:|Ruta del PDF:)\s*(?P<path>\S+\.pdf)"
)


def _extract_pdf_artifacts(
    results: list[dict],
    include_base64: bool,
) -> list[dict]:
    artifacts: list[dict] = []

    for item in results:
        if item.get("source") != "pdf":
            continue
        raw_result = str(item.get("result", ""))
        matches = _PDF_PATH_PATTERN.findall(raw_result)
        for raw_path in matches:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            resolved = candidate.resolve()

            if (
                resolved.suffix.lower() != ".pdf"
                or not resolved.exists()
                or not resolved.is_relative_to(_PDF_OUTPUT_DIR)
            ):
                continue

            artifact: dict[str, str | None] = {
                "filename": resolved.name,
                "path": str(resolved),
                "download_url": f"/api/v1/files/{resolved.name}",
                "content_base64": None,
            }
            if include_base64:
                artifact["content_base64"] = base64.b64encode(
                    resolved.read_bytes()
                ).decode("utf-8")
            artifacts.append(artifact)

    return artifacts


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/files/{file_name}")
def download_pdf(file_name: str) -> FileResponse:
    safe_name = Path(file_name).name
    candidate = (_PDF_OUTPUT_DIR / safe_name).resolve()

    if not candidate.exists() or not candidate.is_file() or not candidate.is_relative_to(
        _PDF_OUTPUT_DIR
    ):
        raise HTTPException(status_code=404, detail="PDF no encontrado")

    return FileResponse(
        path=str(candidate),
        media_type="application/pdf",
        filename=safe_name,
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    started = perf_counter()
    trace_id = uuid4().hex[:8]
    logger.info("[%s] 🚀 flow:start conversation_id=%s", trace_id, payload.conversation_id)
    conversation_id = payload.conversation_id or uuid4().hex
    history = conversation_store.get(conversation_id)
    conversation_context = "\n".join(
        f"{turn['role']}: {turn['content']}" for turn in history
    )

    result = workflow.invoke(
        {
            "trace_id": trace_id,
            "query": payload.message,
            "conversation_context": conversation_context,
        }
    )
    final_answer = result.get("final_answer", "")
    results = result.get("results", [])
    pdf_artifacts = _extract_pdf_artifacts(
        results=results,
        include_base64=payload.include_pdf_base64,
    )

    conversation_store.append_turn(conversation_id, "user", payload.message)
    conversation_store.append_turn(conversation_id, "assistant", final_answer)

    elapsed_s = perf_counter() - started
    logger.info(
        "[%s] 🏁 flow:end conversation_id=%s elapsed_s=%.2f routes=%s results=%d",
        trace_id,
        conversation_id,
        elapsed_s,
        [item.get("source") for item in result.get("classifications", [])],
        len(results),
    )

    return ChatResponse(
        conversation_id=conversation_id,
        query=result["query"],
        classifications=result.get("classifications", []),
        results=results,
        pdf_artifacts=pdf_artifacts,
        final_answer=final_answer,
    )
