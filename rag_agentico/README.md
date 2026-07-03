# rag_agentico

Chat conversacional basado en **FastAPI + LangChain + LangGraph** con orquestación de agentes.

## Estructura

```text
app/
  api/
    router.py
    routes/chat.py
  agents/
    specialists.py
  core/
    config.py
  graph/
    router.py
    state.py
    workflow.py
  memory/
    conversation_store.py
  models/
    chat.py
  tools/
    search.py
  main.py
```

## Capacidades del chat

1. **Consulta web** (agente `web`)  
2. **Consulta base de conocimiento vía MCP** (agente `knowledge_base`)  
3. **Construcción de PDFs** (agente `pdf`)  
   - El PDF renderiza formato estilo Markdown (encabezados, listas, párrafos y bloques de código).

## ¿Por qué patrón Router?

Sí es apropiado para este caso porque:
- las intenciones son claras y discretas (web, KB, PDF),
- evita ejecutar agentes innecesarios,
- permite enrutar a **uno o varios agentes** en paralelo cuando la consulta lo requiere.

En este proyecto se usa un enfoque híbrido:
- **Router** para clasificar intenciones,
- **fan-out paralelo** para ejecutar múltiples agentes si aplica,
- **síntesis final** para responder de forma unificada.

## Variables de entorno

Usa `.env` (o `.env ` si heredaste ese nombre con espacio):

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ROUTER_MODEL=gpt-4o-mini
MCP_KB_ENDPOINT=http://127.0.0.1:9000/mcp/kb/query
MCP_KB_TOKEN=
PDF_OUTPUT_DIR=generated_pdfs
```

Para Azure Foundry / Azure OpenAI:

```env
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT_NAME=<deployment>
OPENAI_MODEL=gpt-4o-mini
ROUTER_MODEL=gpt-4o-mini
```

Para búsqueda web con Firecrawl:

```env
FIRECRAWL_API_KEY=<tu_api_key>
FIRECRAWL_API_BASE_URL=https://api.firecrawl.dev
```

## Ejecutar

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Debug en VS Code

Ya quedó lista la configuración en:

- `../.vscode/launch.json`
- `../.vscode/tasks.json`

Usa la configuración **FastAPI: Debug rag_agentico (uvicorn)** y presiona `F5`.

Nota: `launch.json` usa `${workspaceFolder}/rag_agentico/.env` como `envFile`.  
Si en tu máquina tienes el archivo heredado `.env ` (con espacio al final), renómbralo a `.env`.

## Endpoint principal

`POST /api/v1/chat`

Body:
```json
{
  "message": "Busca las últimas tendencias de RAG y crea un PDF resumen",
  "conversation_id": null,
  "include_pdf_base64": false
}
```

Si se genera PDF, la respuesta incluye `pdf_artifacts` con:
- `download_url` para descargar (`GET /api/v1/files/{filename}`)
- `content_base64` si envías `"include_pdf_base64": true`