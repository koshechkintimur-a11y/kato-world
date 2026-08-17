"""Learning: value learning from action outcomes (TD-style)."""


def learn_from_action(agent_id: str, result) -> None:
    """Outcomes shift goal priorities and values. `result` is an ActionResult."""
    from brain_core.cognition import _bs
    bs = _bs()

    agent = bs.agent_states[agent_id]
    action = result.action
    success = result.success
    sm = bs.self_model[agent_id]
    goals = sm["goals"]
    values = sm["values"]

    def shift_goal(name, delta):
        if name in goals:
            goals[name]["priority"] = min(1.0, max(0.0, goals[name]["priority"] + delta))
            goals[name]["active"] = goals[name]["priority"] > 0.15

    def shift_value(name, delta):
        if name in values:
            values[name] = min(1.0, max(0.0, values[name] + delta))

    lr = 0.03 if success else 0.015  # successes teach more than failures
    if action in ("explore", "investigate", "plan_explore", "open_door"):
        shift_goal("explore", lr if success else -lr)
        shift_value("curiosity", lr if success else -lr * 0.5)
    elif action in ("study", "read_book", "check_portal"):
        shift_goal("learn", lr if success else -lr)
        shift_value("curiosity", lr * 0.5 if success else 0)
    elif action in ("talk", "approach_npc", "seek_npc", "ask_help"):
        shift_goal("social", lr if success else -lr)
        shift_value("kindness", lr if success else -lr * 0.5)
    elif action in ("rest", "sleep", "secure_resources"):
        shift_goal("survive", lr if success else 0)
        shift_value("safety", lr if success else -lr * 0.5)
    if not success and action not in ("rest", "sleep"):
        shift_value("safety", lr * 0.5)  # failures teach caution

    if action == "sleep" and success:
        bs._record_belief(agent_id, "world_is_safe", delta=0.05, reason="успешное действие", origin="experience")
    if action == "talk" and success:
        bs._record_belief(agent_id, "outside_exists", delta=0.02, reason="успешное действие", origin="experience")

    if success:
        agent["hormones"]["reward"] = min(100.0, agent["hormones"]["reward"] + 5.0)
    else:
        agent["hormones"]["stress"] = min(100.0, agent["hormones"]["stress"] + 10.0)


def create_learning_module(agent_id: str):
    """Factory for learning module (stateless, returns function reference)"""
    return {"learn_from_action": learn_from_action, "agent_id": agent_id}
