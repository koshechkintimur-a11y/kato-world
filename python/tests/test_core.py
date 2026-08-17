#!/usr/bin/env python3
"""Kato World — core brain tests (no external server needed, no LLM).
Run:  python -m pytest tests/test_core.py -v
   or: python tests/test_core.py
Covers: emotion dynamics, System 2, memory consolidation, persistence,
revelation gating, belief provenance, safety/arousal fixes."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import brain_server as bs


def make_perception(agent_id="kato", tick=1, stress=0, energy=100, objects=None, npcs=None, events=None):
    return bs.PerceptionPayload(
        agent_id=agent_id,
        tick=tick,
        time_of_day=0.3,
        agent={"position": [12, 8], "energy": energy, "comfort": 70,
               "stress": stress, "integrity": 100, "temperature": 22},
        nearby_objects=objects or [],
        nearby_npcs=npcs or [],
        recent_events=events or []
    )


class TestEmotionDynamics(unittest.TestCase):
    def setUp(self):
        bs.agent_states.clear()
        bs.self_model.clear()
        bs.memory_store.clear()
        bs.init_agent("kato")

    def test_emotion_converges_to_drive(self):
        """Homeostatic model: emotion should converge toward its drive."""
        p = make_perception(stress=0, energy=100, tick=1)
        for i in range(200):
            p.tick = i
            bs.agent_states["kato"]["body"] = dict(p.agent)  # like /perception does
            bs._update_hormones("kato", p.agent)
            bs._update_emotions("kato", p)
        e = bs.agent_states["kato"]["emotions"]
        # Low stress + high comfort → joy should be meaningfully above 0 and stable
        self.assertGreater(e["joy"], 0.1)
        self.assertLess(e["fear"], 0.25)

    def test_fear_suppresses_curiosity(self):
        """Fear should suppress the curiosity drive."""
        p = make_perception(stress=90, energy=100, tick=1)
        for i in range(120):
            p.tick = i
            bs.agent_states["kato"]["body"] = dict(p.agent)
            bs._update_hormones("kato", p.agent)
            bs._update_emotions("kato", p)
        e = bs.agent_states["kato"]["emotions"]
        self.assertGreater(e["fear"], 0.3, "fear should rise under stress")
        self.assertLess(e["curiosity"], 0.5, "curiosity should be suppressed by fear")

    def test_arousal_decays_to_baseline(self):
        """Arousal must decay back toward baseline after stress drops (bug fix)."""
        p = make_perception(stress=90, tick=1)
        for i in range(150):
            p.tick = i
            bs.agent_states["kato"]["body"] = dict(p.agent)
            bs._update_hormones("kato", p.agent)
        h = bs.agent_states["kato"]["hormones"]
        self.assertGreater(h["arousal"], 0.35, "stress should raise arousal")
        # Now calm down
        p2 = make_perception(stress=0, tick=200)
        for i in range(300):
            p2.tick = 200 + i
            bs.agent_states["kato"]["body"] = dict(p2.agent)
            bs._update_hormones("kato", p2.agent)
        h2 = bs.agent_states["kato"]["hormones"]
        self.assertLess(h2["arousal"], 0.5, "arousal should decay back toward baseline")

    def test_attachment_is_per_agent(self):
        """Attachment counters live in agent state, not on the function (bug fix)."""
        p = make_perception(npcs=[{"id": "teacher", "position": [10, 6], "mood": "calm"}])
        for i in range(15):
            p.tick = i
            bs._update_emotions("kato", p)
        interactions = bs.agent_states["kato"].get("npc_interactions", {})
        self.assertEqual(interactions.get("teacher", 0), 15)
        self.assertFalse(hasattr(bs._update_emotions, "_npc_interactions"),
                         "legacy function attribute must not exist")


class TestSystem2(unittest.TestCase):
    def setUp(self):
        bs.agent_states.clear()
        bs.self_model.clear()
        bs.memory_store.clear()
        bs.init_agent("kato")

    def test_system2_does_not_crash_with_dict_goals(self):
        """Bug fix: agent['goals'] is a dict; System 2 must work."""
        agent = bs.agent_states["kato"]
        action, reason, conf = bs._system2_reason(agent, {})
        self.assertIn("type", action)
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)
        self.assertIsInstance(reason, str)

    def test_propose_endpoint_system2_path(self):
        """Force System 2 through the API: high stress must not 500."""
        from fastapi.testclient import TestClient
        client = TestClient(bs.app)
        r = client.post("/agent/register", json={
            "agent_id": "kato", "capabilities": ["perception"], "world_schema_version": 1})
        self.assertEqual(r.status_code, 200)
        resp = client.post("/action/propose", json={
            "agent_id": "kato", "tick": 10, "working_memory": {},
            "agent": {"position": [12, 8], "energy": 10, "comfort": 30, "stress": 80,
                      "integrity": 100, "temperature": 22},
            "nearby_objects": [], "nearby_npcs": [], "recent_events": []
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("action", data)


class TestMemoryConsolidation(unittest.TestCase):
    def setUp(self):
        bs.agent_states.clear()
        bs.self_model.clear()
        bs.memory_store.clear()
        bs.init_agent("kato")

    def test_salient_events_consolidate_to_semantic(self):
        """Events above importance threshold move to semantic memory."""
        import asyncio
        mem = bs.memory_store["kato"]
        mem["episodic"] = [
            {"id": "e1", "time": 10, "what": "I opened the door and saw a new light", "importance": 0.8,
             "emotion": {"curiosity": 0.7}, "tags": ["discovery"]},
            {"id": "e2", "time": 11, "what": "it rained", "importance": 0.2,
             "emotion": {}, "tags": []}
        ]
        asyncio.run(bs._consolidate_memories("kato", mem["episodic"]))
        # e1 (salient) should produce semantic knowledge; e2 should not
        self.assertGreaterEqual(len(mem["semantic"]), 1)
        self.assertTrue(any("двер" in s.get("knowledge", "").lower() for s in mem["semantic"]))


class TestPersistence(unittest.TestCase):
    def setUp(self):
        bs.agent_states.clear()
        bs.self_model.clear()
        bs.memory_store.clear()
        bs.init_agent("kato")
        bs._record_belief("kato", "outside_exists", delta=0.3, reason="test", origin="portal")
        bs.memory_store["kato"]["episodic"].append(
            {"id": "e1", "time": 1, "what": "тест", "importance": 0.9, "emotion": {}, "tags": ["test"]})

    def test_save_load_roundtrip(self):
        """Save → load must restore beliefs, memories, goals dict, provenance."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            bs._save_state(path)
            bs.agent_states.clear()
            bs.self_model.clear()
            bs.memory_store.clear()
            bs._load_state(path)
            sm = bs.self_model["kato"]
            self.assertGreater(sm["beliefs"].get("outside_exists", 0), 0.2)
            self.assertEqual(sm["belief_meta"]["outside_exists"]["origin"], "portal")
            self.assertEqual(len(bs.memory_store["kato"]["episodic"]), 1)
            self.assertIsInstance(bs.agent_states["kato"]["goals"], dict)
            self.assertIn("npc_interactions", bs.agent_states["kato"])

    def test_legacy_list_goals_normalized(self):
        """Loading a legacy state with list-goals must normalize (bug fix)."""
        legacy = {
            "agents": {"kato": {"body": {"position": [1, 1]}, "goals": ["explore", "learn"]}},
            "self_models": {}, "memories": {}
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(legacy, f)
            bs.agent_states.clear()
            bs._load_state(path)
            self.assertIsInstance(bs.agent_states["kato"]["goals"], dict)
            self.assertIn("explore", bs.agent_states["kato"]["goals"])


class TestRevelationGating(unittest.TestCase):
    def setUp(self):
        bs.agent_states.clear()
        bs.self_model.clear()
        bs.memory_store.clear()
        bs.init_agent("kato")
        bs.revelation_journal = {}  # reset per-test journal

    def test_terminal_stays_dark_until_ready(self):
        """Fresh agent: terminal must refuse until maturity threshold (gating fix)."""
        from fastapi.testclient import TestClient
        client = TestClient(bs.app)
        r = client.post("/agent/register", json={
            "agent_id": "kato", "capabilities": ["perception"], "world_schema_version": 1})
        r = client.post("/agent/kato/revelation/begin")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("status"), "not_ready",
                         f"fresh agent must not get an offer, got: {data.get('status')}")
        self.assertEqual(bs.agent_states["kato"]["revelation"]["stage"], "not_started")

    def test_maturity_safety_uses_body_stress(self):
        """Bug fix: safety must drop when body stress is high."""
        bs.agent_states["kato"]["body"]["stress"] = 95
        a = bs._maturity_assessment("kato")
        self.assertLess(a["components"]["safety"], 0.7,
                        "high body stress must lower the safety component")


class TestBeliefProvenance(unittest.TestCase):
    def setUp(self):
        bs.agent_states.clear()
        bs.self_model.clear()
        bs.memory_store.clear()
        bs.init_agent("kato")

    def test_whisper_dream_marks_external_injection(self):
        """Whispers in dreams → belief_meta marks creator_injection (observer-only)."""
        dream = {
            "insights": ["За окном есть огромный мир, полный света"],
            "divine_whispers": [{"content": "За окном есть огромный мир", "interpreted_as": "Свет приходит из-за окна"}]
        }
        bs._update_self_model_from_dream("kato", dream)
        meta = bs.self_model["kato"]["belief_meta"]
        self.assertEqual(meta["outside_exists"]["origin"], "creator_injection")
        self.assertTrue(meta["outside_exists"]["external_injection"])
        self.assertGreaterEqual(len(meta["outside_exists"]["history"]), 1)

    def test_experience_belief_not_marked_external(self):
        bs._record_belief("kato", "world_is_safe", delta=0.05, reason="действие", origin="experience")
        meta = bs.self_model["kato"]["belief_meta"]["world_is_safe"]
        self.assertFalse(meta["external_injection"])
        self.assertEqual(meta["origin"], "experience")


if __name__ == "__main__":
    unittest.main(verbosity=2)
