#!/usr/bin/env python3
"""Emotion system test - 3 scenarios: calm, stress, recovery"""
import json
import urllib.request

BASE = "http://localhost:8080"

def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get(path):
    with urllib.request.urlopen(BASE + path) as resp:
        return json.loads(resp.read())

def perception(tick, energy, comfort, stress, integrity, objects, npcs, events):
    return post("/perception", {
        "agent_id": "kato", "tick": tick, "time_of_day": 0.5,
        "agent": {"position": [12, 8], "energy": energy, "comfort": comfort,
                  "stress": stress, "integrity": integrity, "temperature": 22},
        "nearby_objects": objects, "nearby_npcs": npcs,
        "recent_events": events
    })

def show_state(label):
    d = get("/agent/kato/state")
    e = d["emotions"]
    m = d.get("mood", {})
    print(f"\n--- {label} ---")
    print(f"  body: energy={d['body']['energy']:.0f} comfort={d['body']['comfort']:.0f} stress={d['body']['stress']:.0f}")
    print(f"  emotions: joy={e['joy']:.2f} fear={e['fear']:.2f} anger={e['anger']:.2f} sadness={e['sadness']:.2f} cur={e['curiosity']:.2f} trust={e['trust']:.2f} attach={e['attachment']:.2f}")
    print(f"  mood: {m.get('label','?')} (val={m.get('valence',0):.2f} aro={m.get('arousal',0):.2f})")
    return d

# Reset agent (fresh register)
post("/agent/register", {"agent_id": "kato", "capabilities": ["perception"], "world_schema_version": 1})

# ── SCENARIO 1: Calm morning ──
print("=" * 50)
print("SCENARIO 1: Calm morning, teacher nearby, novel book")
perception(1, 90, 85, 5, 100,
           [{"id": "book", "position": [8, 4], "state": "unknown"}],
           [{"id": "teacher", "position": [10, 6], "mood": "calm"}],
           [{"type": "action", "action": "explore", "result": {"success": True}, "time": 1, "novel": True}])
d = show_state("After calm perception")
action = post("/action/propose", {"agent_id": "kato", "tick": 1, "working_memory": {}})
print(f"  action: {action['action']['type']} ({action['mode']}, conf={action['confidence']:.2f})")

# ── SCENARIO 2: Stress spike ──
print("=" * 50)
print("SCENARIO 2: Stress spike - locked door, failures, dark, alone")
perception(50, 30, 20, 85, 70,
           [{"id": "door_outside", "position": [12, 14], "state": "locked"}],
           [],
           [{"type": "action", "action": "open_door", "result": {"success": False, "reason": "locked"}, "time": 50},
            {"type": "action", "action": "try_terminal", "result": {"success": False, "reason": "broken"}, "time": 49}])
d = show_state("After stress")
action = post("/action/propose", {"agent_id": "kato", "tick": 50, "working_memory": {}})
print(f"  action: {action['action']['type']} ({action['mode']}, conf={action['confidence']:.2f})")

# ── SCENARIO 3: Recovery - rest, teacher comfort ──
print("=" * 50)
print("SCENARIO 3: Recovery - rest, teacher nearby, sleep restored")
perception(100, 95, 90, 5, 100,
           [{"id": "bed", "position": [4, 5], "state": "free"}],
           [{"id": "teacher", "position": [10, 6], "mood": "calm"}],
           [{"type": "action", "action": "sleep", "result": {"success": True}, "time": 100},
            {"type": "action", "action": "talk", "result": {"success": True}, "time": 99}])
d = show_state("After recovery")
action = post("/action/propose", {"agent_id": "kato", "tick": 100, "working_memory": {}})
print(f"  action: {action['action']['type']} ({action['mode']}, conf={action['confidence']:.2f})")

# ── Memory check: stress events should have HIGH salience ──
print("=" * 50)
mems = post("/memory/query", {"agent_id": "kato", "memory_type": "episodic", "limit": 10})
print(f"Episodic memories formed: {len(mems['memories'])}")
for m in mems["memories"]:
    print(f"  [{m['importance']:.2f}] {m['what']} (emotion: {max(m['emotion'], key=m['emotion'].get)})")
