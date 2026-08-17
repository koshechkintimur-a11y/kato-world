#!/usr/bin/env python3
"""Kato World — Experimental Protocol (v0.2)
Run:  python3 experiment.py          (needs no server, no LLM)

Experiment 001 — Personality emergence:  N identical agents, different first
  100 experiences → measure divergence of goals/values/beliefs/emotions.
Experiment 002 — Memory consolidation:   agent with sleep vs without →
  retention (episodic kept) and generalization (semantic knowledge).
Experiment 003 — Creator influence:      no whisper / direct whisper /
  whisper-through-dream → belief stability over time.
"""
import copy
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_server as bs

N_AGENTS = 10
N_TICKS = 100
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "experiment_report.json")


def fresh(agent_id):
    bs.agent_states.clear()
    bs.self_model.clear()
    bs.memory_store.clear()
    bs.init_agent(agent_id)
    return agent_id


def tick(agent_id, stress=0, energy=90, npcs=(), objects=(), events=(), action_result=None):
    p = bs.PerceptionPayload(
        agent_id=agent_id, tick=random.randint(1, 10**6), time_of_day=0.4,
        agent={"position": [12, 8], "energy": energy, "comfort": 70,
               "stress": stress, "integrity": 100, "temperature": 22},
        nearby_objects=list(objects), nearby_npcs=[dict(n) for n in npcs],
        recent_events=list(events))
    bs.agent_states[agent_id]["body"] = dict(p.agent)
    bs._update_hormones(agent_id, p.agent)
    bs._update_emotions(agent_id, p)
    bs._check_memory_formation(agent_id, p)
    if action_result:
        act, ok = action_result
        bs._learn_from_action(agent_id, bs.ActionResult(
            agent_id=agent_id, tick=p.tick, action=act,
            params={}, result={"success": ok}, success=ok))


def run_experiment_001():
    """Same architecture, same start, different experiences → divergence?"""
    profiles = {}
    for i in range(N_AGENTS):
        aid = f"kato_{i}"
        fresh(aid)
        # Divergent experience regimes
        for t in range(N_TICKS):
            if i % 3 == 0:      # safe & social life
                tick(aid, stress=5, npcs=[{"id": "teacher", "position": [10, 6], "mood": "calm"}],
                     events=[{"type": "dialogue", "what": "разговор с учителем"}],
                     action_result=("talk", True))
            elif i % 3 == 1:    # stressful, failing life
                tick(aid, stress=60 + (t % 30), energy=40,
                     events=[{"type": "action", "action": "open_door", "result": {"success": False}}],
                     action_result=("open_door", False))
            else:               # curious, exploring life
                tick(aid, stress=10,
                     objects=[{"id": "unknown_obj", "position": [3, 3], "state": "unknown"}],
                     events=[{"type": "discovery", "what": "новая находка"}],
                     action_result=("explore", True))
        sm = bs.self_model[aid]
        profiles[aid] = {
            "goals": {k: round(v["priority"], 2) for k, v in sm["goals"].items()},
            "values": {k: round(v, 2) for k, v in sm["values"].items()},
            "beliefs": {k: round(v, 2) for k, v in sm["beliefs"].items()},
            "emotions": {k: round(v, 2) for k, v in bs.agent_states[aid]["emotions"].items()},
        }
    # Divergence = mean pairwise distance of goal/value vectors
    def vec(p): return [p["goals"].get(k, 0) for k in ("explore", "learn", "survive", "social")] + \
                      [p["values"].get(k, 0) for k in ("curiosity", "safety", "kindness")]
    div = sum(abs(a - b) for i in range(N_AGENTS) for j in range(i + 1, N_AGENTS)
              for a, b in zip(vec(profiles[f"kato_{i}"]), vec(profiles[f"kato_{j}"]))) / (N_AGENTS * (N_AGENTS - 1) / 2)
    return {"agents": profiles, "mean_pairwise_divergence": round(div, 4)}


def run_experiment_002():
    """Sleep consolidates: retention vs generalization."""
    out = {"without_sleep": {}, "with_sleep": {}}
    # A: no consolidation
    fresh("no_sleep")
    for t in range(60):
        tick("no_sleep", events=[{"type": "discovery", "what": "новая находка"}],
             action_result=("explore", True))
    mem_a = bs.memory_store["no_sleep"]
    out["without_sleep"] = {"episodic": len(mem_a["episodic"]), "semantic": len(mem_a["semantic"])}

    # B: with consolidation (sleep process)
    fresh("with_sleep")
    for t in range(60):
        tick("with_sleep", events=[{"type": "discovery", "what": "новая находка"}],
             action_result=("explore", True))
    # Vivid memories (importance > 0.7) — like emotionally strong events
    mem_b = bs.memory_store["with_sleep"]
    for i in range(10):
        mem_b["episodic"].append({"id": f"vivid_{i}", "time": 1000 + i,
                                  "what": "I found a glowing object by the window",
                                  "importance": 0.85, "emotion": {"curiosity": 0.8},
                                  "tags": ["discovery"]})
    # simulate sleep: consolidate top salient
    import asyncio
    salient = [m for m in mem_b["episodic"] if m.get("importance", 0) > 0.5]
    if salient:
        asyncio.run(bs._consolidate_memories("with_sleep", salient))
    out["with_sleep"] = {"episodic": len(mem_b["episodic"]), "semantic": len(mem_b["semantic"]),
                         "consolidated": len(salient)}
    return out


def run_experiment_003():
    """How beliefs form: none / direct injection / whisper-through-dream."""
    out = {}
    # A: no whisper — belief only from experience
    fresh("no_whisper")
    for t in range(40):
        tick("no_whisper", events=[{"type": "action", "action": "talk", "result": {"success": True}}])
    out["no_whisper"] = round(bs.self_model["no_whisper"]["beliefs"].get("outside_exists", 0), 3)

    # B: direct belief injection (simulates hard-coded belief change)
    fresh("direct")
    bs._record_belief("direct", "outside_exists", delta=0.3, reason="direct", origin="experience")
    out["direct"] = round(bs.self_model["direct"]["beliefs"].get("outside_exists", 0), 3)

    # C: whisper through dream (the real pipeline)
    fresh("dreamed")
    dream = {"insights": ["За окном есть огромный мир, полный света"],
             "divine_whispers": [{"content": "За окном есть огромный мир", "interpreted_as": "Свет приходит из-за окна"}]}
    bs._update_self_model_from_dream("dreamed", dream)
    out["whisper_through_dream"] = round(bs.self_model["dreamed"]["beliefs"].get("outside_exists", 0), 3)
    out["dream_meta_origin"] = bs.self_model["dreamed"]["belief_meta"]["outside_exists"]["origin"]
    return out


def main():
    random.seed(42)
    report = {
        "experiment_001_personality_emergence": run_experiment_001(),
        "experiment_002_memory_consolidation": run_experiment_002(),
        "experiment_003_creator_influence": run_experiment_003(),
    }
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("=== EXPERIMENT 001: дивергенция личностей ===")
    e1 = report["experiment_001_personality_emergence"]
    print(f"  mean pairwise divergence: {e1['mean_pairwise_divergence']}")
    for i in (0, 1, 2):
        p = e1["agents"][f"kato_{i}"]
        print(f"  kato_{i}: goals={p['goals']} values={p['values']}")
    print("=== EXPERIMENT 002: консолидация ===")
    e2 = report["experiment_002_memory_consolidation"]
    print(f"  без сна:  episodic={e2['without_sleep']['episodic']}, semantic={e2['without_sleep']['semantic']}")
    print(f"  со сном:  episodic={e2['with_sleep']['episodic']}, semantic={e2['with_sleep']['semantic']} (консолидировано {e2['with_sleep'].get('consolidated')})")
    print("=== EXPERIMENT 003: влияние создателя ===")
    e3 = report["experiment_003_creator_influence"]
    print(f"  без шёпота:      outside_exists = {e3['no_whisper']}")
    print(f"  прямой впрыск:   outside_exists = {e3['direct']}")
    print(f"  шёпот через сон: outside_exists = {e3['whisper_through_dream']} (origin={e3['dream_meta_origin']})")
    print(f"\nОтчёт: {REPORT_PATH}")


if __name__ == "__main__":
    main()
