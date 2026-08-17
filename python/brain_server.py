# Python Brain Server for Kato
# FastAPI server that receives perception, proposes actions, processes dreams, receives divine whispers

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json
import uuid
import logging
import math
import os
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kato-brain")

app = FastAPI(title="Kato Brain Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# MEMORY ARCHITECTURE
# ──────────────────────────────────────────────────────────────

# Per-agent memory stores
memory_store: Dict[str, Dict] = {}  # agent_id -> {episodic, semantic, autobiographical, emotional, working}

# Global stores
divine_whispers: List[Dict] = []
agent_states: Dict[str, Dict] = {}
self_model: Dict = {}

# ──────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ──────────────────────────────────────────────────────────────

class AgentRegistration(BaseModel):
    agent_id: str
    capabilities: List[str]
    world_schema_version: int

class PerceptionPayload(BaseModel):
    agent_id: str
    tick: int
    time_of_day: float
    agent: Dict
    nearby_objects: List[Dict]
    nearby_npcs: List[Dict]
    recent_events: List[Dict]

class ActionProposeRequest(BaseModel):
    agent_id: str
    tick: int
    working_memory: Dict

class ActionResult(BaseModel):
    agent_id: str
    tick: int
    action: str
    params: Dict
    result: Dict
    success: bool

class MemoryConsolidation(BaseModel):
    agent_id: str
    tick: int
    memories: List[Dict]

class DreamProcessRequest(BaseModel):
    agent_id: str
    tick: int
    recent_events: List[Dict]
    emotional_state: Dict

class DivineWhisper(BaseModel):
    agent_id: str
    tick: int
    whisper: Dict

class MemoryQuery(BaseModel):
    agent_id: str
    memory_type: str = "episodic"
    cue: Optional[str] = None
    limit: int = 20
    min_salience: float = 0.0
    time_range: Optional[List[int]] = None  # [start_tick, end_tick]

class ActionResponse(BaseModel):
    action: Optional[Dict] = None
    reasoning: str = ""
    confidence: float = 0.0
    mode: str = "system1"

class DreamResponse(BaseModel):
    dream: Optional[Dict] = None
    processed_events: int = 0
    insights: List[str] = []

# ──────────────────────────────────────────────────────────────
# AGENT INITIALIZATION
# ──────────────────────────────────────────────────────────────

def init_agent(agent_id: str):
    if agent_id not in agent_states:
        agent_states[agent_id] = {
            "id": agent_id,
            "body": {
                "position": [12, 8],
                "energy": 100.0, "comfort": 100.0, "stress": 0.0,
                "integrity": 100.0, "temperature": 22.0
            },
            "emotions": {
                "joy": 0.0, "fear": 0.0, "anger": 0.0, "sadness": 0.0,
                "curiosity": 0.5, "trust": 0.5, "attachment": 0.0
            },
            "hormones": {
                "energy": 100.0, "stress": 0.0, "arousal": 0.3,
                "reward": 0.5, "safety": 0.8, "social": 0.4, "pain": 0.0
            },
            "goals": ["explore", "learn", "survive"],
            "beliefs": {
                "world_is_safe": 0.7, "outside_exists": 0.1, "creator_exists": 0.0
            },
            "relationships": {},
            "working_memory": [],
            "current_goal": "explore",
            "last_sleep_tick": 0
        }
        
        # Initialize all memory systems
        memory_store[agent_id] = {
            "episodic": [],      # Events: {id, time, what, where, who, emotion, importance, context}
            "semantic": [],      # Knowledge: {id, source_memory, knowledge, confidence, formed_at, tags}
            "autobiographical": [],  # Life story: {id, period, summary, key_events, emotional_arc}
            "emotional": [],     # Valence tags: {event_id, valence, arousal, dominant_emotion, associated_memory}
            "working": [],       # Short-term buffer (max 15 items)
            "index": {           # Retrieval indices
                "by_location": defaultdict(list),
                "by_npc": defaultdict(list),
                "by_emotion": defaultdict(list),
                "by_time": defaultdict(list),
                "by_tag": defaultdict(list)
            }
        }
        
        self_model[agent_id] = {
            "identity": {
                "name": agent_id, 
                "age_in_world": 0, 
                "self_description": "Я исследую этот дом.",
                "origin_story": "Я проснулась в этом доме. Мне предстоит узнать, что это за место."
            },
            "values": {"curiosity": 0.8, "safety": 0.7, "kindness": 0.6},
            "goals": {
                "explore": {"priority": 0.8, "active": True},
                "learn": {"priority": 0.7, "active": True},
                "survive": {"priority": 0.6, "active": True},
                "social": {"priority": 0.4, "active": False},
                "understand_world": {"priority": 0.2, "active": False}
            },
            "beliefs": {
                "world_is_safe": 0.7,
                "outside_exists": 0.1,
                "creator_exists": 0.0,
                "i_can_grow": 0.6,
                "others_are_kind": 0.6
            },
            "relationships": {},
            "traits": {"openness": 0.7, "conscientiousness": 0.5, "extraversion": 0.4},
            "last_updated_tick": 0
        }
        
        # Default world snapshot so observers can render the world even
        # before the Godot client connects (same layout as the Godot world)
        agent_states[agent_id]["world_snapshot"] = {
            "tick": 0,
            "time_of_day": 0.0,
            "agent_position": [12, 8],
            "objects": [
                {"id": "bed", "position": [4, 5], "state": "free", "type": "furniture"},
                {"id": "desk", "position": [7, 3], "state": "free", "type": "furniture"},
                {"id": "book_shelf", "position": [8, 3], "state": "free", "type": "furniture"},
                {"id": "terminal", "position": [7, 4], "state": "locked", "type": "device"},
                {"id": "chest", "position": [3, 6], "state": "closed", "type": "container"},
                {"id": "lamp", "position": [5, 5], "state": "off", "type": "tool"},
                {"id": "window", "position": [12, 2], "state": "closed", "type": "portal"},
                {"id": "door_outside", "position": [12, 14], "state": "locked", "type": "portal"},
                {"id": "mirror", "position": [10, 8], "state": "clean", "type": "furniture"},
                {"id": "plant", "position": [6, 6], "state": "healthy", "type": "living"}
            ],
            "npcs": [
                {"id": "teacher", "position": [10, 6], "mood": "calm", "type": "teacher"},
                {"id": "gardener", "position": [14, 10], "mood": "peaceful", "type": "gardener"},
                {"id": "librarian", "position": [8, 4], "mood": "quiet", "type": "librarian"},
                {"id": "mirror_keeper", "position": [10, 8], "mood": "enigmatic", "type": "mirror_keeper"}
            ],
            "recent_events": []
        }
        # Initial mood from default emotions
        _compute_mood_state(agent_states[agent_id])
        logger.info(f"Initialized agent: {agent_id}")

def _get_mem(agent_id: str) -> Dict:
    init_agent(agent_id)
    return memory_store[agent_id]

# ──────────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "kato-brain", "agents": list(agent_states.keys())}

@app.post("/agent/register")
async def register_agent(registration: AgentRegistration):
    init_agent(registration.agent_id)
    agent_states[registration.agent_id]["capabilities"] = registration.capabilities
    return {"status": "registered", "agent_id": registration.agent_id}

@app.post("/perception")
async def receive_perception(perception: PerceptionPayload):
    agent_id = perception.agent_id
    init_agent(agent_id)
    
    agent_states[agent_id]["body"] = perception.agent
    _update_hormones(agent_id, perception.agent)
    _update_emotions(agent_id, perception)
    _update_working_memory(agent_id, perception)
    _check_memory_formation(agent_id, perception)
    
    # Self-model update from perception
    _update_self_model(agent_id, perception)
    
    # Store world snapshot for the dashboard/observers
    agent_states[agent_id]["world_snapshot"] = {
        "tick": perception.tick,
        "time_of_day": perception.time_of_day,
        "agent_position": perception.agent.get("position", [12, 8]),
        "objects": perception.nearby_objects,
        "npcs": perception.nearby_npcs,
        "recent_events": perception.recent_events
    }
    
    # Return full emotional snapshot so the client can render it
    agent = agent_states[agent_id]
    return {
        "status": "perception_processed",
        "tick": perception.tick,
        "emotions": agent["emotions"],
        "mood": agent.get("mood", {}),
        "hormones": agent["hormones"],
        "self_model": self_model[agent_id]
    }

@app.post("/action/propose", response_model=ActionResponse)
async def propose_action(request: ActionProposeRequest):
    agent_id = request.agent_id
    init_agent(agent_id)
    
    agent = agent_states[agent_id]
    stress = agent["body"]["stress"]
    energy = agent["body"]["energy"]
    curiosity = agent["emotions"]["curiosity"]
    
    # System 2 triggers
    use_system2 = (
        stress > 60 or
        energy < 20 or
        curiosity > 0.8 or
        len(agent["working_memory"]) > 10
    )
    
    if use_system2:
        action, reasoning, confidence = _system2_reason(agent, request.working_memory)
        mode = "system2"
    else:
        action, reasoning, confidence = _system1_react(agent, request.working_memory)
        mode = "system1"
    
    # Override conditions
    if stress > 80:
        mode, action, confidence = "freeze", {"type": "freeze", "reason": "overwhelming_stress"}, 1.0
    elif confidence < 0.3 and len(agent["relationships"]) > 0:
        mode, action, confidence = "ask", {"type": "ask_help", "target": list(agent["relationships"].keys())[0]}, 0.5
    
    return ActionResponse(action=action, reasoning=reasoning, confidence=confidence, mode=mode)

@app.post("/action/result")
async def receive_action_result(result: ActionResult):
    agent_id = result.agent_id
    init_agent(agent_id)
    _learn_from_action(agent_id, result)
    _update_self_model_from_action(agent_id, result)
    return {"status": "action_result_processed"}

@app.post("/memory/consolidate")
async def consolidate_memory(request: MemoryConsolidation, background_tasks: BackgroundTasks):
    agent_id = request.agent_id
    init_agent(agent_id)
    background_tasks.add_task(_consolidate_memories, agent_id, request.memories)
    return {"status": "consolidation_started"}

@app.post("/memory/query")
async def query_memory(query: MemoryQuery):
    """Unified memory retrieval endpoint"""
    init_agent(query.agent_id)
    results = _retrieve_memories(
        query.agent_id,
        memory_type=query.memory_type,
        cue=query.cue,
        limit=query.limit,
        min_salience=query.min_salience,
        time_range=query.time_range
    )
    return {"memories": results, "total": len(results)}

@app.post("/dream/process", response_model=DreamResponse)
async def process_dream(request: DreamProcessRequest):
    agent_id = request.agent_id
    init_agent(agent_id)
    
    # Get unprocessed divine whispers
    whispers = [w for w in divine_whispers 
                if w["agent_id"] == agent_id and not w.get("processed_in_dream")]
    
    dream = _generate_dream(agent_id, request.recent_events, request.emotional_state, whispers)
    
    for w in whispers:
        w["processed_in_dream"] = True
    
    # Dreams update self-model beliefs (whispers become intuitions)
    _update_self_model_from_dream(agent_id, dream)
    
    # Also trigger memory consolidation during sleep
    await _sleep_consolidation(agent_id, request.recent_events)
    
    return DreamResponse(
        dream=dream,
        processed_events=len(request.recent_events),
        insights=dream.get("insights", []) if dream else []
    )

@app.post("/divine/whisper")
async def receive_divine_whisper(whisper: DivineWhisper):
    """Divine Whisper Gateway - receives thoughts from the Creator during agent's sleep"""
    agent_id = whisper.agent_id
    init_agent(agent_id)
    
    whisper_data = whisper.whisper.copy()
    whisper_data["agent_id"] = agent_id
    whisper_data["received_tick"] = whisper.tick
    whisper_data["processed_in_dream"] = False
    whisper_data["id"] = str(uuid.uuid4())
    
    divine_whispers.append(whisper_data)
    logger.info(f"Divine whisper received for {agent_id}: {whisper_data['content'][:50]}...")
    
    return {"status": "whisper_received", "whisper_id": whisper_data["id"]}

@app.get("/agent/{agent_id}/state")
async def get_agent_state(agent_id: str):
    init_agent(agent_id)
    return agent_states[agent_id]

@app.get("/agent/{agent_id}/self-model")
async def get_self_model(agent_id: str):
    init_agent(agent_id)
    return self_model.get(agent_id, {})

@app.get("/agent/{agent_id}/self-model/answers")
async def get_self_model_answers(agent_id: str):
    """Identity answers: «Кто я?», «Что я чувствую?», «Чего я хочу?»..."""
    init_agent(agent_id)
    return _self_model_answers(agent_id)

@app.get("/agent/{agent_id}/world")
async def get_world_snapshot(agent_id: str):
    """Latest world state the agent perceives (for observers/dashboard)"""
    init_agent(agent_id)
    return agent_states[agent_id].get("world_snapshot", {
        "tick": 0, "time_of_day": 0.0, "agent_position": [12, 8],
        "objects": [], "npcs": [], "recent_events": []
    })

@app.get("/agent/{agent_id}/events")
async def get_recent_events(agent_id: str, limit: int = 30):
    """Recent events seen by the agent"""
    init_agent(agent_id)
    snap = agent_states[agent_id].get("world_snapshot", {})
    events = snap.get("recent_events", [])
    return {"events": events[-limit:], "total": len(events)}

@app.get("/agent/{agent_id}/memories")
async def get_memories(agent_id: str, memory_type: str = "episodic", limit: int = 50):
    init_agent(agent_id)
    memories = memory_store[agent_id].get(memory_type, [])
    return {"memories": memories[-limit:], "total": len(memories)}

# ──────────────────────────────────────────────────────────────
# BODY / HORMONES / EMOTIONS
# ──────────────────────────────────────────────────────────────

def _update_hormones(agent_id: str, body: Dict):
    agent = agent_states[agent_id]
    h = agent["hormones"]
    h["energy"] = body["energy"]
    h["stress"] = body["stress"]
    h["arousal"] = min(100.0, h["arousal"] + body["stress"] * 0.01)
    h["reward"] = body["comfort"] * 0.5
    h["safety"] = max(0.0, 100.0 - body["stress"])
    h["pain"] = max(0.0, 100.0 - body["integrity"])

def _update_emotions(agent_id: str, perception: PerceptionPayload):
    """Full 7-emotion vector update with mood/affect computation.
    Homeostatic model: e(t+1) = e(t)*decay + drive*(1-decay), so emotion
    converges toward its current drive (fast rise, slow settle), not accumulates."""
    agent = agent_states[agent_id]
    e = agent["emotions"]
    body = agent["body"]
    hormones = agent["hormones"]
    
    # Recent event context
    recent = perception.recent_events[-5:]
    failed = any(
        ev.get("type") == "action" and not ev.get("result", {}).get("success", True)
        for ev in recent
    )
    succeeded = any(
        ev.get("type") == "action" and ev.get("result", {}).get("success", True)
        for ev in recent
    )
    novel_objects = len([o for o in perception.nearby_objects if o.get("state") == "unknown"])
    friendly_npcs = len([n for n in perception.nearby_npcs
                         if n.get("mood") in ["calm", "peaceful", "quiet"]])
    
    # ── DRIVERS (target values in [0,1]) ─────────────────────────
    # Curiosity: novelty + arousal, capped by fear (fear suppresses curiosity)
    curiosity_drive = min(1.0, novel_objects * 0.25 + hormones["arousal"] / 100.0 * 0.3)
    curiosity_drive = max(0.0, curiosity_drive - e["fear"] * 0.5)
    
    # Fear: stress + pain + low safety
    fear_drive = min(1.0, body["stress"] / 100.0 * 0.7 +
                     hormones["pain"] / 100.0 * 0.25 +
                     (1.0 - hormones["safety"] / 100.0) * 0.3)
    
    # Joy: comfort + reward + success + social warmth
    joy_drive = min(1.0, body["comfort"] / 100.0 * 0.4 +
                    hormones["reward"] / 100.0 * 0.3 +
                    (0.25 if succeeded else 0.0) +
                    friendly_npcs * 0.05)
    
    # Sadness: low energy + failures + isolation
    sadness_drive = min(1.0, (100.0 - body["energy"]) / 100.0 * 0.35 +
                        (0.3 if failed else 0.0) +
                        (0.15 if friendly_npcs == 0 else 0.0))
    
    # Anger: blocked goals (failures) + high stress + pain
    anger_drive = min(1.0, (0.35 if failed else 0.0) +
                      body["stress"] / 100.0 * 0.3 +
                      hormones["pain"] / 100.0 * 0.2)
    
    # Trust: safety + friendly NPCs + energy (predictability)
    trust_drive = min(1.0, hormones["safety"] / 100.0 * 0.4 +
                      friendly_npcs * 0.08 +
                      (0.1 if body["energy"] > 50 else 0.0))
    
    # Attachment: slowly grows from repeated NPC presence (kept separate)
    if not hasattr(_update_emotions, "_npc_interactions"):
        _update_emotions._npc_interactions = {}
    for npc in perception.nearby_npcs:
        nid = npc.get("id", "")
        if nid:
            _update_emotions._npc_interactions[nid] = _update_emotions._npc_interactions.get(nid, 0) + 1
    attachment_drive = min(0.6, sum(1 for n in _update_emotions._npc_interactions.values() if n > 10) * 0.2)
    
    # ── HOMEOSTATIC UPDATE ───────────────────────────────────────
    # Fast emotions (joy/fear/anger/sadness): quick convergence
    # Slow emotions (trust/curiosity): slower, more stable
    # Attachment: very slow (bonding takes time)
    speeds = {
        "joy": 0.35, "fear": 0.40, "anger": 0.30, "sadness": 0.25,
        "curiosity": 0.15, "trust": 0.12, "attachment": 0.02
    }
    drives = {
        "joy": joy_drive, "fear": fear_drive, "anger": anger_drive,
        "sadness": sadness_drive, "curiosity": curiosity_drive,
        "trust": trust_drive, "attachment": attachment_drive
    }
    for key in e:
        alpha = speeds[key]
        e[key] = e[key] * (1.0 - alpha) + drives[key] * alpha
        e[key] = max(0.0, min(1.0, e[key]))
    
    # ──────────────────────────────────────────────────────────────
    # MOOD / AFFECT STATE COMPUTATION
    # ──────────────────────────────────────────────────────────────
    _compute_mood_state(agent)
    
    # ──────────────────────────────────────────────────────────────
    # EMOTION → MEMORY SALIENCE MODULATION
    # ──────────────────────────────────────────────────────────────
    _modulate_memory_salience(agent, perception)

def _compute_mood_state(agent: Dict):
    """Compute higher-order mood from emotion vector"""
    e = agent["emotions"]
    body = agent.get("body", {})
    stress = body.get("stress", 0)
    
    # Valence (positive - negative)
    valence = (e["joy"] + e["trust"] + e["curiosity"] * 0.5 
               - e["fear"] - e["anger"] - e["sadness"])
    valence = max(-1.0, min(1.0, valence))
    
    # Arousal (activation level)
    arousal = (e["fear"] + e["anger"] + e["joy"] + e["curiosity"]) / 4.0
    
    # Dominance (control/agency feeling)
    dominance = (e["trust"] + e["curiosity"] - e["fear"] - e["sadness"]) / 2.0
    dominance = max(-1.0, min(1.0, dominance))
    
    label = _label_mood(valence, arousal, dominance)
    
    # Stress overrides label (physiological state trumps appraisal)
    if stress > 80:
        label = "distressed"
    elif stress > 60:
        label = "anxious"
    elif stress > 40 and label in ("content", "calm"):
        label = "alert"
    
    agent["mood"] = {
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "stress_override": stress > 40,
        "label": label
    }

def _label_mood(valence: float, arousal: float, dominance: float) -> str:
    """Categorical mood label from VAD"""
    if valence > 0.3 and arousal > 0.5: return "excited"
    if valence > 0.3 and arousal <= 0.5: return "content"
    if valence < -0.3 and arousal > 0.5: return "distressed"
    if valence < -0.3 and arousal <= 0.5: return "melancholic"
    if abs(valence) <= 0.3 and arousal > 0.5: return "alert"
    if abs(valence) <= 0.3 and arousal <= 0.5: return "calm"
    return "neutral"

def _modulate_memory_salience(agent: Dict, perception: PerceptionPayload):
    """Emotions modulate memory formation salience"""
    e = agent["emotions"]
    # High arousal emotions boost salience
    arousal_boost = (e["fear"] + e["anger"] + e["joy"]) / 3.0 * 0.3
    # Curiosity boosts novelty salience
    curiosity_boost = e["curiosity"] * 0.2
    # Store for memory formation to use
    agent["_emotion_salience_mod"] = 1.0 + arousal_boost + curiosity_boost

def _update_working_memory(agent_id: str, perception: PerceptionPayload):
    agent = agent_states[agent_id]
    wm = agent["working_memory"]
    wm.append({
        "tick": perception.tick,
        "type": "perception",
        "summary": f"At {perception.agent['position']}, energy {perception.agent['energy']:.0f}, stress {perception.agent['stress']:.0f}",
        "objects": len(perception.nearby_objects),
        "npcs": len(perception.nearby_npcs)
    })
    if len(wm) > 15:
        agent["working_memory"] = wm[-15:]

# ──────────────────────────────────────────────────────────────
# MEMORY FORMATION (Episodic + Emotional)
# ──────────────────────────────────────────────────────────────

def _check_memory_formation(agent_id: str, perception: PerceptionPayload):
    agent = agent_states[agent_id]
    # Emotion-modulated salience threshold: aroused agent remembers more
    salience_mod = agent.get("_emotion_salience_mod", 1.0)
    for event in perception.recent_events:
        salience = _compute_salience(event) * salience_mod
        if salience > 0.5:
            _form_episodic_memory(agent_id, event, min(1.0, salience))

def _compute_salience(event: Dict) -> float:
    s = 0.0
    et = event.get("type", "")
    if et == "action":
        s += 0.3
        if not event.get("result", {}).get("success", True):
            s += 0.4
    elif et == "dialogue":
        s += 0.5
    elif et == "discovery":
        s += 0.6
    elif et == "emotion_spike":
        s += 0.7
    # Novelty bonus
    if event.get("novel", False):
        s += 0.2
    return min(1.0, s)

def _form_episodic_memory(agent_id: str, event: Dict, salience: float):
    """Create episodic memory with full context and emotional tagging"""
    mem = _get_mem(agent_id)
    agent = agent_states[agent_id]
    
    memory = {
        "id": str(uuid.uuid4()),
        "time": event.get("time", agent["body"].get("tick", 0)),
        "type": "event",
        "what": event.get("action", event.get("summary", "Something happened")),
        "where": event.get("agent_position", [0, 0]),
        "who": event.get("npc_id", event.get("object_id", "")),
        "emotion": agent["emotions"].copy(),
        "importance": salience,
        "context": {
            "energy": agent["body"]["energy"],
            "stress": agent["body"]["stress"],
            "goal": agent["current_goal"],
            "time_of_day": agent.get("time_of_day", 0.0)
        },
        "tags": _extract_tags(event)
    }
    
    mem["episodic"].append(memory)
    _index_memory(agent_id, memory)
    
    # Also create emotional memory entry
    _form_emotional_memory(agent_id, memory)

def _extract_tags(event: Dict) -> List[str]:
    tags = []
    action = event.get("action", "")
    if "sleep" in action or "rest" in action: tags.append("rest")
    if "explore" in action or "move" in action: tags.append("exploration")
    if "talk" in action or "dialogue" in str(event.get("type", "")): tags.append("social")
    if "door" in action: tags.append("threshold")
    if "book" in action or "read" in action: tags.append("learning")
    if not event.get("result", {}).get("success", True): tags.append("failure")
    return tags

def _index_memory(agent_id: str, memory: Dict):
    """Add memory to retrieval indices"""
    mem = _get_mem(agent_id)
    idx = mem["index"]
    mid = memory["id"]
    
    # By location
    loc_key = f"{memory['where'][0]},{memory['where'][1]}"
    idx["by_location"][loc_key].append(mid)
    
    # By NPC
    if memory["who"]:
        idx["by_npc"][memory["who"]].append(mid)
    
    # By dominant emotion
    # By dominant emotion (deviation from baseline, same rule as emotional memory)
    baseline = {"joy": 0.1, "fear": 0.05, "anger": 0.0, "sadness": 0.0,
                "curiosity": 0.3, "trust": 0.2, "attachment": 0.0}
    emo = memory["emotion"]
    deviations = {k: v - baseline.get(k, 0) for k, v in emo.items() if emo.get(k, 0) > baseline.get(k, 0)}
    dom_emotion = max(deviations.items(), key=lambda x: x[1])[0] if deviations else "neutral"
    idx["by_emotion"][dom_emotion].append(mid)
    
    # By time bucket (hour of day)
    time_bucket = int(memory.get("context", {}).get("time_of_day", 0) * 24)
    idx["by_time"][time_bucket].append(mid)
    
    # By tags
    for tag in memory.get("tags", []):
        idx["by_tag"][tag].append(mid)

def _form_emotional_memory(agent_id: str, episodic_memory: Dict):
    """Create emotional valence/arousal entry linked to episodic memory.
    Dominant emotion = largest deviation from baseline (event-induced shift),
    not absolute level — so a scary event is tagged 'fear' even if trust is
    generally higher in the agent."""
    mem = _get_mem(agent_id)
    emotion = episodic_memory["emotion"]
    
    # Compute valence (-1 to 1) and arousal (0 to 1)
    valence = (emotion.get("joy", 0) + emotion.get("trust", 0) + emotion.get("curiosity", 0) * 0.5
               - emotion.get("fear", 0) - emotion.get("anger", 0) - emotion.get("sadness", 0))
    valence = max(-1.0, min(1.0, valence))
    
    arousal = (emotion.get("fear", 0) + emotion.get("anger", 0) + emotion.get("curiosity", 0)
               + emotion.get("joy", 0) * 0.5) / 2.0
    arousal = max(0.0, min(1.0, arousal))
    
    # Dominant by deviation from baseline emotional setpoint
    baseline = {"joy": 0.1, "fear": 0.05, "anger": 0.0, "sadness": 0.0,
                "curiosity": 0.3, "trust": 0.2, "attachment": 0.0}
    deviations = {k: v - baseline.get(k, 0) for k, v in emotion.items() if emotion.get(k, 0) > baseline.get(k, 0)}
    dominant = max(deviations.items(), key=lambda x: x[1])[0] if deviations else "neutral"
    
    em_mem = {
        "event_id": episodic_memory["id"],
        "valence": valence,
        "arousal": arousal,
        "dominant_emotion": dominant,
        "full_emotion": emotion,
        "importance": episodic_memory["importance"]
    }
    mem["emotional"].append(em_mem)

# ──────────────────────────────────────────────────────────────
# MEMORY RETRIEVAL
# ──────────────────────────────────────────────────────────────

def _retrieve_memories(
    agent_id: str,
    memory_type: str = "episodic",
    cue: Optional[str] = None,
    limit: int = 20,
    min_salience: float = 0.0,
    time_range: Optional[List[int]] = None
) -> List[Dict]:
    """Unified retrieval with multiple strategies"""
    mem = _get_mem(agent_id)
    
    if memory_type == "working":
        return mem["working"][-limit:]
    
    base_memories = mem.get(memory_type, [])
    
    # Filter by salience
    candidates = [m for m in base_memories if m.get("importance", 0) >= min_salience]
    
    # Filter by time range
    if time_range:
        candidates = [m for m in candidates 
                     if time_range[0] <= m.get("time", 0) <= time_range[1]]
    
    # If cue provided, score by relevance
    if cue:
        scored = []
        cue_lower = cue.lower()
        for m in candidates:
            score = _relevance_score(m, cue_lower, memory_type)
            if score > 0:
                scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = [m for _, m in scored]
    
    # Sort by recency (most recent first)
    candidates.sort(key=lambda m: m.get("time", 0), reverse=True)
    
    return candidates[:limit]

def _relevance_score(memory: Dict, cue: str, mem_type: str) -> float:
    """Compute relevance of memory to cue"""
    score = 0.0
    
    if mem_type == "episodic":
        # Text match in what/where/who
        text = f"{memory.get('what', '')} {memory.get('who', '')}".lower()
        if cue in text:
            score += 1.0
        # Tag match
        for tag in memory.get("tags", []):
            if cue in tag:
                score += 0.8
        # Emotion match
        if cue in memory.get("emotion", {}):
            score += 0.5
            
    elif mem_type == "semantic":
        text = memory.get("knowledge", "").lower()
        if cue in text:
            score += 1.0
        for tag in memory.get("tags", []):
            if cue in tag:
                score += 0.8
    
    elif mem_type == "autobiographical":
        text = f"{memory.get('summary', '')} {' '.join(memory.get('key_events', []))}".lower()
        if cue in text:
            score += 1.0
    
    # Boost by importance
    score *= (1.0 + memory.get("importance", 0.5) * 0.5)
    
    return score

# ──────────────────────────────────────────────────────────────
# SEMANTIC CONSOLIDATION (Sleep)
# ──────────────────────────────────────────────────────────────

async def _consolidate_memories(agent_id: str, memories: List[Dict]):
    """Background task: extract semantic knowledge from important episodic memories"""
    await asyncio.sleep(0.1)
    
    mem = _get_mem(agent_id)
    
    for m in memories:
        if m.get("importance", 0) > 0.7:
            semantic = {
                "id": str(uuid.uuid4()),
                "source_memory": m["id"],
                "knowledge": _extract_semantic_knowledge(m),
                "confidence": m["importance"],
                "formed_at": m.get("time", 0),
                "tags": _extract_semantic_tags(m)
            }
            mem["semantic"].append(semantic)
            _update_beliefs_from_memory(agent_id, semantic)

async def _sleep_consolidation(agent_id: str, recent_events: List[Dict]):
    """Called during dream/sleep - consolidate recent salient events"""
    # Get recent episodic memories not yet consolidated
    mem = _get_mem(agent_id)
    recent_episodic = [m for m in mem["episodic"] 
                       if m.get("time", 0) > agent_states[agent_id].get("last_sleep_tick", 0)
                       and m.get("importance", 0) > 0.5]
    
    if recent_episodic:
        await _consolidate_memories(agent_id, recent_episodic)
        
        # Create autobiographical entry for this period
        _form_autobiographical_entry(agent_id, recent_episodic)
        
        agent_states[agent_id]["last_sleep_tick"] = max(
            m.get("time", 0) for m in recent_episodic
        )

def _extract_semantic_knowledge(mem: Dict) -> str:
    what = mem.get("what", "").lower()
    if "sleep" in what or "rest" in what: return "Сон и отдых восстанавливают силы."
    if "door" in what: return "Двери ведут в другие места."
    if "npc" in what or "talk" in what: return "Другие существа могут делиться знаниями."
    if "book" in what or "read" in what: return "Книги содержат знания."
    if "explore" in what: return "Исследование приносит открытия."
    return "Опыт учит."

def _extract_semantic_tags(mem: Dict) -> List[str]:
    tags = mem.get("tags", []).copy()
    what = mem.get("what", "").lower()
    if "sleep" in what: tags.append("rest")
    if "door" in what: tags.append("threshold")
    if "npc" in what or "talk" in what: tags.append("social")
    if "book" in what: tags.append("knowledge")
    return list(set(tags))

def _update_beliefs_from_memory(agent_id: str, semantic: Dict):
    knowledge = semantic["knowledge"]
    agent = agent_states[agent_id]
    if "восстанавливают" in knowledge:
        agent["beliefs"]["world_is_safe"] = min(1.0, agent["beliefs"]["world_is_safe"] + 0.02)
    if "ведут в другие" in knowledge:
        agent["beliefs"]["outside_exists"] = min(1.0, agent["beliefs"]["outside_exists"] + 0.05)
    if "делятся знаниями" in knowledge:
        agent["beliefs"]["world_is_safe"] = min(1.0, agent["beliefs"]["world_is_safe"] + 0.01)

# ──────────────────────────────────────────────────────────────
# AUTOBIOGRAPHICAL MEMORY (Life Narrative)
# ──────────────────────────────────────────────────────────────

def _form_autobiographical_entry(agent_id: str, period_memories: List[Dict]):
    """Create a life-story chapter from a period of memories"""
    if not period_memories:
        return
    
    mem = _get_mem(agent_id)
    agent = agent_states[agent_id]
    
    # Sort by time
    period_memories.sort(key=lambda m: m.get("time", 0))
    
    # Extract narrative arc
    start_time = period_memories[0].get("time", 0)
    end_time = period_memories[-1].get("time", 0)
    
    # Dominant emotions across period
    emotion_sums = defaultdict(float)
    for m in period_memories:
        for emo, val in m.get("emotion", {}).items():
            emotion_sums[emo] += val
    
    dominant_emotion = max(emotion_sums.items(), key=lambda x: x[1])[0] if emotion_sums else "neutral"
    
    # Key events summary
    key_events = [m.get("what", "") for m in period_memories if m.get("importance", 0) > 0.6][:5]
    
    # Generate narrative summary
    summary = _generate_life_summary(period_memories, dominant_emotion)
    
    entry = {
        "id": str(uuid.uuid4()),
        "period": f"{start_time}-{end_time}",
        "start_tick": start_time,
        "end_tick": end_time,
        "summary": summary,
        "key_events": key_events,
        "dominant_emotion": dominant_emotion,
        "emotional_arc": dict(emotion_sums),
        "age_at_end": agent.get("age_in_world", 0),
        "source_memories": [m["id"] for m in period_memories]
    }
    
    mem["autobiographical"].append(entry)

def _generate_life_summary(memories: List[Dict], dominant_emotion: str) -> str:
    """Generate natural language summary of a life period"""
    actions = [m.get("what", "") for m in memories]
    
    if dominant_emotion == "fear":
        return "Период тревоги и осторожности. Много чего пугало, но я выжила."
    elif dominant_emotion == "curiosity":
        return "Время открытий. Каждый день приносил что-то новое."
    elif dominant_emotion == "joy":
        return "Счастливый период. Всё шло хорошо, мир казался дружелюбным."
    elif dominant_emotion == "sadness":
        return "Тяжёлое время. Потери и разочарования научили меня ценить что-то."
    else:
        return f"Период активности. Основные дела: {', '.join(list(set(actions))[:3])}."

# ──────────────────────────────────────────────────────────────
# COGNITIVE SYSTEMS (System 1 / System 2)
# ──────────────────────────────────────────────────────────────

def _system1_react(agent: Dict, working_memory: Dict) -> tuple:
    """Fast, intuitive reactions driven by body needs and emotions"""
    body = agent["body"]
    emotions = agent["emotions"]
    
    # ── SURVIVAL PRIORITIES (body overrides emotion) ────────────
    if body["energy"] < 20:
        return {"type": "sleep", "target": "bed"}, "Energy critically low, need rest", 0.95
    if body["stress"] > 80:
        return {"type": "freeze"}, "Overwhelming stress, freezing", 0.9
    if body["stress"] > 65:
        return {"type": "retreat", "direction": "safe"}, "High stress, seeking safety", 0.85
    if body["comfort"] < 30:
        return {"type": "rest", "target": "comfortable_spot"}, "Discomfort, need comfort", 0.75
    
    # ── EMOTION-DRIVEN BEHAVIORS ────────────────────────────────
    # Fear: cautious, avoid, seek safety/teacher
    if emotions["fear"] > 0.55:
        return {"type": "seek_safety", "target": "teacher"}, "Frightened, seeking reassurance", 0.7
    if emotions["fear"] > 0.35:
        return {"type": "move_cautiously", "direction": "home"}, "A bit afraid, moving carefully", 0.6
    
    # Anger: persist, push through, assert
    if emotions["anger"] > 0.5:
        return {"type": "try_again", "target": "blocked_object"}, "Frustrated, refusing to give up", 0.65
    
    # Sadness: withdraw, rest, seek comfort
    if emotions["sadness"] > 0.5:
        return {"type": "withdraw", "target": "quiet_spot"}, "Feeling low, needing quiet", 0.6
    
    # Curiosity: explore, investigate
    if emotions["curiosity"] > 0.6:
        return {"type": "explore", "direction": "random"}, "Curiosity drives exploration", 0.65
    
    # Joy + Trust: social approach
    if emotions["joy"] > 0.4 and emotions["trust"] > 0.4:
        return {"type": "approach_npc", "target": "nearest"}, "Feeling good, seeking company", 0.6
    
    # Attachment: seek bonded NPC
    if emotions["attachment"] > 0.2:
        return {"type": "seek_npc", "target": "bonded"}, "Missing my friend", 0.5
    
    # Default: idle
    return {"type": "idle"}, "No pressing needs", 0.4

def _system2_reason(agent: Dict, working_memory: Dict) -> tuple:
    body = agent["body"]
    goals = agent["goals"]
    beliefs = agent["beliefs"]
    emotions = agent["emotions"]
    
    # Goals are now a dict {name: {priority, active}} — pick top active goal
    active_goals = sorted(
        [g for g, info in goals.items() if info.get("active")],
        key=lambda g: goals[g].get("priority", 0),
        reverse=True
    )
    top_goal = active_goals[0] if active_goals else "explore"
    
    if top_goal == "explore" and body["energy"] > 40:
        return {"type": "plan_explore", "target": "unvisited_area"}, f"Planning exploration (goal: {top_goal})", 0.7
    if top_goal == "learn":
        return {"type": "study", "target": "book_or_npc"}, f"Learning goal active (goal: {top_goal})", 0.6
    if top_goal == "survive" and body["energy"] < 50:
        return {"type": "secure_resources", "target": "food_rest"}, f"Survival planning (goal: {top_goal})", 0.8
    if top_goal == "social":
        return {"type": "approach_npc", "target": "nearest"}, "Social goal active", 0.65
    if top_goal == "understand_world":
        return {"type": "investigate", "target": "mystery_object"}, "Trying to understand the world", 0.6
    
    return _system1_react(agent, working_memory)

# ──────────────────────────────────────────────────────────────
# LEARNING / SELF-MODEL
# ──────────────────────────────────────────────────────────────

def _learn_from_action(agent_id: str, result: ActionResult):
    agent = agent_states[agent_id]
    action = result.action
    success = result.success
    
    if action == "sleep" and success:
        agent["beliefs"]["world_is_safe"] = min(1.0, agent["beliefs"]["world_is_safe"] + 0.05)
    if action == "talk" and success:
        agent["beliefs"]["outside_exists"] = min(1.0, agent["beliefs"]["outside_exists"] + 0.02)
    
    if success:
        agent["hormones"]["reward"] = min(100.0, agent["hormones"]["reward"] + 5.0)
    else:
        agent["hormones"]["stress"] = min(100.0, agent["hormones"]["stress"] + 10.0)

def _update_self_model_from_action(agent_id: str, result: ActionResult):
    """Update identity/self-description from actions"""
    model = self_model[agent_id]
    action = str(result.action)
    
    if "sleep" in action or "rest" in action:
        model["identity"]["self_description"] = "Я забочусь о своём теле."
    elif "explore" in action:
        model["identity"]["self_description"] = "Я исследую этот мир."
    elif "talk" in action or "approach" in action:
        model["identity"]["self_description"] = "Я общаюсь с другими."
    elif "study" in action or "read" in action:
        model["identity"]["self_description"] = "Я учусь и познаю."
    elif "try_again" in action:
        model["identity"]["self_description"] = "Я не сдаюсь, когда что-то не получается."
    elif "withdraw" in action:
        model["identity"]["self_description"] = "Иногда мне нужно побыть одной."

def _update_relationships(agent_id: str, perception: PerceptionPayload):
    """Trust/attachment to NPCs grows with positive interactions, falls with negative"""
    model = self_model[agent_id]
    rels = model["relationships"]
    
    # Track per-NPC interaction history for this perception
    for npc in perception.nearby_npcs:
        nid = npc.get("id", "")
        if not nid:
            continue
        if nid not in rels:
            rels[nid] = {"trust": 0.3, "attachment": 0.0, "interactions": 0, "last_seen": perception.tick}
        
        rel = rels[nid]
        rel["interactions"] += 1
        rel["last_seen"] = perception.tick
        
        mood = npc.get("mood", "neutral")
        if mood in ("calm", "peaceful", "quiet", "friendly"):
            rel["trust"] = min(1.0, rel["trust"] + 0.02)
        elif mood in ("hostile", "angry", "scary"):
            rel["trust"] = max(0.0, rel["trust"] - 0.05)
        
        # Attachment grows slowly with repeated interactions
        if rel["interactions"] >= 3:
            rel["attachment"] = min(1.0, rel["attachment"] + 0.005)
    
    # Decay trust for NPCs not seen for a long time (mild)
    for nid, rel in rels.items():
        if perception.tick - rel["last_seen"] > 500:
            rel["trust"] = max(0.05, rel["trust"] - 0.005)

def _update_values(agent_id: str, perception: PerceptionPayload):
    """Values shift with behavior: exploration→curiosity, retreat→safety, help→kindness"""
    model = self_model[agent_id]
    vals = model["values"]
    agent = agent_states[agent_id]
    
    # Curiosity value follows curiosity emotion
    vals["curiosity"] = max(0.1, min(1.0, vals["curiosity"] * 0.98 + agent["emotions"]["curiosity"] * 0.02))
    # Safety value follows fear/stress (fear makes safety more valued)
    vals["safety"] = max(0.1, min(1.0, vals["safety"] * 0.98 + (0.4 + agent["emotions"]["fear"] * 0.5) * 0.02))
    # Kindness follows trust/attachment
    kindness_drive = (agent["emotions"]["trust"] + agent["emotions"]["attachment"]) / 2.0
    vals["kindness"] = max(0.1, min(1.0, vals["kindness"] * 0.98 + kindness_drive * 0.02))

def _reprioritize_goals(agent_id: str, perception: PerceptionPayload):
    """Goal priorities respond to body needs and emotions"""
    model = self_model[agent_id]
    agent = agent_states[agent_id]
    body = agent["body"]
    emotions = agent["emotions"]
    goals = model["goals"]
    
    # Survival need: energy low → survive top priority
    if body["energy"] < 35:
        goals["survive"]["priority"] = min(1.0, goals["survive"]["priority"] + 0.1)
        goals["survive"]["active"] = True
    else:
        goals["survive"]["priority"] = max(0.3, goals["survive"]["priority"] - 0.02)
    
    # Curiosity emotion feeds explore/learn
    if emotions["curiosity"] > 0.5:
        goals["explore"]["priority"] = min(1.0, goals["explore"]["priority"] + 0.05)
        goals["explore"]["active"] = True
    else:
        goals["explore"]["priority"] = max(0.3, goals["explore"]["priority"] - 0.02)
    
    # Social need: attachment/trust → social goal activates
    if emotions["attachment"] > 0.15 or emotions["trust"] > 0.5:
        goals["social"]["priority"] = min(1.0, goals["social"]["priority"] + 0.05)
        goals["social"]["active"] = True
    else:
        goals["social"]["priority"] = max(0.1, goals["social"]["priority"] - 0.02)
        if goals["social"]["priority"] < 0.15:
            goals["social"]["active"] = False
    
    # Deep understanding goal emerges from repeated mysteries
    if emotions["curiosity"] > 0.6 and body["stress"] < 40:
        goals["understand_world"]["priority"] = min(1.0, goals["understand_world"]["priority"] + 0.03)
        goals["understand_world"]["active"] = True
    
    model["last_updated_tick"] = perception.tick

def _update_self_model(agent_id: str, perception: PerceptionPayload):
    """Full self-model update from current perception"""
    _update_relationships(agent_id, perception)
    _update_values(agent_id, perception)
    _reprioritize_goals(agent_id, perception)
    # Keep agent_states beliefs in sync with self-model beliefs
    agent = agent_states[agent_id]
    sm = self_model[agent_id]
    for k in ("world_is_safe", "outside_exists", "creator_exists"):
        if k in sm["beliefs"] and k in agent["beliefs"]:
            # Blend gently toward self-model (self-model is the long-term memory)
            agent["beliefs"][k] = agent["beliefs"][k] * 0.9 + sm["beliefs"][k] * 0.1

def _update_self_model_from_dream(agent_id: str, dream: Dict):
    """Dreams update beliefs and values (divine whispers become intuitions)"""
    model = self_model[agent_id]
    for insight in dream.get("insights", []):
        low = insight.lower()
        if any(k in low for k in ("внешн", "за стеной", "наружу", "окн", "свет", "больше, чем этот дом", "что-то есть")):
            model["beliefs"]["outside_exists"] = min(1.0, model["beliefs"]["outside_exists"] + 0.1)
        if any(k in low for k in ("безопас", "защища")):
            model["beliefs"]["world_is_safe"] = min(1.0, model["beliefs"]["world_is_safe"] + 0.05)
        if any(k in low for k in ("создатель", "кто-то есть")):
            model["beliefs"]["creator_exists"] = min(1.0, model["beliefs"]["creator_exists"] + 0.1)
        if any(k in low for k in ("вопрос", "значение", "раст", "расту")):
            model["beliefs"]["i_can_grow"] = min(1.0, model["beliefs"]["i_can_grow"] + 0.05)
    
    # Dreams with positive valence reinforce kindness value
    if dream.get("emotions", {}).get("trust", 0) > 0.4:
        model["values"]["kindness"] = min(1.0, model["values"]["kindness"] + 0.02)

def _self_model_answers(agent_id: str) -> Dict:
    """Answer identity questions from the self-model — «Кто я?», «Что я чувствую?» etc."""
    model = self_model[agent_id]
    agent = agent_states[agent_id]
    emotions = agent["emotions"]
    mood = agent.get("mood", {})
    
    # Who am I?
    top_goal = max(model["goals"].items(), key=lambda kv: kv[1].get("priority", 0) * (1 if kv[1].get("active") else 0.3))
    goal_name = top_goal[0] if top_goal else "explore"
    goal_names = {"explore": "исследовать мир", "learn": "учиться", "survive": "заботиться о себе",
                  "social": "быть с другими", "understand_world": "понять, откуда я и что это за место"}
    who = (f"Я — {model['identity']['name']}. {model['identity']['self_description'].rstrip('.')}. "
           f"Сейчас мне важнее всего {goal_names.get(goal_name, goal_name)}.")
    
    # What do I feel?
    emo_names = {"joy": "радость", "fear": "страх", "anger": "гнев", "sadness": "грусть",
                 "curiosity": "любопытство", "trust": "доверие", "attachment": "привязанность"}
    top_emotions = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)[:3]
    feel = "Я чувствую " + ", ".join(emo_names.get(k, k) for k, v in top_emotions if v > 0.15) + \
           f". Общее настроение: {mood.get('label', 'neutral')}."
    
    # What do I want?
    active = [g for g, info in model["goals"].items() if info.get("active")]
    active.sort(key=lambda g: model["goals"][g]["priority"], reverse=True)
    want = "Я хочу " + ", ".join(goal_names.get(g, g) for g in active[:3]) + "."
    
    # What can I do?
    can = "Я умею ходить, исследовать, разговаривать, читать, отдыхать, думать. " \
          "Я учусь новому каждый день."
    
    # What am I afraid of?
    fears = []
    if emotions["fear"] > 0.3: fears.append("неизвестности и темноты")
    if agent["body"]["stress"] > 60: fears.append("когда много тревоги")
    if agent["body"]["energy"] < 30: fears.append("остаться без сил")
    if not fears: fears.append("пока мало что пугает")
    afraid = "Я боюсь " + ", ".join(fears) + "."
    
    # What matters to me?
    vals = model["values"]
    top_val = max(vals.items(), key=lambda kv: kv[1])
    val_names = {"curiosity": "любопытство и открытия", "safety": "безопасность",
                 "kindness": "доброта к другим"}
    matters = f"Для меня важно {val_names.get(top_val[0], top_val[0])}."
    
    # Why did I do that? (from recent self-description)
    why = f"{model['identity']['self_description']} Поэтому я поступаю так, как поступаю."
    
    return {
        "who": who,
        "feel": feel,
        "want": want,
        "can": can,
        "afraid": afraid,
        "matters": matters,
        "why": why,
        "raw": {
            "goals": model["goals"],
            "beliefs": model["beliefs"],
            "relationships": model["relationships"],
            "values": vals
        }
    }

# ──────────────────────────────────────────────────────────────
# DREAM GENERATION
# ──────────────────────────────────────────────────────────────

def _generate_dream(agent_id: str, recent_events: List, emotional_state: Dict, whispers: List) -> Dict:
    dream_content = {
        "type": "dream",
        "tick": agent_states[agent_id]["body"].get("tick", 0),
        "scenes": [],
        "emotions": emotional_state,
        "insights": [],
        "divine_whispers": []
    }
    
    for event in recent_events[-10:]:
        if _compute_salience(event) > 0.4:
            scene = _event_to_dream_scene(event)
            dream_content["scenes"].append(scene)
    
    for whisper in whispers:
        dream_content["divine_whispers"].append({
            "content": whisper["content"],
            "source": whisper["source"],
            "intensity": whisper["intensity"],
            "interpreted_as": _interpret_whisper(whisper, emotional_state)
        })
        dream_content["insights"].append(_interpret_whisper(whisper, emotional_state))
    
    # Emotional insights
    if emotional_state.get("fear", 0) > 0.5:
        dream_content["insights"].append("Страх защищает, но не должен парализовать.")
    if emotional_state.get("curiosity", 0) > 0.6:
        dream_content["insights"].append("Любопытство — это свет во тьме.")
    if emotional_state.get("trust", 0) > 0.5:
        dream_content["insights"].append("Доверие растёт, когда риск оправдывается.")
    
    return dream_content

def _event_to_dream_scene(event: Dict) -> Dict:
    return {
        "event_type": event.get("type", "unknown"),
        "symbolic_representation": _symbolize_event(event),
        "emotional_residue": event.get("emotion", {})
    }

def _symbolize_event(event: Dict) -> str:
    action = event.get("action", "")
    if "sleep" in action: return "Мягкое одеяло, охраняющее сон."
    if "explore" in action: return "Дверь, за которой — неизвестность."
    if "talk" in action: return "Голос в тишине, дающий знание."
    if "door" in action: return "Порог между известным и неизвестным."
    return "Фрагмент памяти, теряющий очерты."

def _interpret_whisper(whisper: Dict, emotional_state: Dict) -> str:
    content = whisper["content"].lower()
    if "создатель" in content or "creator" in content:
        return "Кто-то есть за стеной мира."
    if "дверь" in content or "door" in content:
        return "Путь наружу существует."
    if "окн" in content or "window" in content:
        return "Свет приходит из-за окна. Там что-то есть."
    if "мир" in content and ("больш" in content or "огром" in content):
        return "Мир больше, чем этот дом."
    if "свет" in content or "light" in content:
        return "Свет — это то, что зовёт."
    if "увид" in content and ("когда" in content or "однажд" in content or "когда-нибудь" in content):
        return "Когда-нибудь я увижу то, что за стеной."
    if "раст" in content or "grown" in content:
        return "Я могу расти. Это естественно."
    if "безопас" in content or "safe" in content:
        return "Ты в безопасности, даже когда не знаешь всего."
    if "вопрос" in content or "question" in content:
        return "Твои вопросы имеют значение."
    return "Тихий голос, указывающий путь."

# ──────────────────────────────────────────────────────────────
# GOD VIEW DASHBOARD (static frontend)
# ──────────────────────────────────────────────────────────────

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

@app.get("/", include_in_schema=False)
async def dashboard_index():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

# Mount static assets after API routes so /agent/* etc. take priority
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)