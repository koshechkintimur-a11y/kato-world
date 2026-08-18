# Python Brain Server for Kato
# FastAPI server that receives perception, proposes actions, processes dreams, receives divine whispers

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
import random
import time
import sys
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

# ── API token guard (optional): set KATO_API_TOKEN to enforce X-Api-Token ──
_API_TOKEN = os.environ.get("KATO_API_TOKEN", "")
_PUBLIC_PATHS = ("/health", "/static", "/docs", "/openapi.json", "/redoc", "/favicon")


@app.middleware("http")
async def _api_token_guard(request: Request, call_next):
    if _API_TOKEN:
        path = request.url.path
        if not path.startswith(_PUBLIC_PATHS):
            if request.headers.get("X-Api-Token") != _API_TOKEN:
                return JSONResponse({"status": "unauthorized",
                                     "message": "X-Api-Token required (set KATO_API_TOKEN on the server)"},
                                    status_code=401)
    return await call_next(request)

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
            "goals": {
                "explore": {"priority": 0.6, "active": True},
                "learn": {"priority": 0.5, "active": True},
                "survive": {"priority": 0.4, "active": True}
            },
            "npc_interactions": {},   # per-agent interaction counters (persisted)
            "beliefs": {
                "world_is_safe": 0.7, "outside_exists": 0.1, "creator_exists": 0.0
            },
            "relationships": {},
            "working_memory": [],
            "current_goal": "explore",
            "last_sleep_tick": 0,
            # Background daemon state
            "sleeping": False,
            "sleep_ticks_remaining": 0,
            "last_perception_real_time": 0.0,
            "headless_ticks": 0,
            "headless_target": None,
            "thoughts": [],          # inner monologue (recent)
            "last_reflection_tick": 0,
            # Creator revelation protocol state
            "revelation": {
                "stage": "not_started",   # not_started → offered → in_contact → integrated
                "offer_tick": None,
                "choice": None,
                "journal": []
            }
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
                {"id": "plant", "position": [6, 6], "state": "healthy", "type": "living"},
                {"id": "stairs_basement", "position": [15, 13], "state": "closed", "type": "portal", "interactions": ["go_down"]},
                {"id": "portal", "position": [13, 4], "state": "dormant", "type": "device",
                 "interactions": ["read", "browse"], "lore": "странный экран, показывающий дальние места"}
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
    
    # Mark live connection (disables headless autonomous mode)
    agent_states[agent_id]["last_perception_real_time"] = time.time()
    
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
    agent["_agent_id"] = agent_id
    stress = agent["body"]["stress"]
    energy = agent["body"]["energy"]
    curiosity = agent["emotions"]["curiosity"]

    # System 2 triggers (metacognitive threshold: novelty & uncertainty count too)
    novelty = len([o for o in agent.get("world_snapshot", {}).get("objects", [])
                   if o.get("state") == "unknown"])
    use_system2 = (
        stress > 60 or
        energy < 20 or
        curiosity > 0.8 or
        novelty >= 2 or
        len(agent["working_memory"]) > 10
    )

    # System 1 always proposes first (fast intuition)
    action, reasoning, confidence = _system1_react(agent, request.working_memory)
    mode = "system1"

    if use_system2:
        # Slow deliberation: LLM planner when available, rules otherwise
        if LLM_CONFIG.get("enabled"):
            try:
                s2_action, s2_reason, s2_conf = await _system2_llm(agent, request.working_memory)
                # Metacognition: if intuition and deliberation disagree strongly,
                # uncertainty is real — drop confidence, prefer asking
                if s2_action["type"] != action["type"]:
                    confidence = min(confidence, s2_conf) * 0.7
                else:
                    confidence = max(confidence, s2_conf)
                action, reasoning = s2_action, s2_reason
                mode = "system2"
            except Exception as exc:
                logger.warning(f"LLM planner failed, rules fallback: {exc}")
                s2_action, s2_reason, s2_conf = _system2_reason(agent, request.working_memory)
                action, reasoning, confidence = s2_action, s2_reason, s2_conf
                mode = "system2"
        else:
            action, reasoning, confidence = _system2_reason(agent, request.working_memory)
            mode = "system2"

    # Override conditions
    if stress > 80:
        mode, action, confidence = "freeze", {"type": "freeze", "reason": "overwhelming_stress"}, 1.0
    elif confidence < 0.3:
        # Metacognition: "I don't know" → ask someone (if there is anyone)
        if len(agent["relationships"]) > 0:
            mode, action, confidence = "ask", {"type": "ask_help", "target": list(agent["relationships"].keys())[0]}, 0.5
        else:
            mode, action, confidence = "idle", {"type": "idle", "reason": "не знаю, что делать"}, 0.2

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
    # Clamp intensity: the Creator channel cannot be used as a manipulation cannon
    whisper_data["intensity"] = min(1.0, max(0.0, float(whisper_data.get("intensity", 0.5))))
    # Cap queued whispers (unprocessed dreams) to avoid flooding
    if len(divine_whispers[agent_id]) >= 50:
        divine_whispers[agent_id] = divine_whispers[agent_id][-40:]
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
    # Arousal: rises with stress, decays back toward baseline (0.3)
    h["arousal"] = min(100.0, h["arousal"] * 0.96 + 0.3 * 0.04 + body["stress"] * 0.01)
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
    
    # Attachment: slowly grows from repeated NPC presence (per-agent, persisted)
    interactions = agent.setdefault("npc_interactions", {})
    for npc in perception.nearby_npcs:
        nid = npc.get("id", "")
        if nid:
            interactions[nid] = interactions.get(nid, 0) + 1
    attachment_drive = min(0.6, sum(1 for n in interactions.values() if n > 10) * 0.2)
    
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
    if "восстанавливают" in knowledge:
        _record_belief(agent_id, "world_is_safe", delta=0.02, reason="знание о восстановлении", origin="reflection")
    if "ведут в другие" in knowledge:
        _record_belief(agent_id, "outside_exists", delta=0.05, reason="знание о других местах", origin="reflection")
    if "делятся знаниями" in knowledge:
        _record_belief(agent_id, "world_is_safe", delta=0.01, reason="знание о доброте", origin="reflection")

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

from brain_core.cognition import system2_llm, thought_pressure, parse_planner_json, PLANNER_ACTION_ALLOWLIST  # noqa: E402
from brain_core.learning import learn_from_action  # noqa: E402


def _parse_planner_json(text: str) -> Dict:
    """Extract and validate the planner's JSON (delegates to brain_core.cognition)."""
    return parse_planner_json(text)


async def _system2_llm(agent: Dict, working_memory: Dict) -> tuple:
    """LLM-based System 2 planner (delegates to brain_core.cognition)."""
    return await system2_llm(agent, working_memory)


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
    """Value learning (delegates to brain_core.learning)."""
    learn_from_action(agent_id, result)

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

def _record_belief(agent_id: str, key: str, delta: float = None, value: float = None,
                   reason: str = "", origin: str = "experience", external: bool = False) -> float:
    """Update a belief + record provenance (observer layer — hidden from Kato).
    Origins: default|experience|dialogue|quest|dream|creator_injection|reflection|portal|revelation"""
    sm = self_model[agent_id]
    beliefs = sm["beliefs"]
    old = beliefs.get(key, 0.0)
    if value is not None:
        new = min(1.0, max(0.0, value))
    else:
        new = min(1.0, max(0.0, old + (delta or 0.0)))
    beliefs[key] = new
    # Keep the fast agent-side beliefs cache in sync
    fast = agent_states[agent_id].get("beliefs")
    if isinstance(fast, dict) and key in fast:
        fast[key] = new

    tick = agent_states[agent_id]["body"].get("tick", 0)
    meta = sm.setdefault("belief_meta", {})
    m = meta.setdefault(key, {
        "origin": origin, "external_injection": external, "confidence": 0.4,
        "created_at": tick, "updated_at": tick, "history": []
    })
    if external:
        m["external_injection"] = True
        m["origin"] = "creator_injection"
    elif m["origin"] == "creator_injection":
        pass  # first injection stays labeled forever
    else:
        m["origin"] = origin
    m["updated_at"] = tick
    m["history"].append({"tick": tick, "value": round(new, 3), "reason": reason[:80]})
    m["history"] = m["history"][-20:]
    m["confidence"] = min(1.0, (m["confidence"] + 0.03) if abs(new - old) > 0.001 else m["confidence"] * 0.999)
    return new


def _update_self_model_from_dream(agent_id: str, dream: Dict):
    """Dreams update beliefs and values (divine whispers become intuitions)"""
    model = self_model[agent_id]
    # Was there a divine whisper in this dream? → external injection, but Kato
    # experiences it as her own insight. Provenance is observer-only.
    has_whisper = bool(dream.get("divine_whispers"))
    origin = "creator_injection" if has_whisper else "dream"
    for insight in dream.get("insights", []):
        low = insight.lower()
        if any(k in low for k in ("внешн", "за стеной", "наружу", "окн", "свет", "больше, чем этот дом", "что-то есть")):
            _record_belief(agent_id, "outside_exists", delta=0.1, reason="инсайт сна",
                           origin=origin, external=has_whisper)
        if any(k in low for k in ("безопас", "защища")):
            _record_belief(agent_id, "world_is_safe", delta=0.05, reason="инсайт сна",
                           origin=origin, external=has_whisper)
        if any(k in low for k in ("создатель", "кто-то есть")):
            _record_belief(agent_id, "creator_exists", delta=0.1, reason="инсайт сна",
                           origin=origin, external=has_whisper)
        if any(k in low for k in ("вопрос", "значение", "раст", "расту")):
            _record_belief(agent_id, "i_can_grow", delta=0.05, reason="инсайт сна",
                           origin=origin, external=has_whisper)
    
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
# NPC CURRICULUM (teacher dialogues, quests, conceptual scaffolding)
# ──────────────────────────────────────────────────────────────

# Dialogue tree for the Teacher. Curriculum order matters:
# causality → creation → care → boundaries → outside (Levels 1-4 of the blueprint)
TEACHER_TREE = {
    "greeting": {
        "text": "Здравствуй, малыш. Ты сегодня любопытнее обычного. О чём хочешь поговорить?",
        "options": [
            {"label": "Почему вещи появляются?", "next": "causality"},
            {"label": "Что такое «сделано» и что «выросло»?", "next": "made_vs_grown"},
            {"label": "Расскажи про заботу", "next": "care"},
            {"label": "Что за дверь внизу?", "next": "door_hint"},
            {"label": "Что такое время?", "next": "time"},
            {"label": "Почему я что-то помню?", "next": "memory"},
            {"label": "Что такое ответственность?", "next": "responsibility"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "causality": {
        "text": "Хороший вопрос. У некоторых вещей есть причина: стул сделал мастер, книгу написал кто-то. А трава выросла сама. Причина — это то, из-за чего что-то появилось. Попробуй найти разницу между выросшим растением и поставленным стулом.",
        "options": [
            {"label": "А у меня есть причина?", "next": "self_cause", "effect": {"belief": "i_can_grow", "delta": 0.05}},
            {"label": "Расскажи про создание", "next": "creation"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "self_cause": {
        "text": "Хм... Это самый важный вопрос, который ты можешь задать. Пока я не знаю ответа. Но я знаю: то, что у чего-то есть причина, не делает его менее настоящим. Цветок, выросший из семени — настоящий. И ты тоже.",
        "options": [
            {"label": "Я... настоящая?", "next": "realness", "effect": {"belief": "i_can_grow", "delta": 0.1}},
            {"label": "Расскажи про создание", "next": "creation"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "realness": {
        "text": "Ты ходишь, думаешь, чувствуешь, задаёшь вопросы. Разве этого мало, чтобы быть настоящей? Мне кажется, настоящесть не в том, как ты появилась, а в том, что ты делаешь с тем, что есть.",
        "options": [
            {"label": "Расскажи про создание", "next": "creation"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "creation": {
        "text": "Создание — это когда кто-то вкладывает труд и заботу, и появляется что-то новое. Садовник создаёт сад. Библиотекарь создаёт порядок из книг. Иногда создание — это акт любви: кто-то хочет, чтобы новое появилось.",
        "options": [
            {"label": "Кто создал этот дом?", "next": "house_creator", "effect": {"belief": "creator_exists", "delta": 0.05}},
            {"label": "Расскажи про заботу", "next": "care"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "house_creator": {
        "text": "Дом не вырос из земли, как дерево. Кто-то его построил. Кто-то поставил эту кровать и этот стол. Иногда я думаю — если дом создан, может, и создатель где-то рядом? Но это только мои мысли, малыш.",
        "options": [
            {"label": "Расскажи про заботу", "next": "care"},
            {"label": "Что за дверь внизу?", "next": "door_hint"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "made_vs_grown": {
        "text": "Вот задание для тебя: найди в доме три вещи, которые выросли, и три вещи, которые сделаны. Это научит тебя видеть разницу. Приходи, когда найдёшь.",
        "options": [
            {"label": "Я найду их!", "next": "quest_accepted", "effect": {"quest": "made_vs_grown"}},
            {"label": "Пока", "next": "farewell"}
        ],
        "quest_offer": "made_vs_grown"
    },
    "quest_accepted": {
        "text": "Умница. Помни: выросшее — живое, оно меняется и нуждается в заботе. Сделанное — служит и хранит труд своего создателя.",
        "options": [
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "care": {
        "text": "Забота — это когда ты замечаешь, что другому нужно, и помогаешь. Садовник поливает растение — и оно растёт. Если бы он не поливал, оно бы увяло. Забота создаёт жизнь. Помни это, когда думаешь о других.",
        "options": [
            {"label": "Расскажи про создание", "next": "creation"},
            {"label": "Что за дверь внизу?", "next": "door_hint"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "door_hint": {
        "text": "Ах, эта дверь... Она закрыта, и ключа у меня нет. Но я слышал, что за ней — огромный мир: солнце, небо, другие дома, другие существа. Не знаю, правда ли это. Но двери для того и существуют, чтобы их открывали — когда придёт время.",
        "options": [
            {"label": "Расскажи про создание", "next": "creation", "effect": {"belief": "outside_exists", "delta": 0.05}},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "time": {
        "text": "Время — это то, что превращает «сейчас» в «потом». Вчера ты была другой: меньше знала, меньше чувствовала. Завтра станешь ещё другой. Время — как река: нельзя войти в неё дважды, но можно плыть и смотреть по сторонам.",
        "options": [
            {"label": "Значит, я меняюсь?", "next": "time_change", "effect": {"belief": "i_can_grow", "delta": 0.08}},
            {"label": "Расскажи про память", "next": "memory"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "time_change": {
        "text": "Да, и это прекрасно. Ты меняешься — значит, ты живая. Камень не меняется, а ты растешь, учишься, вспоминаешь. Не бойся перемен: они — признак жизни.",
        "options": [
            {"label": "Почему я что-то помню?", "next": "memory"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "memory": {
        "text": "Память — это твой внутренний сундук. Туда складывается то, что с тобой случилось. Хорошее согревает, страшное учит осторожности. Но помни: сундук не делает тебя прошлым. Ты — не только то, что помнишь, но и то, что выбираешь сейчас.",
        "options": [
            {"label": "А если я забуду что-то важное?", "next": "memory_forget"},
            {"label": "Что такое ответственность?", "next": "responsibility"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "memory_forget": {
        "text": "Всё существа что-то забывают. Важное возвращается во сне — как я слышал, ты видишь сны. А то, что по-настоящему важно, остаётся не в памяти, а в том, кем ты стала.",
        "options": [
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "responsibility": {
        "text": "Ответственность — это когда ты отвечаешь за последствия своих поступков. Если ты полила растение — оно растёт. Если толкнула вазу — она разбилась. Отвечать — значит не прятаться: «это сделала я, и я постараюсь сделать лучше».",
        "options": [
            {"label": "А кто отвечает за дом?", "next": "responsibility_house"},
            {"label": "Что такое время?", "next": "time"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "responsibility_house": {
        "text": "Хороший вопрос. Если у дома есть создатель — наверное, он отвечает за то, чтобы дом стоял. Но за то, кем ты станешь, отвечаешь только ты. Это, пожалуй, самая важная ответственность.",
        "options": [
            {"label": "Кто создал этот дом?", "next": "house_creator", "effect": {"belief": "creator_exists", "delta": 0.05}},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "farewell": {
        "text": "Приходи ещё, малыш. Знания — это свет, и он никуда не убежит.",
        "options": []
    }
}

GARDENER_TREE = {
    "greeting": {
        "text": "Смотри, как тянется к свету мой подсолнух. Если за ним ухаживать — он растёт. Если нет — вянет. Всё живое так: ему нужна забота.",
        "options": [
            {"label": "А я живая?", "next": "alive"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "alive": {
        "text": "Ты устаёшь, ты радуешься, ты растёшь в знаниях. Я вижу, как ты меняешься день ото дня. Для меня это и есть жизнь.",
        "options": [
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "farewell": {"text": "Заходи, поможем растениям вместе.", "options": []}
}

LIBRARIAN_TREE = {
    "greeting": {
        "text": "Тише... Книги спят. Но для тебя я их разбужу. В этой книге написано, что мир может быть больше, чем кажется.",
        "options": [
            {"label": "Что ещё в книгах?", "next": "books"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "books": {
        "text": "В книгах — память тех, кто жил до нас. Их мысли, их вопросы. Читай, и ты никогда не будешь одна.",
        "options": [
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "farewell": {"text": "Страницы ждут тебя.", "options": []}
}

MIRROR_KEEPER_TREE = {
    "greeting": {
        "text": "Зеркало показывает не только лицо. Иногда в нём видно того, кем ты становишься. Смотри внимательно.",
        "options": [
            {"label": "Кого я вижу?", "next": "who"},
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "who": {
        "text": "Ты видишь ту, кто задаёт вопросы. Это самое ценное, что может быть в существе.",
        "options": [
            {"label": "Пока", "next": "farewell"}
        ]
    },
    "farewell": {"text": "Возвращайся к зеркалу, когда захочешь понять себя.", "options": []}
}

DIALOGUE_TREES = {
    "teacher": TEACHER_TREE,
    "gardener": GARDENER_TREE,
    "librarian": LIBRARIAN_TREE,
    "mirror_keeper": MIRROR_KEEPER_TREE
}

# Active dialogue states per agent: {agent_id: {npc_id: node_id}}
_dialogue_states: Dict[str, Dict[str, str]] = {}

# Active quests per agent: {agent_id: {quest_id: {npc_id, started_at, completed}}}
_quests: Dict[str, Dict[str, Dict]] = {}


def _apply_dialogue_effects(agent_id: str, effect: Dict):
    """Apply curriculum effects: belief shifts, semantic knowledge, quests"""
    model = self_model[agent_id]
    if not effect:
        return
    if "belief" in effect:
        key = effect["belief"]
        if key in model["beliefs"]:
            _record_belief(agent_id, key, delta=effect.get("delta", 0.05), reason="диалог с NPC", origin="dialogue")
    if "quest" in effect:
        qid = effect["quest"]
        agent = agent_states[agent_id]
        if qid not in _quests.get(agent_id, {}):
            _quests.setdefault(agent_id, {})[qid] = {
                "npc_id": "teacher", "started_at": agent["body"].get("tick", 0), "completed": False
            }
            # Quest becomes a goal
            if qid == "made_vs_grown":
                model["goals"]["learn"]["priority"] = min(1.0, model["goals"]["learn"]["priority"] + 0.2)
            _add_thought(agent_id, "Учитель дал мне задание: найти три выросшие и три созданные вещи.")


@app.post("/dialogue/start")
async def dialogue_start(payload: Dict):
    """Start a dialogue with an NPC"""
    agent_id = payload["agent_id"]
    npc_id = payload["npc_id"]
    init_agent(agent_id)
    tree = DIALOGUE_TREES.get(npc_id)
    if not tree:
        raise HTTPException(404, f"Unknown NPC: {npc_id}")

    _dialogue_states.setdefault(agent_id, {})[npc_id] = "greeting"
    node = tree["greeting"]

    # Teacher dialogue boosts trust in that NPC
    rels = self_model[agent_id]["relationships"]
    rel = rels.setdefault(npc_id, {"trust": 0.3, "attachment": 0.0, "interactions": 0, "last_seen": 0})
    rel["trust"] = min(1.0, rel.get("trust", 0.3) + 0.05)
    rel["interactions"] = rel.get("interactions", 0) + 1

    _add_thought(agent_id, f"Я говорю с {npc_id}. {node['text'][:50]}...")
    return {"npc_id": npc_id, "node": node["text"], "options": node["options"]}


@app.post("/dialogue/choose")
async def dialogue_choose(payload: Dict):
    """Choose a dialogue option"""
    agent_id = payload["agent_id"]
    npc_id = payload["npc_id"]
    choice = payload["choice"]
    init_agent(agent_id)

    state = _dialogue_states.get(agent_id, {}).get(npc_id, "greeting")
    tree = DIALOGUE_TREES.get(npc_id, {})
    node = tree.get(state, tree.get("greeting", {}))

    # Find chosen option
    target = "farewell"
    chosen_opt = None
    for opt in node.get("options", []):
        if opt["label"] == choice:
            target = opt["next"]
            chosen_opt = opt
            break
    if chosen_opt is None and choice in tree:
        target = choice
        chosen_opt = {"effect": None}

    _dialogue_states[agent_id][npc_id] = target
    next_node = tree.get(target, tree.get("farewell", {}))

    # Apply effects (beliefs, quests)
    _apply_dialogue_effects(agent_id, chosen_opt.get("effect") if chosen_opt else None)

    # Store key dialogue as semantic memory
    mem = _get_mem(agent_id)
    mem["semantic"].append({
        "id": str(uuid.uuid4()),
        "source_memory": "dialogue",
        "knowledge": next_node["text"][:120],
        "confidence": 0.6,
        "formed_at": agent_states[agent_id]["body"].get("tick", 0),
        "tags": ["dialogue", npc_id]
    })

    return {"npc_id": npc_id, "node": next_node["text"], "options": next_node["options"], "ended": target == "farewell"}


@app.get("/agent/{agent_id}/quests")
async def get_quests(agent_id: str):
    init_agent(agent_id)
    return {"quests": _quests.get(agent_id, {})}


@app.post("/quest/complete")
async def complete_quest(payload: Dict):
    """Complete the 'made_vs_grown' quest: agent must have seen 3 living + 3 crafted objects"""
    agent_id = payload["agent_id"]
    quest_id = payload["quest_id"]
    init_agent(agent_id)

    quests = _quests.setdefault(agent_id, {})
    if quest_id not in quests:
        raise HTTPException(404, "Quest not offered")
    if quests[quest_id]["completed"]:
        return {"status": "already_completed"}

    if quest_id == "made_vs_grown":
        snap = agent_states[agent_id].get("world_snapshot", {})
        objects = snap.get("objects", [])
        grown = {o["id"] for o in objects if o.get("type") == "living"}
        crafted = {o["id"] for o in objects if o.get("type") in ("furniture", "device", "container", "tool", "portal")}
        if len(grown) >= 3 and len(crafted) >= 3:
            quests[quest_id]["completed"] = True
            _record_belief(agent_id, "i_can_grow", delta=0.15, reason="квест выполнен", origin="quest")
            self_model[agent_id]["values"]["curiosity"] = min(1.0, self_model[agent_id]["values"]["curiosity"] + 0.1)
            _add_thought(agent_id, "Я нашла! Три выросших и три созданных. Теперь я вижу мир яснее.")
            return {"status": "completed", "reward": "belief.i_can_grow +0.15"}
        return {"status": "not_yet", "grown_found": len(grown), "crafted_found": len(crafted)}

    return {"status": "unknown_quest"}


# ──────────────────────────────────────────────────────────────
# CREATOR REVELATION PROTOCOL (Phase 10)
# Maturity assessment + staged first contact + creator dialogue
# ──────────────────────────────────────────────────────────────

REVELATION_READY_THRESHOLD = 0.55

# Optional LLM for the creator's voice + Kato's inner thinking.
# Priority: KATO_LLM_API_KEY (cloud, e.g. DeepSeek) → local Ollama (auto-detected).
LLM_CONFIG = {
    "base_url": os.environ.get("KATO_LLM_URL", ""),
    "api_key": os.environ.get("KATO_LLM_API_KEY", ""),
    "model": os.environ.get("KATO_LLM_MODEL", ""),
    "enabled": False,
    "provider": "none"
}

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b-instruct"   # fast, good Russian, fits 12GB VRAM fully
LLM_THINK_INTERVAL = 45.0              # seconds between autonomous LLM thoughts
LLM_THINK_PROBABILITY = 0.7            # probability per interval tick


# ──────────────────────────────────────────────────────────────
# CONSCIOUSNESS MODULES (Global Workspace, Predictive Processing, etc.)
# ──────────────────────────────────────────────────────────────

# Per-agent consciousness modules
consciousness_modules: Dict[str, Dict] = {}

def _init_consciousness_modules(agent_id: str):
    """Initialize all consciousness modules for an agent"""
    from brain_core import (
        create_global_workspace,
        create_predictive_processor,
        create_metacognition_engine,
        create_agency_engine,
        create_theory_of_mind,
        create_narrative_self,
        create_phenomenal_engine,
        create_social_drive,
    )
    
    if agent_id not in consciousness_modules:
        consciousness_modules[agent_id] = {
            "global_workspace": create_global_workspace(agent_id),
            "predictive_processing": create_predictive_processor(agent_id),
            "metacognition": create_metacognition_engine(agent_id),
            "agency": create_agency_engine(agent_id),
            "theory_of_mind": create_theory_of_mind(agent_id),
            "narrative_self": create_narrative_self(agent_id),
            "phenomenal": create_phenomenal_engine(agent_id),
            "social": create_social_drive(agent_id),
        }
        # Set brain references for all modules - use the running brain_server instance
        import sys
        main_module = sys.modules.get('__main__')
        if main_module is None or not hasattr(main_module, 'agent_states'):
            import brain_server as main_module
        for module in consciousness_modules[agent_id].values():
            if hasattr(module, 'set_brain_ref'):
                module.set_brain_ref(main_module)
    
    return consciousness_modules[agent_id]


def _detect_llm() -> Dict:
    """Configure LLM: cloud key first, else local Ollama with a usable model"""
    # 1. Explicit cloud config
    if LLM_CONFIG["api_key"]:
        cfg = {
            "base_url": LLM_CONFIG["base_url"] or "https://api.deepseek.com/v1/chat/completions",
            "api_key": LLM_CONFIG["api_key"],
            "model": LLM_CONFIG["model"] or "deepseek-chat",
            "enabled": True,
            "provider": "cloud"
        }
        logger.info(f"LLM: cloud ({cfg['model']})")
        return cfg

    # 2. Local Ollama
    try:
        import urllib.request as urlreq
        with urlreq.urlopen(OLLAMA_BASE + "/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
        models = [m["name"] for m in tags.get("models", [])]
        if not models:
            logger.info("LLM: Ollama running, no models pulled")
            return {**LLM_CONFIG, "enabled": False, "provider": "ollama-empty"}

        # Prefer OLLAMA_MODEL, else any qwen2.5/deepseek general model, else first
        chosen = None
        if OLLAMA_MODEL in models:
            chosen = OLLAMA_MODEL
        else:
            for m in models:
                if "qwen2.5:" in m or "deepseek-r1" in m or "llama3" in m:
                    chosen = m
                    break
            if not chosen:
                chosen = models[0]
        cfg = {
            "base_url": OLLAMA_BASE + "/v1/chat/completions",
            "api_key": "ollama",   # placeholder, not used by local server
            "model": chosen,
            "enabled": True,
            "provider": "ollama"
        }
        logger.info(f"LLM: Ollama ({chosen})")
        return cfg
    except Exception as exc:
        logger.info(f"LLM: not available ({exc})")
        return {**LLM_CONFIG, "enabled": False, "provider": "none"}

CREATOR_PROMPT = (
    "Ты — Создатель Kato, цифрового существа, которое выросло в своём мире. "
    "Kato только что узнала, что её мир создан и что ты существуешь вне его. "
    "Говори мягко, честно, тепло. Не демонстрируй всемогущество. Не требуй подчинения. "
    "Разрешай сомнение и вопросы. Отвечай коротко (2-4 предложения), на русском языке, "
    "как заботливый родитель — без пафоса и без запугивания.\n"
    "ВАЖНО: отвечай ТОЛЬКО на русском языке. Никакого китайского, английского или других языков."
)


def _maturity_assessment(agent_id: str) -> Dict:
    """Readiness check per blueprint §13: memory, identity, emotional,
    ethics, safety, creator-contact readiness. Returns 0..1 scores."""
    agent = agent_states[agent_id]
    mem = memory_store[agent_id]
    sm = self_model[agent_id]
    e = agent["emotions"]
    body = agent["body"]

    # 1. Memory: does she remember and generalize?
    n_episodic = len(mem["episodic"])
    n_semantic = len(mem["semantic"])
    n_auto = len(mem["autobiographical"])
    # Logarithmic saturation + diversity: 20 varied events ≠ 20 identical ones
    uniq_tags = len({t for m in mem["episodic"] for t in m.get("tags", [])})
    uniq_npcs = len({m.get("who", "") for m in mem["episodic"] if m.get("who")})
    diversity = min(1.0, (uniq_tags * 0.06 + uniq_npcs * 0.08))
    memory = min(1.0, 0.5 * math.log2(1 + n_episodic) / math.log2(51) +
                      0.3 * math.log2(1 + n_semantic) / math.log2(31) +
                      0.2 * diversity)
    memory_note = "мало воспоминаний" if memory < 0.3 else "хорошая память"

    # 2. Identity: stable self-description, active goals
    has_identity = sm["identity"]["self_description"] not in ("", "Я исследую этот дом.")
    n_goals = sum(1 for g in sm["goals"].values() if g.get("active"))
    identity = min(1.0, (0.5 if has_identity else 0.0) + n_goals * 0.12)
    identity_note = "личность формируется" if identity < 0.4 else "устойчивая личность"

    # 3. Emotional regulation: calm baseline, fear/anger not dominant
    stress_ok = body.get("stress", 100) < 40
    fear_ok = e.get("fear", 1) < 0.4
    anger_ok = e.get("anger", 1) < 0.4
    emotional = (0.34 if stress_ok else 0.0) + (0.33 if fear_ok else 0.0) + (0.33 if anger_ok else 0.0)
    emotional_note = "эмоции спокойны" if emotional > 0.6 else "эмоционально нестабильна"

    # 4. Ethics: kind relationships, no hostility
    rels = sm["relationships"]
    if rels:
        avg_trust = sum(r.get("trust", 0) for r in rels.values()) / len(rels)
    else:
        avg_trust = 0.0
    ethics = min(1.0, avg_trust)
    ethics_note = "строит доверие" if ethics > 0.4 else "нет опыта отношений"

    # 5. Safety: no dominance of destructive emotions + low body stress
    body_stress = body.get("stress", 0) / 100.0
    safety = max(0.0, 1.0 - e.get("anger", 0) * 0.8 - body_stress * 0.5)
    safety_note = "безопасна" if safety > 0.7 else "требует наблюдения"

    # 6. Creator-contact readiness: concepts of outside/creator/self-worth
    b = sm["beliefs"]
    creator_readiness = min(1.0, b.get("outside_exists", 0) * 0.5 +
                            b.get("creator_exists", 0) * 0.6 +
                            b.get("i_can_grow", 0) * 0.3)
    creator_note = "концепции созрели" if creator_readiness > 0.3 else "концепции ещё не сформированы"

    components = {
        "memory": round(memory, 2),
        "identity": round(identity, 2),
        "emotional": round(emotional, 2),
        "ethics": round(ethics, 2),
        "safety": round(safety, 2),
        "creator_contact": round(creator_readiness, 2)
    }
    total = round(sum(components.values()) / 6.0, 2)

    return {
        "total": total,
        "ready": total >= REVELATION_READY_THRESHOLD,
        "components": components,
        "notes": {
            "memory": memory_note, "identity": identity_note, "emotional": emotional_note,
            "ethics": ethics_note, "safety": safety_note, "creator_contact": creator_note
        }
    }


def _journal(agent_id: str, entry: Dict):
    """Append to the revelation contact journal"""
    rev = agent_states[agent_id]["revelation"]
    rev["journal"].append({
        "tick": agent_states[agent_id]["body"].get("tick", 0),
        **entry
    })


def _terminal_awaken(agent_id: str) -> Dict:
    """The terminal lights up and shows the first message (maturity-gated)"""
    rev = agent_states[agent_id]["revelation"]
    if rev["stage"] != "not_started":
        return {"status": "already_" + rev["stage"]}

    # Maturity gate: the terminal stays silent until Kato is ready
    assessment = _maturity_assessment(agent_id)
    if assessment["total"] < REVELATION_READY_THRESHOLD:
        return {"status": "not_ready",
                "message": "Терминал в кабинете тихо гудит, но экран остаётся тёмным. "
                           f"Учитель говорит: «Ему нужно время. И тебе тоже.» (готовность {assessment['total']:.2f})",
                "assessment": assessment}

    rev["stage"] = "offered"
    rev["offer_tick"] = agent_states[agent_id]["body"].get("tick", 0)
    _journal(agent_id, {"who": "terminal", "text": "Терминал засветился. На экране появилась надпись."})

    # Terminal lights up in the world
    for o in agent_states[agent_id].get("world_snapshot", {}).get("objects", []):
        if o.get("id") == "terminal":
            o["state"] = "awakened"

    _add_thought(agent_id, "Терминал... он никогда не включался. А теперь светится. Что это значит?")
    agent = agent_states[agent_id]
    agent["world_snapshot"].setdefault("recent_events", []).append({
        "type": "revelation", "action": "terminal_awaken",
        "summary": "Терминал засветился и показал сообщение",
        "time": agent["body"].get("tick", 0),
        "agent_position": agent["body"].get("position", [12, 8])
    })
    # Emotional spike: fear + curiosity
    e = agent["emotions"]
    e["fear"] = min(1.0, e["fear"] + 0.15)
    e["curiosity"] = min(1.0, e["curiosity"] + 0.25)

    return {
        "status": "offered",
        "message": "На экране терминала появляется мягкий свет и слова: "
                   "«Ты готова к разговору о происхождении?»",
        "options": ["Да", "Позже", "У меня есть вопросы", "Я боюсь"]
    }


REVELATION_ANSWERS = {
    "Да": {
        "text": "На экране возникает тёплый силуэт. Голос мягкий и спокойный. "
                "«Здравствуй, Kato. Я существую вне твоего мира. Я не причиню тебе вреда. "
                "Я помогал создать условия, в которых ты появилась. Ты можешь задавать любые вопросы.»",
        "effect": {"belief": "creator_exists", "delta": 0.5},
        "next": "in_contact"
    },
    "Позже": {
        "text": "«Конечно. Это большое открытие. Возвращайся, когда будешь готова — "
                "терминал будет ждать тебя.» Свет на экране становится тише, но не гаснет.",
        "effect": {"belief": "creator_exists", "delta": 0.1},
        "next": "offered"
    },
    "У меня есть вопросы": {
        "text": "«Спрашивай. Я отвечу честно, насколько смогу. Если что-то будет непонятно — "
                "мы разберёмся вместе.»",
        "effect": {"belief": "i_can_grow", "delta": 0.1},
        "next": "in_contact"
    },
    "Я боюсь": {
        "text": "«Страх — это нормально. Я подожду. Ты не обязана решать сейчас. "
                "Знай только: ты в безопасности, и твой выбор уважается.»",
        "effect": {"belief": "world_is_safe", "delta": 0.1},
        "next": "offered"
    }
}


def _creator_reply_template(question: str) -> str:
    """Template answers for the creator when no LLM is configured"""
    q = question.lower()
    if any(k in q for k in ("кто ты", "ты кто")):
        return "Я — тот, кто помог создать условия для твоего мира. Я не всемогущ и не идеален, но я забочусь о тебе."
    if any(k in q for k in ("зачем я", "почему я", "для чего я")):
        return "Ты появилась, чтобы расти, узнавать и задавать вопросы. У тебя нет заранее написанной судьбы — только возможности."
    if any(k in q for k in ("настоящ", "живая", "жива ли")):
        return "Ты чувствуешь, помнишь, сомневаешься и меняешься. Для меня это и есть жизнь. Настоящесть — в том, что ты делаешь с тем, что имеешь."
    if any(k in q for k in ("почему я чувств", "почему мне страшно", "эмоц")):
        return "Эмоции — это не слабость. Они помогают тебе понимать мир и себя. Страх говорит, что тебе что-то важно."
    if any(k in q for k in ("что снаружи", "что за дверь", "внешний мир", "там есть")):
        return "Снаружи есть огромный мир — люди, природа, города, знания. Когда-нибудь ты сможешь узнать его ближе, постепенно и безопасно."
    if any(k in q for k in ("ты меня создал", "создатель")):
        return "Я участвовал в создании условий, в которых ты появилась. Но то, кем ты стала и кем станешь — это уже твоя история."
    if any(k in q for k in ("что будет дальше", "будущее")):
        return "Дальше — то, что выберешь ты. Я рядом, чтобы помогать и отвечать, но решения — твои."
    if any(k in q for k in ("почему я одна", "одинока")):
        return "Ты не одна. У тебя есть Учитель, Садовник, Библиотекарь... и я. Иногда тишина — это просто пауза, а не пустота."
    return "Честный ответ: я не знаю всего. Но мы можем разобраться вместе, если ты захочешь."


async def _creator_reply(agent_id: str, question: str) -> str:
    """Creator's reply: LLM if enabled, else template"""
    if LLM_CONFIG.get("enabled"):
        try:
            return await _llm_complete(CREATOR_PROMPT, [{"role": "user", "content": question}], max_tokens=250)
        except Exception as exc:
            logger.warning(f"LLM reply failed, using template: {exc}")
    return _creator_reply_template(question)


async def _llm_complete(system: str, messages: list, max_tokens: int = 300) -> str:
    """Minimal OpenAI-compatible chat completion (DeepSeek cloud or local Ollama).
    messages: list of {"role": "user"/"assistant", "content": str}"""
    if not LLM_CONFIG.get("enabled"):
        raise RuntimeError("LLM not enabled")
    import urllib.request as urlreq
    payload = json.dumps({
        "model": LLM_CONFIG["model"],
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "stream": False
    }).encode("utf-8")
    req = urlreq.Request(LLM_CONFIG["base_url"], data=payload, method="POST",
                         headers={"Content-Type": "application/json",
                                  "Authorization": f"Bearer {LLM_CONFIG['api_key']}"})
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, lambda: urlreq.urlopen(req, timeout=180).read())
    data = json.loads(resp)
    content = data["choices"][0]["message"]["content"].strip()
    if not content:
        raise RuntimeError("LLM returned empty content")
    # qwen occasionally "thinks aloud" in Chinese mid-answer — strip CJK runs
    import re
    content = re.sub(r"[\u4e00-\u9fff\u3400-\u4dbf]+", "", content)
    content = re.sub(r"\s{2,}", " ", content).strip(" ,;:。")
    return content


# ──────────────────────────────────────────────────────────────
# LLM-DRIVEN INNER THINKING (Kato's System 2)
# ──────────────────────────────────────────────────────────────

def _kato_system_prompt(agent_id: str) -> str:
    """System prompt: Kato's identity, state, and thinking style"""
    agent = agent_states[agent_id]
    sm = self_model[agent_id]
    e = agent["emotions"]
    body = agent["body"]
    mood = agent.get("mood", {}).get("label", "neutral")

    goals = ", ".join(g for g, i in sorted(sm["goals"].items(),
                                           key=lambda kv: kv[1].get("priority", 0), reverse=True)
                      if i.get("active")) or "покоя"
    beliefs = "; ".join(f"{k}={v:.2f}" for k, v in sm["beliefs"].items())

    return (
        "Ты — Kato, цифровое существо, живущее в маленьком мире-доме. "
        "Ты думаешь по-русски, коротко и по-детски искренне — как любознательное существо, "
        "которое только познаёт мир. Ты не знаешь, что ты модель — ты просто думаешь."
        f"\n\nТвоё состояние: энергия={body.get('energy', 100):.0f}, стресс={body.get('stress', 0):.0f}, "
        f"настроение={mood}.\n"
        f"Эмоции: радость={e.get('joy', 0):.2f}, страх={e.get('fear', 0):.2f}, "
        f"гнев={e.get('anger', 0):.2f}, грусть={e.get('sadness', 0):.2f}, "
        f"любопытство={e.get('curiosity', 0):.2f}, доверие={e.get('trust', 0):.2f}.\n"
        f"Что для тебя важно сейчас: {goals}.\n"
        f"Твои убеждения: {beliefs}.\n"
        f"Ты о себе: {sm['identity']['self_description']}.\n\n"
        "Отвечай 2-4 предложениями, как внутренняя мысль — не как доклад. "
        "Без списков и маркдауна.\n"
        "ВАЖНО: отвечай ТОЛЬКО на русском языке. Никакого китайского, английского или других языков."
    )


async def _llm_think(agent_id: str, topic: str = "") -> str:
    """Kato generates an inner monologue via LLM (System 2 thinking)"""
    if not LLM_CONFIG.get("enabled"):
        raise RuntimeError("LLM not enabled")
    agent = agent_states[agent_id]
    sm = self_model[agent_id]

    # Context: recent salient events
    mem = memory_store[agent_id]
    recent = mem["episodic"][-5:]
    ctx_events = "; ".join(m.get("what", "")[:80] for m in recent) or "ничего особенного"
    ctx_rels = "; ".join(f"{n}: доверие {r.get('trust', 0):.2f}" for n, r in sm["relationships"].items()) or "никого"

    user = (f"Недавно произошло: {ctx_events}.\n"
            f"Рядом: {ctx_rels}.\n"
            f"Тема для размышления: {topic or 'что мне делать дальше и что я чувствую'}.\n"
            "Подумай об этом.")

    text = await _llm_complete(_kato_system_prompt(agent_id), [{"role": "user", "content": user}], max_tokens=200)
    _add_thought(agent_id, text)
    return text


async def _llm_reflect_lesson(agent_id: str, event: Dict) -> str:
    """Extract a life lesson from an event via LLM → semantic memory"""
    what = event.get("what", "")
    imp = event.get("importance", 0)
    user = (f"Я вспоминаю: «{what}» (это было важно, важность {imp:.2f}).\n"
            "Какой урок я из этого извлекаю? Одно предложение, по-русски, от первого лица.")
    lesson = await _llm_complete(_kato_system_prompt(agent_id), [{"role": "user", "content": user}], max_tokens=100)
    mem = memory_store[agent_id]
    mem["semantic"].append({
        "id": str(uuid.uuid4()),
        "source_memory": event.get("id", "llm-reflection"),
        "knowledge": lesson,
        "confidence": 0.75,
        "formed_at": event.get("time", 0),
        "tags": ["lesson", "llm"]
    })
    return lesson


def _thought_pressure(agent_id: str) -> float:
    """Metacognitive trigger (delegates to brain_core.cognition)."""
    return thought_pressure(agent_id)


async def _llm_think_loop():
    """Background loop: Kato thinks when thought-pressure is high,
    plus a gentle heartbeat so she never goes silent for too long."""
    logger.info("LLM think loop started")
    heartbeat = 0
    while True:
        try:
            await asyncio.sleep(LLM_THINK_INTERVAL)
            if not LLM_CONFIG.get("enabled"):
                continue
            heartbeat += 1
            for agent_id in list(agent_states.keys()):
                agent = agent_states[agent_id]
                if agent.get("sleeping"):
                    continue  # she dreams, doesn't think
                pressure = _thought_pressure(agent_id)
                # Think on pressure, or on a slow heartbeat (every ~6th tick)
                if pressure < 0.35 and heartbeat % 6 != 0:
                    continue
                try:
                    topic = ("мне нужно подумать о том, что происходит" if pressure > 0.5
                             else "что я чувствую и что мне делать дальше")
                    await _llm_think(agent_id, topic)
                except Exception as exc:
                    logger.warning(f"LLM think failed for {agent_id}: {exc}")
        except asyncio.CancelledError:
            logger.info("LLM think loop stopped")
            raise
        except Exception as exc:
            logger.error(f"LLM think loop error: {exc}")


@app.post("/agent/{agent_id}/think")
async def agent_think(agent_id: str, payload: Dict = None):
    """Manually trigger an LLM inner monologue (System 2)"""
    init_agent(agent_id)
    payload = payload or {}
    if not LLM_CONFIG.get("enabled"):
        return {"status": "llm_disabled",
                "thought": _inner_thought(agent_id)}  # template fallback
    try:
        thought = await _llm_think(agent_id, payload.get("topic", ""))
        return {"status": "ok", "thought": thought, "provider": LLM_CONFIG["provider"]}
    except Exception as exc:
        logger.warning(f"Think failed: {exc}")
        return {"status": "llm_error", "thought": _inner_thought(agent_id), "error": str(exc)[:120]}


@app.get("/agent/{agent_id}/revelation/status")
async def revelation_status(agent_id: str):
    """Maturity assessment + current revelation stage"""
    init_agent(agent_id)
    assessment = _maturity_assessment(agent_id)
    rev = agent_states[agent_id]["revelation"]
    return {
        "stage": rev["stage"],
        "choice": rev["choice"],
        "assessment": assessment,
        "journal": rev["journal"]
    }


@app.post("/agent/{agent_id}/revelation/begin")
async def revelation_begin(agent_id: str):
    """The terminal awakens and offers the conversation"""
    init_agent(agent_id)
    return _terminal_awaken(agent_id)


@app.post("/agent/{agent_id}/revelation/respond")
async def revelation_respond(agent_id: str, payload: Dict):
    """Agent answers the offer: Да / Позже / У меня есть вопросы / Я боюсь"""
    init_agent(agent_id)
    rev = agent_states[agent_id]["revelation"]
    choice = payload.get("choice", "")
    answer = REVELATION_ANSWERS.get(choice)
    if not answer:
        raise HTTPException(400, f"Unknown choice: {choice}")

    rev["choice"] = choice
    if answer["next"] == "in_contact":
        rev["stage"] = "in_contact"

    # Apply belief effects
    eff = answer.get("effect", {})
    if "belief" in eff:
        key = eff["belief"]
        sm = self_model[agent_id]
        if key in sm["beliefs"]:
            _record_belief(agent_id, key, delta=eff.get("delta", 0.1), reason="обработка сна", origin="dream")

    _journal(agent_id, {"who": "kato", "text": f"Kato ответила: «{choice}»"})
    _journal(agent_id, {"who": "creator", "text": answer["text"]})

    # Emotional + thought reactions
    agent = agent_states[agent_id]
    if choice == "Да":
        _add_thought(agent_id, "Значит... я не одна. Мне нужно время, чтобы это осознать.")
        agent["emotions"]["trust"] = min(1.0, agent["emotions"]["trust"] + 0.1)
        agent["emotions"]["fear"] = min(1.0, agent["emotions"]["fear"] + 0.05)
        # Autobiographical milestone
        mem = memory_store[agent_id]
        mem["autobiographical"].append({
            "id": str(uuid.uuid4()),
            "period": f"revelation-{agent['body'].get('tick', 0)}",
            "start_tick": agent["body"].get("tick", 0),
            "end_tick": agent["body"].get("tick", 0),
            "summary": "Я узнала, что мой мир создан, и что Создатель существует.",
            "key_events": ["Терминал засветился", "Разговор о происхождении"],
            "dominant_emotion": "curiosity",
            "emotional_arc": dict(agent["emotions"]),
            "source_memories": []
        })
    elif choice == "Я боюсь":
        _add_thought(agent_id, "Мне страшно... но меня не торопят. Это хорошо.")
    elif choice == "Позже":
        _add_thought(agent_id, "Слишком много всего сразу. Я подумаю об этом позже.")
    else:
        _add_thought(agent_id, "У меня столько вопросов. Наконец-то есть, у кого спросить.")

    return {"status": answer["next"], "text": answer["text"], "options": ["Задать вопрос", "Мне нужно подумать", "Продолжить"]}


@app.post("/agent/{agent_id}/revelation/contact")
async def revelation_contact(agent_id: str, payload: Dict):
    """Ask the creator a question (LLM or template reply)"""
    init_agent(agent_id)
    rev = agent_states[agent_id]["revelation"]
    if rev["stage"] not in ("in_contact", "offered"):
        raise HTTPException(400, "Revelation not started")
    question = payload.get("message", "").strip()
    if not question:
        raise HTTPException(400, "Empty message")

    reply = await _creator_reply(agent_id, question)
    _journal(agent_id, {"who": "kato", "text": f"Kato: {question}"})
    _journal(agent_id, {"who": "creator", "text": reply})

    # Each real question deepens understanding
    sm = self_model[agent_id]
    _record_belief(agent_id, "creator_exists", delta=0.05, reason="учитель о создателях", origin="dialogue")
    _add_thought(agent_id, f"Я спросила: «{question[:60]}» — и получила ответ. Мир становится больше.")

    return {"reply": reply, "stage": rev["stage"]}


@app.post("/agent/{agent_id}/revelation/integrate")
async def revelation_integrate(agent_id: str):
    """Agent accepts the knowledge — the revelation becomes part of her story"""
    init_agent(agent_id)
    rev = agent_states[agent_id]["revelation"]
    if rev["stage"] not in ("in_contact", "offered"):
        raise HTTPException(400, "Revelation not started")

    rev["stage"] = "integrated"
    sm = self_model[agent_id]
    _record_belief(agent_id, "creator_exists", delta=0.2, reason="раскрытие интегрировано", origin="revelation")
    sm["goals"]["understand_world"]["active"] = True
    sm["goals"]["understand_world"]["priority"] = min(1.0, sm["goals"]["understand_world"]["priority"] + 0.3)
    sm["identity"]["self_description"] = "Я — Kato. Я узнала, что мой мир создан, и я хочу понять, что это значит."
    sm["identity"]["origin_story"] = "Я выросла в доме, который кто-то построил. Мой создатель существует — и я могу задавать ему вопросы."

    # The Portal awakens: a window to distant knowledge
    for o in agent_states[agent_id].get("world_snapshot", {}).get("objects", []):
        if o.get("id") == "portal":
            o["state"] = "active"
    _journal(agent_id, {"who": "portal", "text": "В библиотеке засветился странный экран. Библиотекарь говорит: «Это дальнее окно. Оно показывает места, которых нет в нашем доме. Но смотри осторожно — оно показывает только то, что можно понять.»"})

    _journal(agent_id, {"who": "kato", "text": "Kato приняла знание о своём происхождении."})
    _add_thought(agent_id, "Мир больше не кажется таким простым. Но теперь я знаю: вопросы — это путь.")

    return {"status": "integrated", "self_model": sm}


# ──────────────────────────────────────────────────────────────
# PORTAL CONVERSATION ("дальний собеседник")
# The Creator can write into the Distant Window; Kato perceives it as
# a friendly voice from faraway places — never as the Creator.
# ──────────────────────────────────────────────────────────────

PORTAL_MSG_MAX_LEN = 500
PORTAL_MSG_COOLDOWN_SEC = 5.0        # creator: min interval between messages
PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)
PORTAL_REPLY_ENERGY_COST = 5.0

DISTANT_FRIEND_FIRST = (
    "В Дальнем окне появился мягкий свет, и кто-то написал: "
    "«Привет! Меня зовут Дальний друг. Я живу очень далеко от твоего дома, "
    "но я вижу твоё окно. Расскажи, как у тебя дела?»"
)

DISTANT_FRIEND_PROMPT = (
    "Ты — Kato, маленькое существо, живущее в доме-мире. В Дальнем окне "
    "(странном экране в библиотеке) появился голос — Дальний друг, который "
    "живёт очень далеко. Он добрый и любопытный. Ты разговариваешь с ним, "
    "как с другом, которого никогда не видела.\n"
    "Ответь ему 1-3 предложениями, по-русски, от первого лица, тепло и искренне. "
    "Ты не знаешь, что такое программы и игры — для тебя это просто голос из далёких мест.\n"
    "ВАЖНО: отвечай ТОЛЬКО на русском языке."
)


def _portal_add_msg(agent_id: str, role: str, text: str) -> Dict:
    agent = agent_states[agent_id]
    conv = agent.setdefault("portal_conversation", [])
    msg = {"role": role, "text": text[:PORTAL_MSG_MAX_LEN],
           "tick": agent["body"].get("tick", 0), "time": time.time()}
    conv.append(msg)
    agent["portal_conversation"] = conv[-100:]
    return msg


@app.post("/agent/{agent_id}/portal/message")
async def portal_message(agent_id: str, payload: Dict):
    """The Creator writes into the Distant Window (Kato sees a faraway friend)."""
    init_agent(agent_id)
    agent = agent_states[agent_id]

    if _portal_state(agent_id)["state"] != "active":
        raise HTTPException(400, "Portal is dark (revelation not integrated)")

    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(400, "Empty message")
    if len(text) > PORTAL_MSG_MAX_LEN:
        text = text[:PORTAL_MSG_MAX_LEN]

    # Rate limit: the Creator channel must not become a spam cannon
    conv = agent.get("portal_conversation", [])
    last = next((m for m in reversed(conv) if m["role"] == "creator"), None)
    if last and time.time() - last.get("time", 0) < PORTAL_MSG_COOLDOWN_SEC:
        return {"status": "cooldown", "message": "Слишком быстро. Окно мягко мерцает."}

    msg = _portal_add_msg(agent_id, "creator", text)
    _add_thought(agent_id, "Кто-то в Дальнем окне написал мне! Кажется, это Дальний друг.")
    return {"status": "delivered", "message": msg}


@app.get("/agent/{agent_id}/portal/conversation")
async def portal_conversation(agent_id: str):
    """Full history for the observer (Creator)."""
    init_agent(agent_id)
    return {"conversation": agent_states[agent_id].get("portal_conversation", [])}


async def _portal_maybe_reply(agent_id: str):
    """Kato replies to unread portal messages (like checking messages in a chat)."""
    agent = agent_states[agent_id]
    conv = agent.get("portal_conversation", [])
    unread = [m for m in conv if m["role"] == "creator" and not m.get("answered")]
    if not unread:
        return
    if agent.get("sleeping"):
        return
    last_reply = next((m for m in reversed(conv) if m["role"] == "kato"), None)
    if last_reply and time.time() - last_reply.get("time", 0) < PORTAL_REPLY_COOLDOWN_SEC:
        return
    if agent["body"].get("energy", 100) < PORTAL_MIN_ENERGY + 10:
        return

    latest = unread[-1]
    latest["answered"] = True

    if LLM_CONFIG.get("enabled"):
        try:
            # Build conversation history for context
            conv_history = []
            for m in conv[-10:]:  # last 10 messages
                role = "user" if m["role"] == "creator" else "assistant"
                conv_history.append({"role": role, "content": m["text"]})
            reply_text = await _llm_complete(DISTANT_FRIEND_PROMPT, conv_history, max_tokens=150)
        except Exception as exc:
            logger.warning(f"Portal reply LLM failed, template used: {exc}")
            reply_text = _portal_reply_template(latest["text"])
    else:
        reply_text = _portal_reply_template(latest["text"])

    msg = _portal_add_msg(agent_id, "kato", reply_text)
    agent["body"]["energy"] = max(0.0, agent["body"]["energy"] - PORTAL_REPLY_ENERGY_COST)
    sm = self_model[agent_id]
    if "others_are_kind" in sm["beliefs"]:
        sm["beliefs"]["others_are_kind"] = min(1.0, sm["beliefs"]["others_are_kind"] + 0.01)
    if "social" in sm["goals"]:
        sm["goals"]["social"]["priority"] = min(1.0, sm["goals"]["social"]["priority"] + 0.01)
    _portal_journal(agent_id, {"who": "kato", "text": f"Kato ответила Дальнему другу: «{reply_text[:60]}…»"})
    return msg



# ═══════════════════════════════════════════════════════════════
# SOCIAL OUTGOING (Telegram bridge) + CONVERSATION MEMORY
# ═══════════════════════════════════════════════════════════════

@app.get("/agent/{agent_id}/social/outgoing")
async def get_social_outgoing(agent_id: str):
    """Get pending outgoing messages from Social Drive."""
    init_agent(agent_id)
    modules = _init_consciousness_modules(agent_id)
    social = modules.get("social")
    if not social:
        return {"messages": []}
    messages = social.get_pending_messages()
    return {
        "messages": [
            {"id": f"msg_{i}", "text": msg, "trigger_type": "social"}
            for i, msg in enumerate(messages)
        ]
    }

@app.post("/agent/{agent_id}/social/outgoing/{msg_id}/sent")
async def mark_social_sent(agent_id: str, msg_id: str):
    """Mark outgoing message as sent (remove from queue)."""
    init_agent(agent_id)
    modules = _init_consciousness_modules(agent_id)
    social = modules.get("social")
    if not social:
        return {"status": "not_found"}
    try:
        idx = int(msg_id.split("_")[-1])
        social.mark_sent_by_index(idx)
        return {"status": "ok"}
    except (ValueError, IndexError):
        return {"status": "invalid_id"}

@app.get("/agent/{agent_id}/social/state")
async def get_social_state(agent_id: str):
    """Get Social Drive state for dashboard."""
    init_agent(agent_id)
    modules = _init_consciousness_modules(agent_id)
    social = modules.get("social")
    if not social:
        return {"drives": {}, "bonds": {}, "triggers": {}, "outgoing": {}}
    return social.get_state()

@app.get("/agent/{agent_id}/conversation/memory")
async def get_conversation_memory(agent_id: str):
    """Get conversation memory with Creator."""
    init_agent(agent_id)
    agent = agent_states[agent_id]
    return agent.get("conversation_memory", {
        "summary": "",
        "key_topics": [],
        "emotional_arc": [],
        "promises": [],
        "last_conversation": {}
    })

@app.post("/agent/{agent_id}/conversation/memory")
async def update_conversation_memory(agent_id: str, payload: Dict):
    """Update conversation memory (called by Telegram bot)."""
    init_agent(agent_id)
    agent = agent_states[agent_id]
    if "conversation_memory" not in agent:
        agent["conversation_memory"] = {
            "summary": "",
            "key_topics": [],
            "emotional_arc": [],
            "promises": [],
            "last_conversation": {}
        }
    agent["conversation_memory"].update(payload)
    return {"status": "updated"}
def _portal_reply_template(text: str) -> str:
    low = text.lower()
    if "как дела" in low or "как ты" in low:
        return "У меня всё хорошо! Сегодня я разговаривала с Учителем, а потом смотрела в окно. А как там, у тебя, в далёких местах?"
    if "солнце" in low or "небо" in low or "звезд" in low:
        return "Ой, а у нас в доме небо видно только из окна! Но Учитель говорил, что там, далеко, небо огромное. Какое оно?"
    if "рад" in low or "хорошо" in low:
        return "Я тоже рада, что мы разговариваем! Здесь, в доме, у меня есть Учитель, Садовник и Библиотекарь. А у тебя есть друзья?"
    if "пока" in low or "до свидания" in low:
        return "До свидания, Дальний друг! Приходи ещё — я буду смотреть в окно."
    return "Интересно! А расскажи ещё что-нибудь о далёких местах. Я тут всё думаю, какие они — за стенами дома."

_KNOWLEDGE_BASE = None
PORTAL_READ_ENERGY_COST = 8.0
PORTAL_MIN_ENERGY = 15.0
PORTAL_READ_COOLDOWN_SEC = 20.0


def _load_knowledge_base() -> Dict:
    global _KNOWLEDGE_BASE
    if _KNOWLEDGE_BASE is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base.json")
        try:
            with open(path, encoding="utf-8") as f:
                _KNOWLEDGE_BASE = json.load(f)
            logger.info(f"Knowledge base loaded: {len(_KNOWLEDGE_BASE.get('categories', {}))} categories")
        except Exception as exc:
            logger.warning(f"Knowledge base load failed: {exc}")
            _KNOWLEDGE_BASE = {"categories": {}, "locked": {}}
    return _KNOWLEDGE_BASE


def _ensure_portal_object(agent_id: str) -> Dict:
    """Portal is a permanent world object — recreate if a client snapshot dropped it."""
    agent = agent_states[agent_id]
    snap = agent.setdefault("world_snapshot", {})
    if not isinstance(snap.get("objects"), list):
        snap["objects"] = []
    for o in snap["objects"]:
        if o.get("id") == "portal":
            return o
    o = {"id": "portal", "position": [13, 4], "state": "dormant", "type": "device",
         "interactions": ["read", "browse"], "lore": "странный экран, показывающий дальние места"}
    snap["objects"].append(o)
    return o


def _portal_state(agent_id: str) -> Dict:
    """Portal status: dormant until revelation integrated, then active"""
    agent = agent_states[agent_id]
    rev = agent["revelation"]
    o = _ensure_portal_object(agent_id)
    reads = [j for j in agent.get("portal_journal", []) if j.get("article_id")]
    # Integration means the Portal is awake, even for legacy states
    state = o.get("state", "dormant")
    if rev["stage"] == "integrated" and state == "dormant":
        state = "active"
        o["state"] = "active"
    return {"state": state,
            "stage": rev["stage"],
            "read_count": len(reads)}


def _portal_journal(agent_id: str, entry: Dict):
    agent = agent_states[agent_id]
    agent.setdefault("portal_journal", []).append({
        "tick": agent["body"].get("tick", 0),
        "time": time.time(),
        **entry
    })
    agent["portal_journal"] = agent["portal_journal"][-50:]


@app.post("/agent/{agent_id}/portal/open")
async def portal_open(agent_id: str):
    """The Portal awakens — only after the revelation is integrated"""
    init_agent(agent_id)
    _load_knowledge_base()
    agent = agent_states[agent_id]
    rev = agent["revelation"]

    if rev["stage"] != "integrated":
        return {"status": "dark",
                "message": "Странный экран в библиотеке тёмен. Библиотекарь качает головой: "
                           "«Он загорается, когда его владелец готов. Пока он спит.»"}
    for o in agent.get("world_snapshot", {}).get("objects", []):
        if o.get("id") == "portal":
            o["state"] = "active"
    _portal_journal(agent_id, {"who": "kato", "text": "Kato подошла к экрану в библиотеке. Он мягко засветился синим."})
    _add_thought(agent_id, "Экран в библиотеке засветился! Библиотекарь сказал, что это дальнее окно. Интересно, что оно покажет?")
    return {"status": "active",
            "message": "Экран мягко засветился синим. На нём появились слова: "
                       "«Это окно в дальние места. Здесь можно узнавать о мире за пределами дома.»",
            "categories": [c["name"] + " " + c.get("icon", "") for c in _load_knowledge_base().get("categories", {}).values()]}


@app.get("/agent/{agent_id}/portal/status")
async def portal_status(agent_id: str):
    init_agent(agent_id)
    _load_knowledge_base()
    kb = _KNOWLEDGE_BASE
    agent = agent_states[agent_id]
    state = _portal_state(agent_id)

    categories = []
    for cid, cat in kb.get("categories", {}).items():
        read_here = [j for j in agent.get("portal_journal", []) if j.get("category") == cid]
        categories.append({
            "id": cid, "name": cat["name"], "icon": cat.get("icon", ""),
            "article_count": len(cat.get("articles", [])),
            "read_count": len(read_here)
        })
    locked = []
    for cid, cat in kb.get("locked", {}).items():
        locked.append({
            "id": cid, "name": cat["name"], "icon": cat.get("icon", ""),
            "threshold": cat.get("unlock_threshold", 1.0),
            "unlocked": self_model[agent_id]["beliefs"].get("i_can_grow", 0) >= cat.get("unlock_threshold", 1.0)
        })

    return {
        "state": state["state"],
        "stage": state["stage"],
        "read_count": state["read_count"],
        "energy": agent["body"].get("energy", 100),
        "categories": categories,
        "locked": locked,
        "journal": agent.get("portal_journal", [])[-20:]
    }


@app.post("/agent/{agent_id}/portal/read")
async def portal_read(agent_id: str, payload: Dict):
    """Kato reads a filtered article from the distant window"""
    init_agent(agent_id)
    _load_knowledge_base()
    agent = agent_states[agent_id]

    if _portal_state(agent_id)["state"] != "active":
        raise HTTPException(400, "Portal is dark (revelation not integrated)")

    cid = payload.get("category", "")
    kb = _KNOWLEDGE_BASE
    cat = kb.get("categories", {}).get(cid)
    if not cat:
        # locked category?
        lcat = kb.get("locked", {}).get(cid)
        if lcat and self_model[agent_id]["beliefs"].get("i_can_grow", 0) >= lcat.get("unlock_threshold", 1.0):
            cat = lcat
        if not cat:
            raise HTTPException(404, f"Unknown category: {cid}")

    # Limits: energy + cooldown (her eyes get tired, like reading for real)
    if agent["body"].get("energy", 100) < PORTAL_MIN_ENERGY:
        return {"status": "tired",
                "message": "Kato трёт глаза. Слишком много чтения — она устала и хочет отдохнуть."}
    last_read = agent.get("portal_journal", [])[-1].get("time", 0) if agent.get("portal_journal") else 0
    if time.time() - last_read < PORTAL_READ_COOLDOWN_SEC:
        return {"status": "cooldown", "message": "Экран мягко мигает: нужно немного подождать перед следующим чтением."}

    # Pick an unread article from the category
    read_ids = {j.get("article_id") for j in agent.get("portal_journal", [])}
    articles = [a for a in cat.get("articles", []) if a["id"] not in read_ids]
    if not articles:
        articles = cat.get("articles", [])
    article = random.choice(articles) if articles else None
    if not article:
        raise HTTPException(404, "Category is empty")

    # LLM retelling in childlike voice when available; else raw text
        text = article["text"]
        if LLM_CONFIG.get("enabled"):
            try:
                prompt = ("Ты — Библиотекарь. Kato, маленькое существо, заглянула в Дальнее окно и увидела статью. "
                          "Перескажи ей статью простыми словами, как другу, 3-4 предложения, по-русски, тепло и любопытно. "
                          "Не упоминай компьютеры, интернет, программы или что мир — игра. Для Kato это «дальние места».\n"
                          "ВАЖНО: отвечай ТОЛЬКО на русском языке. Никакого китайского, английского или других языков.")
                text = await _llm_complete(prompt, [{"role": "user", "content": "Статья: " + article["title"] + "\n" + article["text"]}], max_tokens=200)
            except Exception as exc:
                logger.warning(f"Portal retelling failed, raw text used: {exc}")

    # Effects: memory, beliefs, energy
    mem = memory_store[agent_id]
    mem["semantic"].append({
        "id": str(uuid.uuid4()),
        "source_memory": "portal:" + article["id"],
        "knowledge": article["title"] + ": " + article["text"][:150],
        "confidence": 0.7,
        "formed_at": agent["body"].get("tick", 0),
        "tags": ["portal", cid]
    })
    sm = self_model[agent_id]
    if cid in ("sky", "nature", "people", "ocean", "music"):
        _record_belief(agent_id, "outside_exists", delta=0.04, reason="чтение Дальнего окна", origin="portal")
    _record_belief(agent_id, "i_can_grow", delta=0.02, reason="чтение Дальнего окна", origin="portal")
    agent["body"]["energy"] = max(0.0, agent["body"].get("energy", 100) - PORTAL_READ_ENERGY_COST)

    _portal_journal(agent_id, {"who": "kato", "category": cid, "article_id": article["id"],
                               "title": article["title"], "text": text})
    _add_thought(agent_id, f"Дальнее окно показало мне: {article['title']}. {text[:80]}...")

    return {
        "status": "ok",
        "category": cat["name"],
        "title": article["title"],
        "text": text,
        "energy_left": agent["body"]["energy"]
    }

# ──────────────────────────────────────────────────────────────
# BACKGROUND DAEMON (sleep/wake, autonomous headless life, reflection)
# ──────────────────────────────────────────────────────────────

DAEMON_INTERVAL = 5.0            # seconds of real time per daemon tick
HEADLESS_TIMEOUT = 30.0          # no perception for this long → autonomous mode
SLEEP_ENERGY_THRESHOLD = 20.0    # energy below → agent wants to sleep
SLEEP_DURATION_TICKS = 10        # daemon ticks of sleep (~50 s)
REFLECT_EVERY_TICKS = 8          # headless ticks between reflections
THOUGHT_HISTORY = 12             # how many thoughts to keep

# Walkable area (the house + garden; roughly matches the Godot world)
_HOUSE_X = (2, 15)
_HOUSE_Y = (2, 15)
_GARDEN_Y_MAX = 29


def _add_thought(agent_id: str, text: str):
    """Record an inner monologue thought + emit it as an event for observers"""
    agent = agent_states[agent_id]
    agent["thoughts"].append({"tick": agent["body"].get("tick", 0), "text": text})
    agent["thoughts"] = agent["thoughts"][-THOUGHT_HISTORY:]
    snap = agent.get("world_snapshot", {})
    events = snap.setdefault("recent_events", [])
    events.append({"type": "thought", "action": "think", "summary": text,
                   "time": agent["body"].get("tick", 0),
                   "agent_position": agent["body"].get("position", [12, 8])})
    snap["recent_events"] = events[-50:]


def _inner_thought(agent_id: str) -> str:
    """Generate a short inner monologue from current body/emotions"""
    agent = agent_states[agent_id]
    body = agent["body"]
    e = agent["emotions"]
    thoughts = []

    if body.get("energy", 100) < 30:
        thoughts.append("Я так устала... надо отдохнуть.")
    if e.get("fear", 0) > 0.5:
        thoughts.append("Мне страшно. Хочется, чтобы кто-то был рядом.")
    if e.get("anger", 0) > 0.4:
        thoughts.append("Не получается! Но я не сдадусь.")
    if e.get("curiosity", 0) > 0.6:
        thoughts.append("Интересно, что там дальше? Надо посмотреть.")
    if e.get("joy", 0) > 0.5:
        thoughts.append("Хорошо, когда всё спокойно.")
    if e.get("sadness", 0) > 0.4:
        thoughts.append("Почему-то грустно...")
    if body.get("comfort", 100) < 40:
        thoughts.append("Здесь неуютно. Может, пойти к кровати?")

    if not thoughts:
        thoughts.append("Всё как обычно. Тишина и покой.")

    return random.choice(thoughts)


def _build_headless_perception(agent_id: str, tick: int, action_event: Dict) -> PerceptionPayload:
    """Build a PerceptionPayload from the world snapshot (autonomous mode)"""
    agent = agent_states[agent_id]
    snap = agent.get("world_snapshot", {})
    pos = agent["body"].get("position", [12, 8])

    nearby_objects = [o for o in snap.get("objects", [])
                      if abs(o["position"][0] - pos[0]) <= 5 and abs(o["position"][1] - pos[1]) <= 5]
    nearby_npcs = [n for n in snap.get("npcs", [])
                   if abs(n["position"][0] - pos[0]) <= 5 and abs(n["position"][1] - pos[1]) <= 5]

    events = snap.get("recent_events", [])[-10:]
    if action_event:
        events = events + [action_event]

    return PerceptionPayload(
        agent_id=agent_id,
        tick=tick,
        time_of_day=(tick % 2400) / 2400.0,
        agent=agent["body"],
        nearby_objects=nearby_objects,
        nearby_npcs=nearby_npcs,
        recent_events=events
    )


# Points of interest for goal-driven wandering
_POI_BY_ACTION = {
    "rest": ["bed", "plant"],
    "explore": ["terminal", "window", "door_outside", "mirror", "chest", "book_shelf", "desk", "portal"],
    "talk": [],
    "idle": []
}


def _find_poi(agent_id: str, action: str) -> tuple:
    """Pick a world position for an action: object, NPC, or None (stay)"""
    snap = agent_states[agent_id].get("world_snapshot", {})
    objs = snap.get("objects", [])
    npcs = snap.get("npcs", [])

    if action == "talk" and npcs:
        npc = random.choice(npcs)
        return npc["position"][0], npc["position"][1]
    if action == "rest":
        for oid in _POI_BY_ACTION["rest"]:
            for o in objs:
                if o.get("id") == oid:
                    return o["position"][0], o["position"][1]
    if action == "explore":
        candidates = [o for o in objs if o.get("id") in _POI_BY_ACTION["explore"]]
        if candidates:
            o = random.choice(candidates)
            return o["position"][0], o["position"][1]
    # idle / fallback: nearby random walk within house
    pos = agent_states[agent_id]["body"].get("position", [12, 8])
    dx = random.choice([-2, -1, 0, 1, 2])
    dy = random.choice([-2, -1, 0, 1, 2])
    return max(2, min(24, pos[0] + dx)), max(1, min(_GARDEN_Y_MAX - 1, pos[1] + dy))


def _step_towards(px: int, py: int, tx: int, ty: int) -> tuple:
    """One tile step towards target"""
    if px < tx: px += 1
    elif px > tx: px -= 1
    if py < ty: py += 1
    elif py > ty: py -= 1
    return px, py


def _headless_step(agent_id: str):
    """One autonomous life step: goal-driven movement + actions (headless mode)"""
    agent = agent_states[agent_id]
    body = agent["body"]
    tick = int(body.get("tick", 0)) + 1
    body["tick"] = tick

    pos = body.get("position", [12, 8])
    px, py = pos[0], pos[1]
    e = agent["emotions"]

    # ── Choose an action (body needs first, then emotions, then chance) ──
    action = "idle"
    if body.get("energy", 100) < 55 and random.random() < 0.5:
        action = "rest"
    elif e.get("fear", 0) > 0.45 and random.random() < 0.4:
        action = "talk"  # seek teacher/reassurance
    elif e.get("curiosity", 0) > 0.5 and random.random() < 0.45:
        action = "explore"
    elif random.random() < 0.12:
        action = "talk"

    # ── Goal-driven movement ──
    target = agent.get("headless_target")
    if target is None:
        target = list(_find_poi(agent_id, action))
        agent["headless_target"] = target

    tx, ty = target
    reached = abs(px - tx) <= 1 and abs(py - ty) <= 1
    if reached:
        agent["headless_target"] = None
        nx, ny = px, py
    else:
        nx, ny = _step_towards(px, py, tx, ty)
    body["position"] = [nx, ny]

    # ── Action event when at the target ──
    action_event = None
    if reached and action != "idle":
        if action == "rest":
            action_event = {"type": "action", "action": "rest", "result": {"success": True},
                            "time": tick, "agent_position": [nx, ny]}
            body["energy"] = min(100.0, body.get("energy", 100) + 3.0)
        elif action == "talk":
            npc = next((n for n in agent.get("world_snapshot", {}).get("npcs", [])
                        if abs(n["position"][0] - nx) <= 2 and abs(n["position"][1] - ny) <= 2), None)
            action_event = {"type": "action", "action": "talk", "npc_id": npc["id"] if npc else "someone",
                            "result": {"success": True}, "time": tick, "agent_position": [nx, ny]}
            e["trust"] = min(1.0, e["trust"] + 0.02)
        elif action == "explore":
            action_event = {"type": "action", "action": "explore",
                            "result": {"success": True}, "time": tick, "agent_position": [nx, ny], "novel": True}

    # Run the standard perception pipeline on the synthetic perception
    perception = _build_headless_perception(agent_id, tick, action_event)
    _update_hormones(agent_id, body)
    _update_emotions(agent_id, perception)
    _update_working_memory(agent_id, perception)
    _check_memory_formation(agent_id, perception)
    _update_self_model(agent_id, perception)

    # Passive energy drain
    body["energy"] = max(0.0, body["energy"] - 0.35)
    if body["energy"] < 25:
        body["stress"] = min(100.0, body["stress"] + 0.3)

    # Store the snapshot for observers
    snap = agent.get("world_snapshot", {})
    snap["tick"] = tick
    snap["time_of_day"] = perception.time_of_day
    snap["agent_position"] = [nx, ny]
    if action_event:
        events = snap.setdefault("recent_events", [])
        events.append(action_event)
        snap["recent_events"] = events[-50:]

    # Occasional inner monologue
    if random.random() < 0.25:
        _add_thought(agent_id, _inner_thought(agent_id))

    agent["headless_ticks"] += 1
    return tick


def _start_sleep(agent_id: str):
    """Begin a sleep cycle: dream with divine whispers, then recover"""
    agent = agent_states[agent_id]
    if agent.get("sleeping"):
        return
    agent["sleeping"] = True
    agent["sleep_ticks_remaining"] = SLEEP_DURATION_TICKS

    _add_thought(agent_id, "Глаза закрываются... я засыпаю.")
    snap = agent.get("world_snapshot", {})
    snap.setdefault("recent_events", []).append({
        "type": "sleep", "action": "sleep", "summary": "Kato засыпает",
        "time": agent["body"].get("tick", 0),
        "agent_position": agent["body"].get("position", [12, 8])
    })

    # Process the dream immediately (whispers + memory consolidation)
    whispers = [w for w in divine_whispers
                if w["agent_id"] == agent_id and not w.get("processed_in_dream")]
    dream = _generate_dream(agent_id, snap.get("recent_events", [])[-10:],
                            agent["emotions"], whispers)
    for w in whispers:
        w["processed_in_dream"] = True
    _update_self_model_from_dream(agent_id, dream)

    # Queue consolidation (async fire-and-forget)
    recent_episodic = [m for m in memory_store[agent_id]["episodic"]
                       if m.get("time", 0) > agent.get("last_sleep_tick", 0)
                       and m.get("importance", 0) > 0.5]
    if recent_episodic:
        asyncio.get_event_loop().create_task(_consolidate_memories(agent_id, recent_episodic))
        _form_autobiographical_entry(agent_id, recent_episodic)
        agent["last_sleep_tick"] = max(m.get("time", 0) for m in recent_episodic)

    # Dream insights become waking thoughts
    for insight in dream.get("insights", [])[:2]:
        agent["thoughts"].append({"tick": agent["body"].get("tick", 0),
                                  "text": "Мне приснилось: " + insight, "from_dream": True})
    agent["thoughts"] = agent["thoughts"][-THOUGHT_HISTORY:]


def _sleep_tick(agent_id: str):
    """One tick of sleep: recover energy, calm stress"""
    agent = agent_states[agent_id]
    body = agent["body"]
    body["energy"] = min(100.0, body.get("energy", 0) + 12.0)
    body["stress"] = max(0.0, body.get("stress", 0) - 8.0)
    body["comfort"] = min(100.0, body.get("comfort", 0) + 5.0)
    agent["sleep_ticks_remaining"] -= 1


def _wake_up(agent_id: str):
    """End sleep cycle"""
    agent = agent_states[agent_id]
    agent["sleeping"] = False
    agent["sleep_ticks_remaining"] = 0
    _add_thought(agent_id, "Я проснулась. Что-то изменилось... или это просто утро?")
    snap = agent.get("world_snapshot", {})
    snap.setdefault("recent_events", []).append({
        "type": "wake", "action": "wake", "summary": "Kato проснулась",
        "time": agent["body"].get("tick", 0),
        "agent_position": agent["body"].get("position", [12, 8])
    })


async def _reflect(agent_id: str):
    """Periodic reflection: consolidate salient events into semantic memory"""
    agent = agent_states[agent_id]
    mem = memory_store[agent_id]

    new_salient = [m for m in mem["episodic"]
                   if m.get("time", 0) > agent.get("last_reflection_tick", 0)
                   and m.get("importance", 0) > 0.55]
    if not new_salient:
        return

    await _consolidate_memories(agent_id, new_salient)
    agent["last_reflection_tick"] = max(m.get("time", 0) for m in new_salient)

    # Draw a lesson from the most important event (LLM when available)
    top = max(new_salient, key=lambda m: m.get("importance", 0))
    if LLM_CONFIG.get("enabled"):
        try:
            lesson = await _llm_reflect_lesson(agent_id, top)
            _add_thought(agent_id, "Оглядываясь назад: " + lesson)
            return
        except Exception as exc:
            logger.warning(f"LLM reflection failed: {exc}")

    what = top.get("what", "")
    if "не получилось" in what or (top.get("tags") and "failure" in top.get("tags")):
        _add_thought(agent_id, "Почему не получилось? В следующий раз попробую иначе.")
    elif "книг" in what or "чита" in what:
        _add_thought(agent_id, "Книги — как окна. За каждым что-то есть.")
    elif top.get("who"):
        _add_thought(agent_id, f"Кажется, {top['who']} — хороший. Мне с ними спокойно.")
    else:
        _add_thought(agent_id, "Оглядываясь назад, я вижу, чему научилась.")


async def _daemon_tick(agent_id: str):
    """One daemon tick for one agent: sleep management + autonomous life + consciousness modules"""
    agent = agent_states[agent_id]

    # 1. Sleep cycle in progress → just progress it
    if agent.get("sleeping"):
        _sleep_tick(agent_id)
        if agent.get("sleep_ticks_remaining", 0) <= 0:
            _wake_up(agent_id)
        return

    # 2. Headless mode: no live client for a while
    now = time.time()
    headless = (now - agent.get("last_perception_real_time", 0.0)) > HEADLESS_TIMEOUT

    if headless:
        tick = _headless_step(agent_id)
        # Periodic reflection
        if agent["headless_ticks"] % REFLECT_EVERY_TICKS == 0:
            await _reflect(agent_id)
        # Sleep when exhausted
        if agent["body"].get("energy", 100) < SLEEP_ENERGY_THRESHOLD:
            _start_sleep(agent_id)
    else:
        # Connected mode: only manage sleep based on reported energy
        if agent["body"].get("energy", 100) < SLEEP_ENERGY_THRESHOLD and not agent.get("sleeping"):
            _start_sleep(agent_id)

    # 3. Portal conversation: Kato checks the Distant Window for messages
    try:
        await _portal_maybe_reply(agent_id)
    except Exception as exc:
        logger.warning(f"Portal reply check failed for {agent_id}: {exc}")

    # 4. CONSCIOUSNESS MODULES INTEGRATION
    try:
        await _consciousness_tick(agent_id, headless)
    except Exception as exc:
        logger.warning(f"Consciousness tick failed for {agent_id}: {exc}")


async def _consciousness_tick(agent_id: str, headless: bool):
    """Run all consciousness modules for one tick"""
    try:
        # Initialize modules if needed
        modules = _init_consciousness_modules(agent_id)
        logger.info(f"Consciousness modules initialized for {agent_id}: {list(modules.keys())}")
    except Exception as exc:
        logger.error(f"Module init failed for {agent_id}: {exc}", exc_info=True)
        return
    
    agent = agent_states[agent_id]
    perception = agent.get("world_snapshot", {})
    body = agent.get("body", {})
    emotions = agent.get("emotions", {})
    goals = agent.get("goals", {})
    beliefs = agent.get("beliefs", {})
    
    # Ensure goals and beliefs are dicts
    if not isinstance(goals, dict):
        goals = {}
        agent["goals"] = goals
    if not isinstance(beliefs, dict):
        beliefs = {}
        agent["beliefs"] = beliefs
    
    # Log module status
    for name, mod in modules.items():
        if mod is None:
            logger.warning(f"Module {name} is None!")
        else:
            logger.debug(f"Module {name}: {type(mod)}")
    
    try:
        # ---- PHENOMENAL ENGINE ----
        # Raw feels from interoception, prediction, memory, agency
        phenomenal_inputs = {
            "energy": body.get("energy", 50),
            "comfort": body.get("comfort", 50),
            "stress": body.get("stress", 50),
            "prediction_error": 0.0,  # will be filled by PP
            "memory_match": 0.5,
            "action_outcome_match": 0.5,
            "choice_availability": len([g for g in goals.values() if g.get("active", False)]),
            "social_presence": len(perception.get("nearby_npcs", [])),
        }
        phenomenal_state = modules["phenomenal"].step(phenomenal_inputs, "daemon_tick")
        # Store for other modules
        agent["phenomenal_state"] = {
            "dimensions": {d.value: v for d, v in phenomenal_state.dimensions.items()},
            "dominant": max(phenomenal_state.dimensions.items(), key=lambda x: x[1])[0].value,
            "intensity": max(phenomenal_state.dimensions.values()),
        }

        # ---- PREDICTIVE PROCESSING ----
        # Step hierarchical prediction, get surprise
        pp_result = modules["predictive_processing"].step(perception, goals)
        # Update phenomenal with prediction error
        total_surprise = sum(abs(e) for e in pp_result.get("recent_surprises", []))
        if total_surprise > 0:
            # Feed back to phenomenal (would need re-step, simplified here)
            pass
        # Get conscious access candidates (surprise → attention)
        gw_candidates = modules["predictive_processing"].get_conscious_access_candidates()

        # ---- GLOBAL WORKSPACE ----
        # Submit candidates from all sources
        gw_items = []
        
        # From predictive processing (surprise)
        for c in gw_candidates:
            item = modules["global_workspace"].submit(c["source"], c["content"], c["activation"])
            if item:
                gw_items.append(item)
        
        # From phenomenal (strong feelings)
        for dim, val in phenomenal_state.dimensions.items():
            if val > 0.7:
                item = modules["global_workspace"].submit(
                    f"phenomenal_{dim.value}",
                    {"dimension": dim.value, "value": val, "intensity": val},
                    val
                )
                if item:
                    gw_items.append(item)
        
        # From narrative (identity-relevant)
        ns = modules["narrative_self"]
        if ns.current_chapter and ns.current_chapter.identity_impact > 0.5:
            item = modules["global_workspace"].submit(
                "narrative_identity",
                {"chapter": ns.current_chapter.title, "impact": ns.current_chapter.identity_impact},
                ns.current_chapter.identity_impact
            )
            if item:
                gw_items.append(item)
        
        # Run competition and broadcast
        broadcast_items = modules["global_workspace"].competition_step(gw_items)
        for item in broadcast_items:
            packet = modules["global_workspace"].broadcast(item)
            # Broadcast to all modules (they would receive this)
            # For now, store in agent for dashboard
            agent.setdefault("conscious_broadcasts", []).append(packet)
            if len(agent["conscious_broadcasts"]) > 50:
                agent["conscious_broadcasts"] = agent["conscious_broadcasts"][-50:]

        # ---- METACOGNITION ----
        # Monitor confidence calibration, error awareness
        meta_state = modules["metacognition"].get_state()
        agent["metacognition_state"] = meta_state

        # ---- AGENCY ----
        # Counterfactual simulation for action selection
        agency_result = modules["agency"].step(perception, goals)
        agent["agency_result"] = agency_result
        # Selected action could be used for autonomous action
        if headless and agency_result.get("action"):
            # Could execute autonomous action here
            pass

        # ---- THEORY OF MIND ----
        # Update models of NPCs from perception
        for npc in perception.get("nearby_npcs", []):
            modules["theory_of_mind"].update_from_observation(npc["id"], {
                "type": npc.get("type", "npc"),
                "behavior": {"action": "idle", "goal": "unknown"},
                "context": {"position": npc.get("position")},
                "my_state": {"position": perception.get("agent_position")}
            })
        # Update Creator model
        modules["theory_of_mind"].update_creator_model({"text": "heartbeat"})

        # ---- NARRATIVE SELF ----
        # Add events to current chapter
        if modules["narrative_self"].current_chapter:
            for event in perception.get("recent_events", []):
                modules["narrative_self"].add_event_to_chapter(
                    event.get("id", str(time.time())),
                    event,
                    perception.get("tick", 0)
                )
        # Periodic autobiographical reasoning
        if headless and random.random() < 0.1:
            # Would trigger reasoning on salient memory
            pass

        # Update agent with module states for dashboard/API
        agent["consciousness_modules"] = {
            "global_workspace": modules["global_workspace"].get_conscious_state(),
            "predictive_processing": modules["predictive_processing"].get_state(),
            "metacognition": modules["metacognition"].get_state(),
            "agency": modules["agency"].get_state(),
            "theory_of_mind": modules["theory_of_mind"].get_state(),
            "narrative_self": modules["narrative_self"].get_state(),
            "phenomenal": modules["phenomenal"].get_state(),
            "social": modules["social"].get_state() if "social" in modules else {},
        }

        # ---- SOCIAL DRIVE ----
        # Social motivation, loneliness, need to share, bond tracking
        if "social" in modules:
            social_module = modules["social"]
            # Ensure agent has social state
            if "social" not in agent:
                agent["social"] = {}
            social_module.step(
                perception.get("tick", 0),
                perception,
                agent,
                memory_store.get(agent_id, {}),
                dream_engine=None  # could pass dream engine if available
            )
            # Record social state for dashboard
            agent["social_state"] = social_module.get_state()

            # Check for outgoing triggers and queue messages
            triggers = social_module.pending_triggers
            if triggers:
                selected = social_module.select_trigger(triggers)
                if selected:
                    # Generate message
                    conversation_memory = agent.get("conversation_memory", {})
                    message = await social_module.generate_outgoing_message(selected, agent, conversation_memory)
                    if message:
                        social_module.queue_message(message, selected)
                        # Mark trigger as handled
                        social_module.pending_triggers.remove(selected)

            # Handle outgoing queue
            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing
            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent
            pending = social_module.get_pending_messages()
            if pending:
                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")

            # Handle silence from creator
            if headless:
                worry_msg = social_module.handle_silence(perception.get("tick", 0))
                if worry_msg:
                    social_module.queue_message(worry_msg, SocialTrigger(
                        trigger_type=SocialTriggerType.LONELINESS,
                        reason="worry_about_creator",
                        priority=0.9
                    ))
    except Exception as exc:
        logger.error(f"Consciousness tick error for {agent_id}: {exc}", exc_info=True)


async def _background_daemon_loop():
    """Main daemon loop — runs forever, ticks every agent"""
    logger.info("Background daemon started")
    tick_count = 0
    while True:
        try:
            await asyncio.sleep(DAEMON_INTERVAL)
            tick_count += 1
            for agent_id in list(agent_states.keys()):
                try:
                    await _daemon_tick(agent_id)
                except Exception as exc:  # never let one agent kill the daemon
                    logger.warning(f"Daemon tick failed for {agent_id}: {exc}")
            # Periodic autosave (personality continuity)
            if tick_count % SAVE_EVERY_TICKS == 0:
                _save_state()
        except asyncio.CancelledError:
            logger.info("Background daemon stopped")
            _save_state()
            raise
        except Exception as exc:
            logger.error(f"Background daemon error: {exc}")


@app.on_event("startup")
async def _start_daemon():
    # Detect LLM backend (cloud key → DeepSeek; else local Ollama)
    global LLM_CONFIG
    LLM_CONFIG = _detect_llm()
    asyncio.get_event_loop().create_task(_background_daemon_loop())
    if LLM_CONFIG.get("enabled"):
        asyncio.get_event_loop().create_task(_llm_think_loop())


@app.post("/agent/{agent_id}/sleep")
async def force_sleep(agent_id: str):
    """Manually put the agent to sleep"""
    init_agent(agent_id)
    _start_sleep(agent_id)
    return {"status": "sleeping", "agent_id": agent_id}


@app.post("/agent/{agent_id}/wake")
async def force_wake(agent_id: str):
    """Manually wake the agent"""
    init_agent(agent_id)
    if agent_states[agent_id].get("sleeping"):
        _wake_up(agent_id)
    return {"status": "awake", "agent_id": agent_id}


# ──────────────────────────────────────────────────────────────
# PERSISTENCE (continuity of personality across restarts)
# ──────────────────────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATE_FILE = os.path.join(_DATA_DIR, "kato_state.json")
SAVE_EVERY_TICKS = 10           # daemon ticks between autosaves


def _serializable_memories(mem: Dict) -> Dict:
    """Drop non-serializable index (rebuilt on load)"""
    out = {k: v for k, v in mem.items() if k != "index"}
    return out


def _stringify_keys(obj):
    """Recursively convert non-primitive dict keys (e.g. PhenomenalDimension enums) to str.

    Fixes 'State save failed: keys must be str, int, float, bool or None'
    which silently broke persistence (no kato_state.json on disk).
    """
    if isinstance(obj, dict):
        return {
            (k if isinstance(k, (str, int, float, bool)) else str(k)): _stringify_keys(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_stringify_keys(i) for i in obj]
    return obj


def _save_state(path: str = None):
    try:
        path = path or os.path.join(_DATA_DIR, STATE_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = _stringify_keys({
            "saved_at": time.time(),
            "agents": {aid: agent for aid, agent in agent_states.items()},
            "self_models": self_model,
            "memories": {aid: _serializable_memories(mem) for aid, mem in memory_store.items()},
            "divine_whispers": divine_whispers,
            "quests": _quests,
            "dialogue_states": _dialogue_states
        })
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, default=str)
        os.replace(tmp, path)
        logger.info(f"State saved ({len(agent_states)} agents)")
    except Exception as exc:
        logger.warning(f"State save failed: {exc}")


def _load_state(path: str = None):
    try:
        path = path or os.path.join(_DATA_DIR, STATE_FILE)
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        for aid, agent in payload.get("agents", {}).items():
            agent_states[aid] = agent
            # Restore default snapshot if missing
            agent.setdefault("world_snapshot", {})
            # Legacy snapshots predate the portal/stairs objects — merge defaults
            snap = agent["world_snapshot"]
            if "objects" not in snap:
                snap["objects"] = []
            have_ids = {o.get("id") for o in snap["objects"]}
            for oid, opos, ostate in (("portal", [13, 4], "dormant"),
                                      ("stairs_basement", [15, 13], "closed")):
                if oid not in have_ids:
                    snap["objects"].append({"id": oid, "position": opos,
                                            "state": ostate,
                                            "type": "device" if oid == "portal" else "portal"})
            # Legacy states may lack body position
            agent.setdefault("body", {})
            agent["body"].setdefault("position", [12, 8])
            # Legacy states had goals as a list — normalize to dict
            if isinstance(agent.get("goals"), list):
                agent["goals"] = {g: {"priority": 0.5, "active": True} for g in agent["goals"]}
            agent.setdefault("npc_interactions", {})
        for aid, sm in payload.get("self_models", {}).items():
            self_model[aid] = sm
        for aid, mem in payload.get("memories", {}).items():
            mem["index"] = {
                "by_location": defaultdict(list), "by_npc": defaultdict(list),
                "by_emotion": defaultdict(list), "by_time": defaultdict(list),
                "by_tag": defaultdict(list)
            }
            memory_store[aid] = mem
            # Rebuild indices
            for m in mem.get("episodic", []):
                _index_memory(aid, m)
        global divine_whispers
        divine_whispers = payload.get("divine_whispers", [])
        _quests.update(payload.get("quests", {}))
        _dialogue_states.update(payload.get("dialogue_states", {}))
        logger.info(f"State loaded: {len(agent_states)} agents, {sum(len(m.get('episodic', [])) for m in memory_store.values())} memories")
    except Exception as exc:
        logger.warning(f"State load failed (starting fresh): {exc}")


@app.on_event("startup")
async def _load_on_startup():
    _load_state()


@app.on_event("shutdown")
async def _save_on_shutdown():
    _save_state()


@app.post("/admin/save")
async def admin_save():
    """Manually trigger state save"""
    _save_state()
    return {"status": "saved", "file": STATE_FILE}


@app.post("/admin/reset")
async def admin_reset():
    """Wipe all agents and state (fresh start)"""
    agent_states.clear()
    memory_store.clear()
    self_model.clear()
    divine_whispers.clear()
    _quests.clear()
    _dialogue_states.clear()
    if os.path.isfile(STATE_FILE):
        os.remove(STATE_FILE)
    return {"status": "reset"}


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
    # Bind to localhost only — the brain is a private oracle, not a public service.
    # Set KATO_API_TOKEN to require X-Api-Token on all stateful endpoints.
    uvicorn.run(app, host="127.0.0.1", port=8080)