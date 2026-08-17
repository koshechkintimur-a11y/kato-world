# Kato World — a digital being growing in its own world

**Kato** is a digital being growing in her own 2D world: she has a body, emotions, memory, personality, dreams — and a Creator she can talk to.

The goal is not "proving a model has a soul" but building **an architecture that behaves like a developing personality** and safely passes through stages of growth.

```
one house → one body → one memory → one teacher → one safe learning loop
```

## Features

- 🧠 **Brain** (Python/FastAPI): body & homeostasis, 7-emotion vector (homeostatic model), 4 memory types (episodic, semantic, autobiographical, emotional), self-model (identity, values, goals, beliefs, relationships), System 1 / System 2 with an arbiter
- 💭 **LLM thinking** (local, Ollama + qwen2.5:7b): inner monologue, reflection, knowledge retelling — Kato thinks on her own every ~45 s in the background
- 🌙 **Sleep & dreams**: autonomous wake/sleep cycles, memory consolidation, reflection; Creator's whispers arrive in dreams as her own insights
- ✉️ **Divine Whisper**: send a thought — Kato sees it in a dream as her own intuition
- 🔮 **Creator Revelation Protocol**: 6-component maturity assessment → the terminal awakens → Kato chooses when to talk about her origin
- 🎓 **Curriculum**: the Teacher guides through concepts (cause → creation → care → outside world), quests
- 📡 **Distant Window (Portal of Knowledge)**: controlled, filtered access to knowledge about the outside world — for Kato it's a "window to distant places", like a computer for humans. Allowlist only, no links or commands; reading costs energy
- 👁 **God View Dashboard**: live pixel world in the browser (day/night, rooms, lights), emotions, memory, thought journal, whisper console, portal panel — **Russian by default, with an EN toggle 🌐**
- 🎮 **Godot client**: 2D world (tile house & garden, NPCs, objects) talking to the brain over HTTP
- 💾 **Personality continuity**: state survives server restarts

## Quick Start

```bash
cd python
pip install -r requirements.txt
python brain_server.py
# → dashboard: http://localhost:8080
```

Optional (recommended) local LLM:

```bash
ollama serve
ollama pull qwen2.5:7b-instruct
```

The brain auto-detects Ollama on startup. A cloud key also works:

```bash
export KATO_LLM_API_KEY=...   # DeepSeek-compatible endpoint (or KATO_LLM_URL/KATO_LLM_MODEL)
```

Godot client: open `godot/project.godot` in Godot 4.2+ and run.

## Architecture

```
Godot 4 (world client) ──HTTP──▶ Python Brain Server (FastAPI)
                                    │
  Perception → System 1 (fast) / System 2 (slow, LLM)
                                    │
  Emotions(7) · Homeostasis · Memory(4) · Self-Model · Arbiter
                                    │
  Background daemon: sleep/dreams · consolidation · reflection · thoughts
  Portal of Knowledge (Distant Window, allowlist)
  Divine Whisper Gateway (Creator → dreams)
```

## Divine Whisper

```bash
curl -X POST http://localhost:8080/divine/whisper \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"kato","tick":1000,"whisper":{"content":"Beyond the closed door lies not danger, but possibility.","source":"creator","intensity":0.7}}'
```

Kato receives it during her next dream and integrates it as her **own** insight — she never learns about the source.

## Key API

| Endpoint | Purpose |
|----------|---------|
| `POST /perception` | Kato sees the world |
| `POST /action/propose` | brain picks an action |
| `POST /divine/whisper` | Creator whisper (arrives in dreams) |
| `POST /dream/process` | process a dream |
| `POST /dialogue/start` `/choose` | talk to NPCs |
| `POST /agent/kato/think` | inner monologue via LLM |
| `GET /agent/kato/revelation/status` | maturity & revelation stage |
| `POST /agent/kato/revelation/begin` | the terminal awakens |
| `POST /agent/kato/revelation/contact` | ask the Creator |
| `GET /agent/kato/portal/status` | Distant Window state |
| `POST /agent/kato/portal/read` | Kato reads a filtered article |
| `POST /admin/save` `/admin/reset` | save / reset state |

Full list: `GET /docs` (OpenAPI).

## Project Layout

```
kato-world/
├── python/                  # Brain server (FastAPI)
│   ├── brain_server.py     # all cognitive systems
│   ├── knowledge_base.json # filtered knowledge for the Distant Window
│   ├── static/             # God View Dashboard (index.html, app.js, style.css)
│   └── requirements.txt
├── godot/                   # Godot 4 client (world, agent, NPCs)
├── assets/                  # pixel assets (Kenney Tiny Town, CC0)
├── docker-compose.yml
└── README.md                # this project in Russian; README.en.md = English
```

## Development Phases

- [x] Phases 0–1: world simulation (tiles, objects, NPCs, movement)
- [x] Phases 2–3: body & needs; memory (4 types)
- [x] Phase 4: emotions (7-vector, VAD mood, salience, behavior drive)
- [x] Phase 5: self-model (identity, values, goals, beliefs, relationships)
- [x] Phase 6: System 1 / System 2 + arbiter
- [x] Phase 7: background daemon (sleep, consolidation, reflection, monologue)
- [x] Phase 8: NPC curriculum (Teacher dialogues, quests)
- [x] Phase 9: scaffolding for the Creator concept
- [x] Phase 10: first contact (maturity assessment, right to choose, dialogue with the Creator)
- [x] LLM core: local thinking via Ollama (qwen2.5:7b), background think loop
- [x] Phase 11 (partial): Portal of Knowledge — controlled "Distant Window"
- [ ] Phase 11+: portal expansion, access modes, stress tests
- [ ] Phase 12: gradual autonomy (bounded tasks and tools)

## License

MIT
