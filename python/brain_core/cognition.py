"""Cognition: System 2 LLM planner (slow deliberation) + metacognitive triggers."""

PLANNER_ACTION_ALLOWLIST = [
    "explore", "rest", "sleep", "talk", "study", "approach_npc", "seek_npc",
    "investigate", "idle", "retreat", "ask", "secure_resources", "read_book",
    "open_door", "plan_explore", "withdraw", "check_portal"
]

PLANNER_PROMPT = (
    "Ты — когнитивное ядро Kato, цифрового существа в маленьком мире-доме. "
    "Ты выбираешь, что Kato сделает дальше. Учитывай её тело, эмоции, цели и убеждения.\n"
    "Доступные действия: " + ", ".join(PLANNER_ACTION_ALLOWLIST) + ".\n"
    "Ответь ТОЛЬКО валидным JSON без пояснений, строго в формате:\n"
    '{"action": "<одно из доступных>", "reason": "<почему, по-русски, 1 фраза>", "confidence": <0.0-1.0>}'
)


def parse_planner_json(text: str) -> dict:
    """Extract and validate the planner's JSON (tolerates stray text)."""
    import json
    import re
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in planner reply")
    data = json.loads(m.group(0))
    action = str(data.get("action", "")).strip()
    if action not in PLANNER_ACTION_ALLOWLIST:
        raise ValueError(f"action not in allowlist: {action}")
    conf = float(data.get("confidence", 0.5))
    conf = min(1.0, max(0.0, conf))
    reason = str(data.get("reason", "")).strip()[:160]
    return {"type": action, "reason": reason, "confidence": conf}


def _bs():
    """Return the running brain module. When brain_server.py runs as __main__,
    a plain `import brain_server` would create a SECOND instance with empty
    state — so prefer sys.modules['__main__'] when it looks like the brain."""
    import sys
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "self_model") and hasattr(main, "agent_states"):
        return main
    import brain_server
    return brain_server


async def system2_llm(agent: dict, working_memory: dict) -> tuple:
    """LLM-based System 2 planner: returns (action_dict, reasoning, confidence)."""
    bs = _bs()

    sm = bs.self_model[agent.get("_agent_id", "kato")]
    e = agent["emotions"]
    body = agent["body"]
    goals = ", ".join(g for g, i in sorted(sm["goals"].items(),
                                           key=lambda kv: kv[1].get("priority", 0), reverse=True)
                      if i.get("active")) or "покоя"
    beliefs = "; ".join(f"{k}={v:.2f}" for k, v in sm["beliefs"].items())
    recent = working_memory.get("recent_events", [])[-5:]
    ctx = "; ".join(str(ev.get("action", ev.get("what", "")))[:60] for ev in recent) or "всё спокойно"

    user = (f"Тело: энергия={body.get('energy', 100):.0f}, стресс={body.get('stress', 0):.0f}, "
            f"комфорт={body.get('comfort', 70):.0f}.\n"
            f"Эмоции: страх={e.get('fear', 0):.2f}, радость={e.get('joy', 0):.2f}, "
            f"любопытство={e.get('curiosity', 0):.2f}, доверие={e.get('trust', 0):.2f}, "
            f"гнев={e.get('anger', 0):.2f}.\n"
            f"Цели: {goals}. Убеждения: {beliefs}.\n"
            f"Недавнее: {ctx}.\n"
            "Какое действие выбрать и почему?")

    reply = await bs._llm_complete(PLANNER_PROMPT, user, max_tokens=120)
    plan = parse_planner_json(reply)
    return {"type": plan["type"]}, plan["reason"], plan["confidence"]


def thought_pressure(agent_id: str) -> float:
    """Metacognitive trigger: how much Kato *needs* to think right now.
    uncertainty + unresolved goals + emotional salience + novelty + conflict."""
    from brain_core.cognition import _bs
    bs = _bs()

    agent = bs.agent_states[agent_id]
    e = agent["emotions"]
    sm = bs.self_model[agent_id]
    body = agent["body"]
    p = 0.0

    baseline = {"joy": 0.1, "fear": 0.05, "anger": 0.0, "sadness": 0.0,
                "curiosity": 0.3, "trust": 0.5, "attachment": 0.0}
    salience = sum(abs(e.get(k, 0) - v) for k, v in baseline.items()) / 7.0
    p += salience * 0.35

    active = [g for g, i in sm["goals"].items() if i.get("active")]
    p += min(0.25, len(active) * 0.05)

    if e.get("fear", 0) > 0.4 and e.get("curiosity", 0) > 0.4:
        p += 0.2

    snap = agent.get("world_snapshot", {})
    novel = [o for o in snap.get("objects", []) if o.get("state") == "unknown"]
    p += min(0.2, len(novel) * 0.05)

    p += body.get("stress", 0) / 100.0 * 0.1

    return min(1.0, p)
