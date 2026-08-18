# brain_server.py - Fixed _consciousness_tick function
# This is a complete replacement for the _consciousness_tick function
# Lines 3029-3235

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
        # Get conscious access candidates (surprise -> attention)
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
    except Exception as exc:
        logger.error(f"Consciousness tick error for {agent_id}: {exc}", exc_info=True)