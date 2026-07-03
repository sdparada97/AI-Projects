from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Consulta del usuario")
    conversation_id: str | None = Field(
        default=None,
        description="ID opcional para mantener contexto entre turnos",
    )
    include_pdf_base64: bool = Field(
        default=False,
        description="Si es true, incluye el contenido base64 de PDFs generados",
    )


class ClassificationView(BaseModel):
    source: str
    query: str


class AgentResultView(BaseModel):
    source: str
    result: str


class PdfArtifactView(BaseModel):
    filename: str
    path: str
    download_url: str
    content_base64: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    query: str
    classifications: list[ClassificationView]
    results: list[AgentResultView]
    pdf_artifacts: list[PdfArtifactView] = Field(default_factory=list)
    final_answer: str
