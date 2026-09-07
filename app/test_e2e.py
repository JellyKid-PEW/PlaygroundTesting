"""End-to-end test for the Talkar RPG app — no API key required.

Runs a mock OpenAI-compatible model server plus the real app server in
threads, then exercises the full flow: settings, campaign creation, streamed
messages, /save capture, compaction, resume-from-save, and error recovery.

    python test_e2e.py
"""

import json
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

import campaigns
import settings as settings_store

MOCK_PORT = 49172
APP_PORT = 49173
BASE = f"http://127.0.0.1:{APP_PORT}"

GM_REPLY = "Rain taps the pier at *Aven's* Lower Port.\n\nWhat do you do?"
SAVE_REPLY = "CAMPAIGN SAVE\nPlayer: Test. Location: Aven. Migration Stage: 1."

mock_state = {"fail_next": False, "truncate_next": False}


class MockLLM(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        if mock_state["fail_next"]:
            mock_state["fail_next"] = False
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"mock failure")
            return
        if mock_state["truncate_next"]:
            mock_state["truncate_next"] = False
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            chunk = {"choices": [{"delta": {"content": "Partial repl"}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            tail = {"choices": [{"delta": {}, "finish_reason": "length"}]}
            self.wfile.write(f"data: {json.dumps(tail)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        last = body["messages"][-1]["content"]
        if "SYSTEM MAINTENANCE" in last or last.lower().startswith("/save"):
            reply = SAVE_REPLY
        else:
            reply = GM_REPLY
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        third = max(1, len(reply) // 3)
        for i in range(0, len(reply), third):
            chunk = {"choices": [{"delta": {"content": reply[i : i + third]}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, *args):
        pass


def start_servers(tmp: Path):
    # Isolate the app's state in a temp dir
    campaigns.DATA_DIR = tmp / "campaigns"
    settings_store.CONFIG_PATH = tmp / "config.json"

    mock = ThreadingHTTPServer(("127.0.0.1", MOCK_PORT), MockLLM)
    threading.Thread(target=mock.serve_forever, daemon=True).start()

    import uvicorn

    import server

    config = uvicorn.Config(server.app, host="127.0.0.1", port=APP_PORT, log_level="error")
    app_server = uvicorn.Server(config)
    threading.Thread(target=app_server.run, daemon=True).start()
    for _ in range(50):
        try:
            httpx.get(f"{BASE}/api/settings", timeout=1)
            return
        except httpx.HTTPError:
            time.sleep(0.1)
    raise RuntimeError("app server did not start")


def send_message(client: httpx.Client, campaign_id: str, content: str) -> dict:
    """Post a message and collect the SSE events."""
    events = {"deltas": [], "status": [], "errors": [], "done": False}
    with client.stream(
        "POST", f"{BASE}/api/campaigns/{campaign_id}/message", json={"content": content}
    ) as response:
        assert response.status_code == 200, response.status_code
        buffer = ""
        for chunk in response.iter_text():
            buffer += chunk
        for raw in buffer.split("\n\n"):
            if not raw.startswith("data: "):
                continue
            evt = json.loads(raw[6:])
            if evt["type"] == "delta":
                events["deltas"].append(evt["text"])
            elif evt["type"] == "status":
                events["status"].append(evt["text"])
            elif evt["type"] == "error":
                events["errors"].append(evt["text"])
            elif evt["type"] == "done":
                events["done"] = True
    return events


def main():
    with tempfile.TemporaryDirectory() as tmp:
        start_servers(Path(tmp))
        client = httpx.Client(timeout=30)

        # settings: point at the mock backend
        response = client.put(
            f"{BASE}/api/settings",
            json={
                "backend": "openai_compatible",
                "openai_base_url": f"http://127.0.0.1:{MOCK_PORT}/v1",
                "compact_after_tokens": 80000,
            },
        )
        assert response.json()["backend"] == "openai_compatible"

        # create + play
        campaign_id = client.post(f"{BASE}/api/campaigns", json={"name": "E2E"}).json()["id"]
        events = send_message(client, campaign_id, "START NEW CAMPAIGN")
        assert events["done"] and "".join(events["deltas"]) == GM_REPLY
        print("PASS  streamed reply")

        # /save writes a save file
        events = send_message(client, campaign_id, "/save")
        assert events["done"] and any("Save written" in s for s in events["status"])
        print("PASS  /save capture")

        # compaction produces a save and rebuilds the context
        response = client.post(f"{BASE}/api/campaigns/{campaign_id}/compact")
        assert response.status_code == 200
        data = client.get(f"{BASE}/api/campaigns/{campaign_id}").json()
        assert len(data["saves"]) == 2
        context = campaigns.get_context(campaign_id)
        assert context[0]["content"].startswith("OUT OF CHARACTER")
        assert SAVE_REPLY in context[0]["content"]
        print("PASS  compaction")

        # a failed turn leaves the working context clean for retry
        before = campaigns.get_context(campaign_id)
        mock_state["fail_next"] = True
        events = send_message(client, campaign_id, "hello?")
        assert events["errors"] and not events["done"]
        assert campaigns.get_context(campaign_id) == before
        events = send_message(client, campaign_id, "hello again")
        assert events["done"]
        print("PASS  error recovery")

        # a truncated compaction save must NOT replace the working context
        before = campaigns.get_context(campaign_id)
        mock_state["truncate_next"] = True
        response = client.post(f"{BASE}/api/campaigns/{campaign_id}/compact")
        assert response.status_code == 502, response.status_code
        assert campaigns.get_context(campaign_id) == before
        print("PASS  truncated compaction rejected")

        # ...but an interactive turn that hits max_tokens is kept, annotated
        mock_state["truncate_next"] = True
        events = send_message(client, campaign_id, "keep going")
        assert events["done"]
        assert "cut off at the max_tokens limit" in "".join(events["deltas"])
        assert "cut off at the max_tokens limit" in campaigns.get_context(campaign_id)[-1]["content"]
        print("PASS  interactive truncation annotated")

        # unicode round-trip through saves (the docs use →, —, ↔ heavily)
        unicode_text = "Route Pere → Aven — storm ↔ wake"
        name = campaigns.write_save(campaign_id, unicode_text, "unicode")
        assert campaigns.read_save(campaign_id, name) == unicode_text
        print("PASS  unicode save round-trip")

        # resume-from-save creates a seeded campaign
        save_name = data["saves"][-1]
        response = client.post(
            f"{BASE}/api/campaigns",
            json={"name": "Fork", "source_campaign": campaign_id, "source_save": save_name},
        )
        fork_id = response.json()["id"]
        fork_context = campaigns.get_context(fork_id)
        assert len(fork_context) == 1 and SAVE_REPLY in fork_context[0]["content"]
        events = send_message(client, fork_id, "continue")
        assert events["done"]
        print("PASS  resume from save")

        print("\nAll end-to-end tests passed.")


if __name__ == "__main__":
    main()
