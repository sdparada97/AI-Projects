from functools import lru_cache
import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["openai", "azure_openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env "), extra="ignore")

    llm_provider: Provider = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    router_model: str = "gpt-4o-mini"
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_deployment_name: str = ""
    firecrawl_api_key: str = ""
    firecrawl_api_base_url: str = "https://api.firecrawl.dev"
    mcp_kb_endpoint: str = ""
    mcp_kb_token: str = ""
    pdf_output_dir: str = "generated_pdfs"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_runtime_env() -> None:
    settings = get_settings()
    if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.azure_openai_api_key and not os.environ.get("AZURE_OPENAI_API_KEY"):
        os.environ["AZURE_OPENAI_API_KEY"] = settings.azure_openai_api_key
    if settings.azure_openai_endpoint and not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
    if settings.azure_openai_api_version and not os.environ.get("AZURE_OPENAI_API_VERSION"):
        os.environ["AZURE_OPENAI_API_VERSION"] = settings.azure_openai_api_version
