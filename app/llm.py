"""LLM backends.

Two paths:
  - "anthropic": the official Anthropic SDK with streaming and prompt caching.
    The ~60k-token instruction stack is cached with cache_control so that after
    the first message of a session it bills at ~10% of input price.
  - "openai_compatible": any local server speaking the OpenAI chat-completions
    protocol (gpt4all, Ollama, LM Studio). Streamed over SSE via httpx.
"""

import json
from collections.abc import Iterator

import httpx


class BackendError(Exception):
    """User-presentable backend failure."""


def stream_reply(settings: dict, system_prompt: str, messages: list[dict]) -> Iterator[str]:
    if settings["backend"] == "anthropic":
        yield from _stream_anthropic(settings, system_prompt, messages)
    else:
        yield from _stream_openai_compatible(settings, system_prompt, messages)


def complete(settings: dict, system_prompt: str, messages: list[dict]) -> str:
    """Non-interactive full completion (used for compaction saves)."""
    return "".join(stream_reply(settings, system_prompt, messages))


# --- Anthropic -------------------------------------------------------------


def _stream_anthropic(settings: dict, system_prompt: str, messages: list[dict]) -> Iterator[str]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.get("anthropic_api_key") or None)

    # Prompt caching is a prefix match: one breakpoint after the (byte-stable)
    # instruction stack, one on the last message so each turn extends the
    # cached conversation prefix.
    system_blocks = [
        {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
    ]
    wire = [dict(m) for m in messages]
    if wire:
        last = wire[-1]
        last["content"] = [
            {
                "type": "text",
                "text": last["content"],
                "cache_control": {"type": "ephemeral"},
            }
        ]

    try:
        with client.messages.stream(
            model=settings["anthropic_model"],
            max_tokens=int(settings["max_tokens"]),
            system=system_blocks,
            messages=wire,
        ) as stream:
            for text in stream.text_stream:
                yield text
            final = stream.get_final_message()
        if final.stop_reason == "refusal":
            raise BackendError(
                "The model declined this request (stop_reason: refusal). "
                "Rephrase and try again."
            )
        if final.stop_reason == "max_tokens":
            yield "\n\n*(Response was cut off at the max_tokens limit — raise it in Settings and say \"continue\".)*"
    except anthropic.AuthenticationError as e:
        raise BackendError(
            "Anthropic authentication failed. Set your API key in Settings or "
            "export ANTHROPIC_API_KEY before launching."
        ) from e
    except anthropic.NotFoundError as e:
        raise BackendError(f"Unknown Anthropic model '{settings['anthropic_model']}'.") from e
    except anthropic.RateLimitError as e:
        raise BackendError("Anthropic rate limit hit — wait a moment and retry.") from e
    except anthropic.APIStatusError as e:
        raise BackendError(f"Anthropic API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise BackendError("Could not reach the Anthropic API (network error).") from e


# --- OpenAI-compatible local servers ---------------------------------------


def _stream_openai_compatible(
    settings: dict, system_prompt: str, messages: list[dict]
) -> Iterator[str]:
    base = settings["openai_base_url"].rstrip("/")
    url = f"{base}/chat/completions"
    payload = {
        "model": settings.get("openai_model") or "default",
        "stream": True,
        "max_tokens": int(settings["max_tokens"]),
        "messages": [{"role": "system", "content": system_prompt}, *messages],
    }
    headers = {"Content-Type": "application/json"}
    if settings.get("openai_api_key"):
        headers["Authorization"] = f"Bearer {settings['openai_api_key']}"

    try:
        with httpx.stream(
            "POST",
            url,
            json=payload,
            headers=headers,
            timeout=httpx.Timeout(600.0, connect=10.0),
        ) as response:
            if response.status_code != 200:
                response.read()
                raise BackendError(
                    f"Local server returned HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = delta.get("content")
                if text:
                    yield text
    except httpx.ConnectError as e:
        raise BackendError(
            f"Could not connect to the local model server at {base}. "
            "Is gpt4all/Ollama/LM Studio running with its API server enabled?"
        ) from e
    except httpx.TimeoutException as e:
        raise BackendError("The local model server timed out.") from e
