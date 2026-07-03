from langchain.chat_models import init_chat_model

from app.core.config import configure_runtime_env, get_settings


def init_project_chat_model(model_name: str):
    settings = get_settings()
    configure_runtime_env()

    provider = settings.llm_provider
    model_id = f"{provider}:{model_name}"
    model_kwargs: dict[str, str] = {}

    if provider == "azure_openai":
        if not settings.azure_openai_deployment_name:
            raise ValueError(
                "LLM_PROVIDER=azure_openai requiere AZURE_OPENAI_DEPLOYMENT_NAME."
            )
        model_kwargs["azure_deployment"] = settings.azure_openai_deployment_name
        if settings.azure_openai_endpoint:
            model_kwargs["azure_endpoint"] = settings.azure_openai_endpoint
        if settings.azure_openai_api_version:
            model_kwargs["api_version"] = settings.azure_openai_api_version
        if settings.azure_openai_api_key:
            model_kwargs["api_key"] = settings.azure_openai_api_key

    return init_chat_model(model_id, **model_kwargs)
