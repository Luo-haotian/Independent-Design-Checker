# Configuration for IDC
import os
import sys
from pathlib import Path

# Get the base directory (works both for script and frozen executable)
def get_base_dir():
    """Get the base directory of the application"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use exe location
        return Path(sys.executable).parent
    else:
        # Running as script - use script location
        return Path(__file__).parent

# Load .env from multiple possible locations
def load_env():
    """Load .env file from various locations"""
    base_dir = get_base_dir()
    
    # Possible locations to search for .env (in order of priority)
    search_paths = [
        base_dir / '.env',                          # Same dir as exe/script
        Path.cwd() / '.env',                        # Current working directory
    ]
    
    # Also check environment variable
    env_file_path = os.environ.get('IDC_ENV_FILE')
    if env_file_path:
        search_paths.insert(0, Path(env_file_path))
    
    # Try to load from first existing file
    for env_path in search_paths:
        if env_path.exists():
            # Only print in non-frozen mode to avoid console window
            if not getattr(sys, 'frozen', False):
                print(f"Loading config from: {env_path}")
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Only set if not already in environment
                            if key not in os.environ:
                                os.environ[key] = value
                return True
            except Exception as e:
                if not getattr(sys, 'frozen', False):
                    print(f"Warning: Error reading {env_path}: {e}")
                continue
    
    # No .env file found - that's ok, maybe env vars are set directly
    return False

# Load environment variables
load_env()

# API Configuration (支持 Grok 或 KIMI)
API_PROVIDER = os.environ.get('API_PROVIDER', 'grok').lower()  # 'grok' 或 'kimi'

if API_PROVIDER == 'grok':
    API_KEY = os.environ.get('GROK_API_KEY')
    API_URL = os.environ.get('GROK_API_URL', 'https://api.x.ai/v1/chat/completions')
    MODEL_NAME = os.environ.get('MODEL_NAME', 'grok-2-1212')
else:
    API_KEY = os.environ.get('KIMI_API_KEY')
    API_URL = os.environ.get('KIMI_API_URL', 'https://api.moonshot.cn/v1/chat/completions')
    MODEL_NAME = os.environ.get('MODEL_NAME', 'moonshot-v1-32k')

# Check API key only when actually using the module (not at import time)
def check_api_key():
    """Check if API key is configured"""
    if not API_KEY:
        error_msg = (
            f"API key not set! Provider: {API_PROVIDER}\n\n"
            f"Please do one of the following:\n"
            f"1. Create a .env file in the same folder as the executable with:\n"
            f"   {('GROK_API_KEY' if API_PROVIDER == 'grok' else 'KIMI_API_KEY')}=your_api_key_here\n"
            f"2. Set environment variable:\n"
            f"   {('GROK_API_KEY' if API_PROVIDER == 'grok' else 'KIMI_API_KEY')}=your_api_key\n"
            f"3. Use IDC_ENV_FILE environment variable to specify .env location\n\n"
            f"Current exe location: {get_base_dir()}"
        )
        raise ValueError(error_msg)
    return True

# Model configs
MODEL_CONFIGS = {
    # Grok models (latest)
    "grok-4-1-fast-non-reasoning": {"max_context": 131072, "max_output": 4096},
    "grok-4": {"max_context": 131072, "max_output": 4096},
    "grok-4-0709": {"max_context": 131072, "max_output": 4096},
    "grok-3": {"max_context": 131072, "max_output": 4096},
    "grok-3-mini": {"max_context": 131072, "max_output": 4096},
    # KIMI models
    "moonshot-v1-8k": {"max_context": 8000, "max_output": 4000},
    "moonshot-v1-32k": {"max_context": 32000, "max_output": 4000},
    "moonshot-v1-128k": {"max_context": 128000, "max_output": 4000},
}

MAX_TOKENS = 4000
TEMPERATURE = 0.2
TOKEN_MULTIPLIER = 1
