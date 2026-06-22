import pytest

from configs.settings import AppSettings
from core.llm.base import LLMConfigurationError, LLMResponseValidationError
from core.llm.factory import create_llm_client
from core.llm.local_client import LocalLLMClient
from core.llm.mock_client import MockLLMClient
from core.llm.openai_client import OpenAILLMClient
from core.llm.qwen_client import QwenLLMClient


def make_settings(**overrides: object) -> AppSettings:
    values = {"app_env": "test", "llm_provider": "mock"}
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


def test_factory_creates_mock_client() -> None:
    assert isinstance(create_llm_client(make_settings()), MockLLMClient)


def test_factory_creates_openai_client_without_network_call() -> None:
    settings = make_settings(llm_provider="openai", openai_api_key="test-key")
    assert isinstance(create_llm_client(settings), OpenAILLMClient)


def test_factory_creates_local_client_without_network_call() -> None:
    settings = make_settings(
        llm_provider="local",
        local_llm_base_url="http://localhost:11434/v1",
        local_llm_model="llama3.1",
    )
    assert isinstance(create_llm_client(settings), LocalLLMClient)


def test_factory_creates_qwen_client_without_network_call() -> None:
    settings = make_settings(
        llm_provider="dashscope",
        dashscope_api_key="test-key",
        dashscope_workspace_id="workspace-id",
    )
    assert settings.resolved_dashscope_base_url == (
        "https://workspace-id.ap-southeast-1.maas.aliyuncs.com/"
        "compatible-mode/v1"
    )
    assert isinstance(create_llm_client(settings), QwenLLMClient)


def test_dashscope_workspace_id_takes_precedence_over_legacy_base_url() -> None:
    settings = make_settings(
        dashscope_workspace_id="workspace-id",
        dashscope_base_url="https://legacy.example/v1/",
    )
    assert settings.resolved_dashscope_base_url == (
        "https://workspace-id.ap-southeast-1.maas.aliyuncs.com/"
        "compatible-mode/v1"
    )


def test_dashscope_base_url_remains_available_as_compatibility_fallback() -> None:
    settings = make_settings(
        dashscope_base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/"
    )
    assert settings.resolved_dashscope_base_url == (
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )


def test_factory_supports_legacy_qwen_provider_and_environment_names() -> None:
    settings = AppSettings(
        _env_file=None,
        app_env="test",
        llm_provider="qwen",
        QWEN_API_KEY="test-key",
        QWEN_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        QWEN_MODEL="qwen-plus",
    )
    assert settings.dashscope_api_key == "test-key"
    assert isinstance(create_llm_client(settings), QwenLLMClient)


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(LLMConfigurationError, match="Unsupported LLM_PROVIDER"):
        create_llm_client(make_settings(llm_provider="other"))


def test_factory_requires_openai_key() -> None:
    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        create_llm_client(make_settings(llm_provider="openai", openai_api_key=""))


def test_factory_requires_qwen_key() -> None:
    with pytest.raises(LLMConfigurationError, match="DASHSCOPE_API_KEY"):
        create_llm_client(
            make_settings(
                llm_provider="dashscope",
                dashscope_api_key="",
                dashscope_base_url="https://workspace.example/v1",
            )
        )


def test_factory_requires_qwen_workspace_or_base_url() -> None:
    with pytest.raises(
        LLMConfigurationError,
        match="DASHSCOPE_WORKSPACE_ID or DASHSCOPE_BASE_URL",
    ):
        create_llm_client(
            make_settings(
                llm_provider="dashscope",
                dashscope_api_key="test-key",
                dashscope_workspace_id="",
                dashscope_base_url="",
            )
        )


def test_factory_requires_qwen_model() -> None:
    with pytest.raises(LLMConfigurationError, match="DASHSCOPE_MODEL"):
        create_llm_client(
            make_settings(
                llm_provider="dashscope",
                dashscope_api_key="test-key",
                dashscope_workspace_id="workspace-id",
                dashscope_model="",
            )
        )


def test_factory_requires_local_configuration() -> None:
    with pytest.raises(LLMConfigurationError, match="LOCAL_LLM_BASE_URL"):
        create_llm_client(
            make_settings(llm_provider="local", local_llm_base_url="")
        )


def test_factory_requires_local_model() -> None:
    with pytest.raises(LLMConfigurationError, match="LOCAL_LLM_MODEL"):
        create_llm_client(make_settings(llm_provider="local", local_llm_model=""))


def test_invalid_llm_json_has_clear_error() -> None:
    from core.schemas.campaign import IdeationResult

    with pytest.raises(LLMResponseValidationError, match="invalid JSON"):
        MockLLMClient.validate_json_response("not-json", IdeationResult)
