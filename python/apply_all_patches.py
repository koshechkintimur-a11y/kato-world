# Read the file
with open('brain_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix PORTAL_REPLY_COOLDOWN_SEC
content = content.replace(
    'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies',
    'PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)'
)

# 2. Add conversation_memory to init_agent
old_revelation = '''            # Creator revelation protocol state
            "revelation": {
                "stage": "not_started",   # not_started -> offered -> in_contact -> integrated
                "offer_tick": None,
                "choice": None,
                "journal": []
            }
        }'''

new_revelation = '''            # Creator revelation protocol state
            "revelation": {
                "stage": "not_started",   # not_started -> offered -> in_contact -> integrated
                "offer_tick": None,
                "choice": None,
                "journal": []
            },
            # Conversation memory with Creator (Telegram)
            "conversation_memory": {
                "summary": "",
                "key_topics": [],
                "emotional_arc": [],
                "promises": [],
                "last_conversation": {}
            }
        }'''

content = content.replace(old_revelation, new_revelation)

# 3. Add Social + Conversation endpoints after _portal_maybe_reply function
old_end = '''    _portal_journal(agent_id, {"who": "kato", "text": f"Kato ответила Дальнему другу: \u00ab{reply_text[:60]}\u00bb"})
    return msg


def _portal_reply_template(text: str) -> str:'''

new_end = '''    _portal_journal(agent_id, {"who": "kato", "text": f"Kato ответила Дальнему другу: \u00ab{reply_text[:60]}\u00bb"})
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


def _portal_reply_template(text: str) -> str:'''

content = content.replace(old_end, new_end)

# 4. Update _init_consciousness_modules to include social
old_init = '''    from brain_core import (
        create_global_workspace,
        create_predictive_processor,
        create_metacognition_engine,
        create_agency_engine,
        create_theory_of_mind,
        create_narrative_self,
        create_phenomenal_engine,
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
        }'''

new_init = '''    from brain_core import (
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
        }'''

content = content.replace(old_init, new_init)

# 5. Update _consciousness_tick to include Social Drive
old_tick_end = '''        # Update agent with module states for dashboard/API
        agent["consciousness_modules"] = {
            "global_workspace": modules["global_workspace"].get_conscious_state(),
            "predictive_processing": modules["predictive_processing"].get_state(),
            "metacognition": modules["metacognition"].get_state(),
            "agency": modules["agency"].get_state(),
            "theory_of_mind": modules["theory_of_mind"].get_state(),
            "narrative_self": modules["narrative_self"].get_state(),
            "phenomenal": modules["phenomenal"].get_state(),
        }
    except Exception as exc:
        logger.error(f"Consciousness tick error for {agent_id}: {exc}", exc_info=True)'''

new_tick_end = '''        # Update agent with module states for dashboard/API
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
                    message = social_module.generate_outgoing_message(selected, agent, conversation_memory)
                    if message:
                        social_module.queue_message(message, selected)
                        # Mark trigger as handled
                        social_module.pending_triggers.remove(selected)

            # Handle outgoing queue
            for message in social_module.get_pending_messages():
                # In headless mode, we could send to telegram outbound
                # For now, just log and mark as sent
                social_module.mark_sent(message)
                logger.info(f"Social outgoing (queued): {message[:50]}...")

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
        logger.error(f"Consciousness tick error for {agent_id}: {exc}", exc_info=True)'''

content = content.replace(old_tick_end, new_tick_end)

# Write back
with open('brain_server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('All patches applied successfully!')