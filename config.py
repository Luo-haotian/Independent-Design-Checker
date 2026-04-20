"""Runtime configuration for IDC."""

import os
import sys
from pathlib import Path


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

API_PROVIDER = "grok"
API_KEY = os.environ.get("GROK_API_KEY")
API_URL = os.environ.get("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
MODEL_NAME = os.environ.get("MODEL_NAME", "grok-4-1-fast-non-reasoning")

MODEL_CONFIGS = {
    "grok-4-1-fast-non-reasoning": {"max_context": 131072, "max_output": 4096},
    "grok-4": {"max_context": 131072, "max_output": 4096},
    "grok-4-0709": {"max_context": 131072, "max_output": 4096},
    "grok-3": {"max_context": 131072, "max_output": 4096},
    "grok-3-mini": {"max_context": 131072, "max_output": 4096},
}

MAX_TOKENS = 4096
TEMPERATURE = 0.2


def check_api_key():
    """Ensure a Grok API key is available before runtime."""
    if API_KEY:
        return True

    raise ValueError(
        "GROK_API_KEY is not set.\n\n"
        "Add a .env file next to the script or executable with:\n"
        "  GROK_API_KEY=your_api_key_here\n\n"
        "Optional keys:\n"
        "  GROK_API_URL=https://api.x.ai/v1/chat/completions\n"
        "  MODEL_NAME=grok-4-1-fast-non-reasoning\n"
        "  IDC_ENV_FILE=C:\\path\\to\\.env\n\n"
        f"Current runtime directory: {get_base_dir()}"
    )
