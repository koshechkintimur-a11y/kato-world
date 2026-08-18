if "social" in sm["goals"]:
        sm["goals"]["social"]["priority"] = min(1.0, sm["goals"]["social"]["priority"] + 0.01)
    _portal_journal(agent_id, {"who": "kato", "text": f"Kato ответила Дальнему другу: \u00ab{reply_text[:60]}\u00bb"})
    return msg


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# SOCIAL OUTGOING (Telegram bridge) + CONVERSATION MEMORY
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

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
    # msg_id format: msg_{index}
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