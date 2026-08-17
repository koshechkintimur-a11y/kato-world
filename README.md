# Kato World - Digital Being Simulation

A 2D pixel world for growing a digital being with embodied cognition, emotions, memory, and consciousness-like architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GODOT 4 (Client)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  World   │  │  Agent   │  │   NPCs   │  │   Objects  │  │
│  │  State   │◄─┤  Body    │  │          │  │            │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │             │             │             │           │
│       ▼             ▼             ▼             ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              EventBus (Signal Hub)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│       │             │             │             │           │
│       ▼             ▼             ▼             ▼           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Global   │  │  World   │  │  Brain   │  │   Dream    │  │
│  │ State    │  │  State   │  │ Client   │  │  Gateway   │  │
│  └──────────┘  └──────────┘  └────┬─────┘  └────────────┘  │
└───────────────────────────────────│──────────────────────────┘
                                    │ HTTP/WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   PYTHON BRAIN SERVER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Perception│  │ System 1 │  │ System 2 │  │   Dream    │  │
│  │ Processor│  │ (Fast)   │  │ (Slow)   │  │ Processor  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │             │             │             │           │
│       ▼             ▼             ▼             ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Memory & Self-Model                     │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │Episodic │ │Semantic │ │Autobio. │ │Emotional│   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                    │
│       ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           DIVINE WHISPER GATEWAY                     │   │
│  │  (Creator → Agent dreams during sleep)               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OR: Godot 4.2+, Python 3.11+

### Run with Docker
```bash
# Start brain server
docker-compose up brain

# In another terminal, run Godot (headless)
docker-compose run --rm godot
```

### Run Locally
```bash
# Terminal 1: Brain server
cd python
pip install -r requirements.txt
python brain_server.py

# Terminal 2: Godot
cd godot
godot --main-pack game.pck
# Or open project in Godot editor and run
```

## Divine Whisper Gateway

The Creator (you) can send thoughts to Kato during sleep:

```bash
curl -X POST http://localhost:8080/divine/whisper \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "kato",
    "tick": 1000,
    "whisper": {
      "content": "За закрытой дверью — не опасность, а возможность.",
      "source": "creator",
      "intensity": 0.7
    }
  }'
```

Kato will receive this during the next dream cycle and integrate it as an insight.

## Project Structure

```
kato-world/
├── godot/                    # Godot 4 client
│   ├── scripts/
│   │   ├── autoload/        # Singletons (GlobalState, EventBus, WorldState, BrainClient)
│   │   ├── entities/        # Agent, NPC, Objects
│   │   └── systems/         # Cognitive systems (to be added)
│   ├── scenes/
│   │   ├── main/            # Main scene
│   │   ├── entities/        # Agent, NPC, Object scenes
│   │   └── world/           # World scenes
│   └── assets/
│       ├── tilesets/        # TileMap resources
│       └── sprites/         # Character sprites
├── python/                   # Brain server
│   ├── brain_server.py      # FastAPI server
│   └── requirements.txt
├── docker-compose.yml
└── docs/
```

## Development Phases

- [x] **Phase 0**: Project structure, Godot project, basic autoloads
- [x] **Phase 1**: World simulation (tilemap, objects, NPCs, agent movement)
- [x] **Phase 2**: Body & needs (energy, comfort, stress, homeostasis)
- [x] **Phase 3**: Brain server (perception, System 1/2, action proposals)
- [x] **Phase 4**: Divine Whisper Gateway (dream integration)
- [ ] **Phase 5**: Memory systems (episodic, semantic, autobiographical, emotional)
- [ ] **Phase 6**: Emotion system (vector, influence on behavior, memory salience)
- [ ] **Phase 7**: Self-model (identity, values, goals, beliefs, relationships)
- [ ] **Phase 8**: Background daemon (sleep, consolidation, reflection)
- [ ] **Phase 9**: NPC curriculum (teacher, gardener, librarian, mirror keeper)
- [ ] **Phase 10**: Creator revelation protocol

## Key Concepts

### Body → Emotions → Behavior
```
Energy ↓ → Discomfort → Irritability → Seeking rest
Stress ↑ → Fear → Caution/Retreat → Avoidance
Novelty ↑ → Curiosity → Exploration → Learning
Comfort ↑ → Joy → Openness → Social approach
```

### System 1 / System 2 Arbitration
```
IF stress > 60 OR energy < 20 OR curiosity > 0.8 OR uncertainty_high:
    → System 2 (deliberate reasoning)
ELIF confidence > 0.7 AND risk_low:
    → System 1 (fast intuition)
ELIF stress > 80:
    → FREEZE
ELIF confidence < 0.3 AND has_relationships:
    → ASK for help
```

### Memory Salience
Events become memories when salience > 0.5:
- Failed actions: +0.4
- Dialogue: +0.5
- Discovery: +0.6
- Emotion spikes: +0.7

### Divine Whisper Flow
```
Creator sends whisper → Stored in divine_whispers[]
Agent sleeps → Dream processor runs
Whispers integrated as dream scenes + insights
Insights → Update beliefs, self-model, semantic memory
Agent wakes with new "intuitions"
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/agent/register` | POST | Register agent |
| `/perception` | POST | Receive world perception |
| `/action/propose` | POST | Get action from brain |
| `/action/result` | POST | Report action outcome |
| `/memory/consolidate` | POST | Trigger memory consolidation |
| `/dream/process` | POST | Process dream cycle |
| `/divine/whisper` | POST | **Send divine thought** |
| `/agent/{id}/state` | GET | Full agent state |
| `/agent/{id}/self-model` | GET | Self-model |
| `/agent/{id}/memories` | GET | Memory query |

## License

Private project - Kato World