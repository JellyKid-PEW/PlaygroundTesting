# Talkar RPG — Local Web App

A standalone application that runs the Talkar Persistent Narrative RPG. It loads the seven instruction-stack documents from the repository root as the Game Master's system prompt, manages campaigns on disk, and talks to either the Anthropic API or a local model server.

## Setup

Requires Python 3.10+.

```bash
cd app
pip install -r requirements.txt
python server.py
```

Then open **http://localhost:8642** in your browser.

## Choosing a backend (Settings, bottom-left)

**Anthropic API** — full-fidelity Game Master. Get a key from [console.anthropic.com](https://console.anthropic.com), then either export it before launching:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

or paste it into Settings (it is then stored in plain text in `app/config.json`, which is gitignored — prefer the environment variable if that concerns you). The ~60k-token instruction stack is sent with prompt caching enabled, so after the first message of a session it bills at roughly 10% of normal input price. Default model: `claude-opus-5`.

**Local model server** — any server speaking the OpenAI-compatible chat API:

| Server | Base URL | Note |
|---|---|---|
| gpt4all | `http://localhost:4891/v1` | Enable "API server" in gpt4all's settings |
| Ollama | `http://localhost:11434/v1` | |
| LM Studio | `http://localhost:1234/v1` | Enable the local server tab |

**Honest expectations for local models:** the instruction stack alone is ~60k tokens. Small models (7B–13B) usually can't fit it in context, and those that can will follow it loosely — you'll get a flavor of Talkar, not the full simulation. If you go local: use the largest model and context window you can run, and lower "Compact after" in Settings to a few thousand tokens.

## Playing

1. **New campaign**, give it a name.
2. Type **START NEW CAMPAIGN** — the GM will ask for your character's name, age, circumstances, background preference, and relationship emphasis, then start you in the Aven Corridor.
3. Play by typing anything. Out-of-character commands: `/status`, `/character`, `/known`, `/suspicions`, `/relationships`, `/threads`, `/recap`, `/save`, `/ooc <question>`.

## How long campaigns survive the context window

The app keeps two records per campaign:

- **Transcript** — the full history, append-only, always shown in the UI.
- **Working context** — what is actually sent to the model each turn.

When the working context passes the "Compact after" threshold (or you press **Compact**), the app asks the GM for a complete portable campaign save — the exact save-state format the RPG Engine itself defines (§51) — writes it to `app/data/campaigns/<id>/saves/`, and restarts the working context from that save plus the last few exchanges. Play continues seamlessly, and every save file doubles as a portable backup you could hand to any other instance of the GM.

Typing `/save` yourself also writes the GM's response to the saves folder.

## Where things live

```
app/config.json                     settings (gitignored; may contain your API key)
app/data/campaigns/<id>/
  meta.json                         name, timestamps
  transcript.jsonl                  full history
  context.json                      current working context
  saves/                            campaign saves (compactions + manual /save)
```

Everything is plain text — copy the campaign folder to back it up or move it to another machine.
