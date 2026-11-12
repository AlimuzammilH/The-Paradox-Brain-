"""Settings. Everything can be overridden with environment variables or a .env file in the working folder."""
import os
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

HOME = Path(os.environ.get("PARADOX_HOME", Path.home() / ".paradox"))

# Any OpenAI-compatible endpoint: Ollama, LM Studio, llama.cpp server, vLLM, OpenAI itself.
LLM_URL = os.environ.get("PARADOX_LLM_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("PARADOX_LLM_MODEL", "qwen2.5:7b-instruct")
LLM_KEY = os.environ.get("PARADOX_LLM_KEY", "ollama")

# Judging models run on the CPU, so the graphics card stays free for the language model.
# The NLI model is the large DeBERTa trained on adversarial NLI (WANLI, ANLI): the small ones call any two
# sentences that mention opposite sides a contradiction, which makes them useless for judging a synthesis.
NLI_MODEL = os.environ.get("PARADOX_NLI_MODEL", "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli")
EMBED_MODEL = os.environ.get("PARADOX_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEVICE = os.environ.get("PARADOX_DEVICE", "cpu")

# How far the dialectic recurses, and how strong a contradiction must be to count as one (0-1).
MAX_DEPTH = int(os.environ.get("PARADOX_MAX_DEPTH", "2"))
TENSION_MIN = float(os.environ.get("PARADOX_TENSION_MIN", "0.45"))
PATTERNS_PER_ROUND = int(os.environ.get("PARADOX_PATTERNS", "2"))
