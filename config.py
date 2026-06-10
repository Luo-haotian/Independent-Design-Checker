"""Runtime configuration for IDC."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import requests


def get_base_dir():
    """Return the directory that contains the script or executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def load_env():
    """Load environment variables from the first available .env file."""
    base_dir = get_base_dir()
    search_paths = [
        Path(os.environ["IDC_ENV_FILE"]) if os.environ.get("IDC_ENV_FILE") else None,
        base_dir / ".env",
        Path.cwd() / ".env",
    ]

    for env_path in search_paths:
        if env_path is None or not env_path.exists():
            continue
        try:
            with open(env_path, "r", encoding="utf-8") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
            return True
        except OSError:
            continue
    return False


load_env()


@dataclass(frozen=True)
class LLMConfig:
    """Resolved chat-completions provider settings."""

    provider: str
    api_key: str | None
    api_url: str
    model: str
    max_context: int
    max_output: int
    temperature: float


PROVIDER_LABELS = {
    "grok": "Grok",
    "kimi": "Kimi",
}

DEFAULT_PROVIDER = os.environ.get("IDC_API_PROVIDER") or os.environ.get("API_PROVIDER") or "grok"
API_PROVIDER = DEFAULT_PROVIDER.strip().lower()
if API_PROVIDER not in PROVIDER_LABELS:
    API_PROVIDER = "grok"

GROK_MODEL_NAME = os.environ.get("GROK_MODEL_NAME") or os.environ.get("MODEL_NAME") or "grok-4-1-fast-non-reasoning"
KIMI_MODEL_NAME = (
    os.environ.get("KIMI_MODEL_NAME")
    or os.environ.get("MOONSHOT_MODEL_NAME")
    or os.environ.get("KIMI_CODE_MODEL")
    or "kimi-k2.5"
)
MODEL_NAME = GROK_MODEL_NAME if API_PROVIDER == "grok" else KIMI_MODEL_NAME

GROK_MODEL_CONFIGS = {
    "grok-4-1-fast-non-reasoning": {"max_context": 131072, "max_output": 4096},
    "grok-4": {"max_context": 131072, "max_output": 4096},
    "grok-4-0709": {"max_context": 131072, "max_output": 4096},
    "grok-3": {"max_context": 131072, "max_output": 4096},
    "grok-3-mini": {"max_context": 131072, "max_output": 4096},
}

KIMI_MODEL_CONFIGS = {
    "kimi-k2.6": {"max_context": 262144, "max_output": 8192},
    "kimi-k2.5": {"max_context": 262144, "max_output": 8192},
    "kimi-k2-0905-preview": {"max_context": 262144, "max_output": 8192},
    "kimi-k2-turbo-preview": {"max_context": 262144, "max_output": 8192},
    "moonshot-v1-8k": {"max_context": 8192, "max_output": 2048},
    "moonshot-v1-32k": {"max_context": 32768, "max_output": 4096},
    "moonshot-v1-128k": {"max_context": 131072, "max_output": 8192},
}

MODEL_CONFIGS = {**GROK_MODEL_CONFIGS, **KIMI_MODEL_CONFIGS}

MAX_TOKENS = 4096
TEMPERATURE = float(os.environ.get("IDC_TEMPERATURE", "0.2"))


def _chat_url(value: str, default_url: str) -> str:
    """Accept either a chat-completions URL or an OpenAI-compatible base URL."""
    url = (value or default_url).strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return url


def available_providers() -> list[str]:
    """Return providers supported by this runtime."""
    return list(PROVIDER_LABELS.keys())


def get_provider_label(provider: str | None = None) -> str:
    """Return a user-facing provider name."""
    resolved = (provider or API_PROVIDER).strip().lower()
    return PROVIDER_LABELS.get(resolved, resolved.upper())


def get_model_configs(provider: str | None = None) -> dict[str, dict[str, int]]:
    """Return model configs for one provider, or all configs when provider is omitted."""
    if provider == "grok":
        return GROK_MODEL_CONFIGS
    if provider == "kimi":
        return KIMI_MODEL_CONFIGS
    return MODEL_CONFIGS


def get_default_model(provider: str | None = None) -> str:
    """Return the configured default model for a provider."""
    resolved = (provider or API_PROVIDER).strip().lower()
    if resolved == "kimi":
        return KIMI_MODEL_NAME
    return GROK_MODEL_NAME


def get_llm_config(provider: str | None = None, model_name: str | None = None) -> LLMConfig:
    """Resolve provider settings while keeping Grok as the default."""
    resolved = (provider or API_PROVIDER).strip().lower()
    if resolved not in PROVIDER_LABELS:
        raise ValueError(f"Unsupported API provider: {provider}")

    if resolved == "kimi":
        api_key = os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")
        api_url = _chat_url(
            os.environ.get("KIMI_API_URL") or os.environ.get("MOONSHOT_API_URL") or "",
            "https://api.moonshot.cn/v1/chat/completions",
        )
        model = model_name or KIMI_MODEL_NAME
    else:
        api_key = os.environ.get("GROK_API_KEY")
        api_url = _chat_url(os.environ.get("GROK_API_URL", ""), "https://api.x.ai/v1/chat/completions")
        model = model_name or GROK_MODEL_NAME

    model_config = MODEL_CONFIGS.get(model, get_model_configs(resolved).get(get_default_model(resolved), {"max_context": 131072, "max_output": MAX_TOKENS}))
    return LLMConfig(
        provider=resolved,
        api_key=api_key,
        api_url=api_url,
        model=model,
        max_context=model_config["max_context"],
        max_output=model_config["max_output"],
        temperature=TEMPERATURE,
    )


def is_provider_configured(provider: str | None = None) -> bool:
    """Return whether the selected provider has an API key."""
    return bool(get_llm_config(provider).api_key)


def check_api_key(provider: str | None = None) -> bool:
    """Ensure the selected provider has an API key available before runtime."""
    config = get_llm_config(provider)
    if config.api_key:
        return True

    if config.provider == "kimi":
        key_hint = "KIMI_API_KEY=your_kimi_key_here  # or MOONSHOT_API_KEY=..."
        optional_hint = "  KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions\n  KIMI_MODEL_NAME=kimi-k2.5"
    else:
        key_hint = "GROK_API_KEY=your_grok_key_here"
        optional_hint = "  GROK_API_URL=https://api.x.ai/v1/chat/completions\n  GROK_MODEL_NAME=grok-4-1-fast-non-reasoning"

    raise ValueError(
        f"{get_provider_label(config.provider)} API key is not set.\n\n"
        "Add a .env file next to the script or executable with:\n"
        f"  IDC_API_PROVIDER={config.provider}\n"
        f"  {key_hint}\n\n"
        "Optional keys:\n"
        f"{optional_hint}\n"
        "  IDC_ENV_FILE=C:\\path\\to\\.env\n\n"
        f"Current runtime directory: {get_base_dir()}"
    )


def call_chat_completion(
    prompt: str,
    *,
    provider: str | None = None,
    model_name: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    timeout: int = 180,
) -> tuple[str, dict]:
    """Call the selected OpenAI-compatible chat completions API."""
    config = get_llm_config(provider, model_name)
    check_api_key(config.provider)
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens or config.max_output,
        "temperature": config.temperature if temperature is None else temperature,
    }
    headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
    response = requests.post(config.api_url, headers=headers, json=payload, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"{get_provider_label(config.provider)} API error {response.status_code}: {response.text[:240]}")
    result = response.json()
    return result["choices"][0]["message"]["content"], result


API_KEY = get_llm_config("grok").api_key
API_URL = get_llm_config("grok").api_url
