"""Campaign persistence.

Each campaign lives in app/data/campaigns/<id>/ :
  meta.json       - name, timestamps
  transcript.jsonl - full append-only transcript (what the UI shows)
  context.json    - the working context actually sent to the model
                    (replaced wholesale when a compaction happens)
  saves/          - campaign saves captured from /save responses and compactions
"""

import json
import re
import time
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "campaigns"


def _dir(campaign_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", campaign_id):
        raise ValueError("bad campaign id")
    return DATA_DIR / campaign_id


def list_campaigns() -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for path in DATA_DIR.iterdir():
        meta_path = path / "meta.json"
        if meta_path.exists():
            try:
                out.append(json.loads(meta_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
    out.sort(key=lambda m: m.get("updated", 0), reverse=True)
    return out


def create(name: str) -> dict:
    campaign_id = uuid.uuid4().hex[:12]
    path = DATA_DIR / campaign_id
    (path / "saves").mkdir(parents=True)
    meta = {"id": campaign_id, "name": name, "created": time.time(), "updated": time.time()}
    (path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (path / "transcript.jsonl").write_text("", encoding="utf-8")
    (path / "context.json").write_text("[]", encoding="utf-8")
    return meta


def get_meta(campaign_id: str) -> dict:
    return json.loads((_dir(campaign_id) / "meta.json").read_text(encoding="utf-8"))


def touch(campaign_id: str) -> None:
    path = _dir(campaign_id) / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["updated"] = time.time()
    path.write_text(json.dumps(meta), encoding="utf-8")


def delete(campaign_id: str) -> None:
    import shutil

    shutil.rmtree(_dir(campaign_id))


def get_transcript(campaign_id: str) -> list[dict]:
    lines = (_dir(campaign_id) / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_transcript(campaign_id: str, entry: dict) -> None:
    entry = {**entry, "ts": time.time()}
    with open(_dir(campaign_id) / "transcript.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_context(campaign_id: str) -> list[dict]:
    return json.loads((_dir(campaign_id) / "context.json").read_text(encoding="utf-8"))


def set_context(campaign_id: str, messages: list[dict]) -> None:
    (_dir(campaign_id) / "context.json").write_text(json.dumps(messages), encoding="utf-8")


def append_context(campaign_id: str, role: str, content: str) -> list[dict]:
    ctx = get_context(campaign_id)
    ctx.append({"role": role, "content": content})
    set_context(campaign_id, ctx)
    return ctx


def write_save(campaign_id: str, text: str, kind: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{stamp}-{kind}.md"
    (_dir(campaign_id) / "saves" / filename).write_text(text, encoding="utf-8")
    return filename


def list_saves(campaign_id: str) -> list[str]:
    saves_dir = _dir(campaign_id) / "saves"
    return sorted((p.name for p in saves_dir.glob("*.md")), reverse=True)


def read_save(campaign_id: str, filename: str) -> str:
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("bad save name")
    return (_dir(campaign_id) / "saves" / filename).read_text(encoding="utf-8")
