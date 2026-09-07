"""Assembles the Talkar GM system prompt from the instruction-stack documents."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Load order mirrors the stack's own layering (see repo README).
DOCUMENT_FILES = [
    "00-master-instruction-set.md",
    "01-narrative-interaction-model.md",
    "02-rpg-engine-v2.md",
    "03-sky-islands-reference-repository-v1.md",
    "04-sky-islands-simulation-layer-v1.md",
    "05-campaign-initialization-kit-v1.md",
    "06-relationship-emphasis.md",
]

HEADER = (
    "You are the Game Master for the Talkar Persistent Narrative RPG. "
    "The complete instruction stack follows as seven documents. Follow them "
    "faithfully; where they define precedence, honor it.\n"
)


def build_system_prompt() -> str:
    parts = [HEADER]
    for name in DOCUMENT_FILES:
        path = REPO_ROOT / name
        if not path.exists():
            raise FileNotFoundError(
                f"Instruction document missing: {path}. "
                "Run the app from a checkout of the full repository."
            )
        parts.append(f"\n===== BEGIN DOCUMENT: {name} =====\n")
        parts.append(path.read_text(encoding="utf-8"))
        parts.append(f"\n===== END DOCUMENT: {name} =====\n")
    return "".join(parts)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token). Used only for compaction
    thresholds and UI display, never for billing."""
    return len(text) // 4
