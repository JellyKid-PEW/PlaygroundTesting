"""Talkar RPG — local web app server.

Run from the app/ directory:  python server.py
Then open http://localhost:8642
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import campaigns
import llm
import prompt
import settings as settings_store

app = FastAPI(title="Talkar RPG")

STATIC_DIR = Path(__file__).parent / "static"

COMPACT_INSTRUCTION = (
    "OUT OF CHARACTER — SYSTEM MAINTENANCE (do not narrate): produce a complete "
    "portable campaign save exactly as specified by the Persistent Narrative RPG "
    "Engine §51 (/save). Include everything another GM instance needs to continue "
    "seamlessly: campaign identity, current date and time, player character, "
    "location, resources and equipment, physical condition, skills and standing, "
    "relationships and behavioral permissions, player knowledge and suspicions, "
    "major NPC states, active world situations, recent consequences, important "
    "places, narrative memory, unresolved questions, scheduled or likely offscreen "
    "developments, relationship emphasis setting, and setting repository version. "
    "Output only the save."
)


class CreateCampaign(BaseModel):
    name: str


class UserMessage(BaseModel):
    content: str


# --- pages -----------------------------------------------------------------


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# --- settings ---------------------------------------------------------------


@app.get("/api/settings")
def get_settings():
    return settings_store.public_view(settings_store.load())


@app.put("/api/settings")
def put_settings(updates: dict):
    # Masked keys come back from the UI as "********" — don't overwrite with the mask.
    for key in ("anthropic_api_key", "openai_api_key"):
        if updates.get(key) == "*" * 8:
            updates.pop(key)
    return settings_store.public_view(settings_store.save(updates))


# --- campaigns ---------------------------------------------------------------


@app.get("/api/campaigns")
def list_campaigns():
    return campaigns.list_campaigns()


@app.post("/api/campaigns")
def create_campaign(body: CreateCampaign):
    name = body.name.strip() or "Untitled campaign"
    return campaigns.create(name)


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: str):
    try:
        meta = campaigns.get_meta(campaign_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "campaign not found")
    context = campaigns.get_context(campaign_id)
    context_tokens = sum(prompt.estimate_tokens(m["content"]) for m in context)
    return {
        "meta": meta,
        "transcript": campaigns.get_transcript(campaign_id),
        "context_tokens": context_tokens,
        "saves": campaigns.list_saves(campaign_id),
    }


@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str):
    try:
        campaigns.delete(campaign_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "campaign not found")
    return {"ok": True}


@app.get("/api/campaigns/{campaign_id}/saves/{filename}")
def get_save(campaign_id: str, filename: str):
    try:
        return {"filename": filename, "text": campaigns.read_save(campaign_id, filename)}
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "save not found")


# --- compaction --------------------------------------------------------------


def _run_compaction(campaign_id: str, cfg: dict, system_prompt: str) -> str:
    """Ask the GM for a full /save, then restart the context from it."""
    context = campaigns.get_context(campaign_id)
    save_text = llm.complete(
        cfg, system_prompt, [*context, {"role": "user", "content": COMPACT_INSTRUCTION}]
    )
    filename = campaigns.write_save(campaign_id, save_text, "compaction")

    keep = int(cfg["compact_keep_messages"])
    tail = context[-keep:] if keep > 0 else []
    resume = (
        "OUT OF CHARACTER: this campaign's context was compacted to stay within "
        "the model's window. Below is the campaign save produced at the moment of "
        "compaction, followed by the most recent exchanges verbatim. Load this "
        "state as established campaign history and continue seamlessly — do not "
        "recap it to the player.\n\n=== CAMPAIGN SAVE ===\n"
        + save_text
        + "\n=== END CAMPAIGN SAVE ==="
    )
    campaigns.set_context(campaign_id, [{"role": "user", "content": resume}, *tail])
    campaigns.append_transcript(
        campaign_id, {"role": "system", "content": f"Context compacted → saves/{filename}"}
    )
    return filename


@app.post("/api/campaigns/{campaign_id}/compact")
def compact_campaign(campaign_id: str):
    try:
        campaigns.get_meta(campaign_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "campaign not found")
    cfg = settings_store.load()
    try:
        filename = _run_compaction(campaign_id, cfg, prompt.build_system_prompt())
    except llm.BackendError as e:
        raise HTTPException(502, str(e))
    return {"ok": True, "save": filename}


# --- chat --------------------------------------------------------------------


@app.post("/api/campaigns/{campaign_id}/message")
def send_message(campaign_id: str, body: UserMessage):
    try:
        campaigns.get_meta(campaign_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "campaign not found")

    content = body.content.strip()
    if not content:
        raise HTTPException(400, "empty message")

    cfg = settings_store.load()
    system_prompt = prompt.build_system_prompt()

    def event(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def generate():
        try:
            # Auto-compact before the new turn if the context has grown too far.
            context = campaigns.get_context(campaign_id)
            context_tokens = sum(prompt.estimate_tokens(m["content"]) for m in context)
            if context_tokens > int(cfg["compact_after_tokens"]):
                yield event({"type": "status", "text": "Compacting campaign context…"})
                _run_compaction(campaign_id, cfg, system_prompt)

            campaigns.append_transcript(campaign_id, {"role": "user", "content": content})
            context = campaigns.append_context(campaign_id, "user", content)

            reply_parts = []
            for chunk in llm.stream_reply(cfg, system_prompt, context):
                reply_parts.append(chunk)
                yield event({"type": "delta", "text": chunk})
            reply = "".join(reply_parts)

            campaigns.append_transcript(campaign_id, {"role": "assistant", "content": reply})
            campaigns.append_context(campaign_id, "assistant", reply)
            campaigns.touch(campaign_id)

            # A /save response is also captured to disk as a real file.
            if content.lower().startswith("/save") and reply.strip():
                filename = campaigns.write_save(campaign_id, reply, "manual")
                yield event({"type": "status", "text": f"Save written: saves/{filename}"})

            yield event({"type": "done"})
        except llm.BackendError as e:
            yield event({"type": "error", "text": str(e)})
        except Exception as e:  # surface unexpected failures to the UI
            yield event({"type": "error", "text": f"Unexpected server error: {e}"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    print("Talkar RPG — http://localhost:8642")
    uvicorn.run(app, host="127.0.0.1", port=8642, log_level="warning")
