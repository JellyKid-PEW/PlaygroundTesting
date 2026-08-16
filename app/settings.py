"""App settings, stored in app/config.json (created on first save)."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULTS = {
    # "anthropic" or "openai_compatible"
    "backend": "anthropic",
    # Anthropic backend
    "anthropic_model": "claude-opus-5",
    "anthropic_api_key": "",  # empty -> SDK resolves from ANTHROPIC_API_KEY env
    # OpenAI-compatible local backend (gpt4all: http://localhost:4891/v1,
    # Ollama: http://localhost:11434/v1, LM Studio: http://localhost:1234/v1)
    "openai_base_url": "http://localhost:4891/v1",
    "openai_model": "",
    "openai_api_key": "not-needed",  # local servers usually ignore it
    # Generation
    "max_tokens": 16000,
    # Auto-compaction: when the working context (excluding the system prompt)
    # exceeds this rough token estimate, the app asks the GM for a /save and
    # restarts the context from it. Lower this a lot for small local models.
    "compact_after_tokens": 80000,
    # How many recent messages to carry verbatim through a compaction
    "compact_keep_messages": 6,
}


def load() -> dict:
    settings = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            settings.update(json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save(updates: dict) -> dict:
    settings = load()
    for key, value in updates.items():
        if key in DEFAULTS:
            settings[key] = value
    CONFIG_PATH.write_text(json.dumps(settings, indent=2))
    return settings


def public_view(settings: dict) -> dict:
    """Settings safe to send to the browser (API keys masked)."""
    view = dict(settings)
    for key in ("anthropic_api_key", "openai_api_key"):
        if view.get(key):
            view[key] = "*" * 8
    return view
