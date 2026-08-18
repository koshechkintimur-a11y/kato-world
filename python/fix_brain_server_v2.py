#!/usr/bin/env python3
"""
Fix brain_server.py by reading the original and writing the complete fixed version.
This is more reliable than string replacement on such a large file.
"""

with open('brain_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We'll build the new file line by line
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # PATCH 1: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # PATCH 2: Add conversation_memory to init_agent
    # Find the revelation dict and insert conversation_memory before the closing brace of agent dict
    if '            # Creator revelation protocol state' in line:
        # Copy the revelation block
        j = i
        while j < len(lines) and '        }' not in lines[j]:
            new_lines.append(lines[j])
            j += 1
        # Now lines[j] should be the closing brace of the agent dict
        # Insert conversation_memory before it
        new_lines.append(lines[j-1])  # the "            }" of revelation
        new_lines.append('            # Conversation memory with Creator (Telegram)\n')
        new_lines.append('            "conversation_memory": {\n')
        new_lines.append('                "summary": "",\n')
        new_lines.append('                "key_topics": [],\n')
        new_lines.append('                "emotional_arc": [],\n')
        new_lines.append('                "promises": [],\n')
        new_lines.append('                "last_conversation": {}\n')
        new_lines.append('            },\n')
        new_lines.append(lines[j])  # the "        }" closing the agent dict
        i = j + 1
        continue
    
    # PATCH 3: Update _init_consciousness_modules to include social
    if '    from brain_core import (' in line:
        # Copy the import block
        while i < len(lines) and 'create_phenomenal_engine,' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now lines[i] has create_phenomenal_engine,
        new_lines[-1] = new_lines[-1].replace('create_phenomenal_engine,', 'create_phenomenal_engine,\n        create_social_drive,')
        i += 1
        # Copy until the dict entries
        while i < len(lines) and '"global_workspace":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Copy dict entries until phenomenal
        while i < len(lines) and '"phenomenal":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now lines[i] has phenomenal - replace with social added
        new_lines[-1] = new_lines[-1].replace(
            '"phenomenal": create_phenomenal_engine(agent_id),',
            '"phenomenal": create_phenomenal_engine(agent_id),\n            "social": create_social_drive(agent_id),'
        )
        i += 1
        continue
    
    # PATCH 3: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # PATCH 4: Update _consciousness_tick - find the consciousness_modules dict and add social
    if '        agent["consciousness_modules"] = {' in line:
        # Copy until we see the closing brace of the dict
        while i < len(lines) and '"phenomenal":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now add social to the dict
        new_lines[-1] = new_lines[-1].replace(
            '"phenomenal": modules["phenomenal"].get_state(),',
            '"phenomenal": modules["phenomenal"].get_state(),\n            "social": modules["social"].get_state() if "social" in modules else {},'
        )
        i += 1
        # Continue copying until we hit the "except Exception" line
        while i < len(lines) and 'except Exception as exc:' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now insert the Social Drive integration BEFORE the except block
        social_code = [
            '',
            '        # ---- SOCIAL DRIVE ----',
            '        # Social motivation, loneliness, need to share, bond tracking',
            '        if "social" in modules:',
            '            social_module = modules["social"]',
            '            # Ensure agent has social state',
            '            if "social" not in agent:',
            '                agent["social"] = {}',
            '            social_module.step(',
            '                perception.get("tick", 0),',
            '                perception,',
            '                agent,',
            '                memory_store.get(agent_id, {}),',
            '                dream_engine=None  # could pass dream engine if available',
            '            )',
            '            # Record social state for dashboard',
            '            agent["social_state"] = social_module.get_state()',
            '',
            '            # Check for outgoing triggers and queue messages',
            '            triggers = social_module.pending_triggers',
            '            if triggers:',
            '                selected = social_module.select_trigger(triggers)',
            '                if selected:',
            '                    # Generate message',
            '                    conversation_memory = agent.get("conversation_memory", {})',
            '                    message = social_module.generate_outgoing_message(selected, agent, conversation_memory)',
            '                    if message:',
            '                        social_module.queue_message(message, selected)',
            '                        # Mark trigger as handled',
            '                        social_module.pending_triggers.remove(selected)',
            '',
            '            # Handle outgoing queue',
            '            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing',
            '            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent',
            '            pending = social_module.get_pending_messages()',
            '            if pending:',
            '                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")',
            '',
            '            # Handle silence from creator',
            '            if headless:',
            '                worry_msg = social_module.handle_silence(perception.get("tick", 0))',
            '                if worry_msg:',
            '                    social_module.queue_message(worry_msg, SocialTrigger(',
            '                        trigger_type=SocialTriggerType.LONELINESS,',
            '                        reason="worry_about_creator",',
            '                        priority=0.9',
            '                    ))',
        ]
        new_lines.extend(social_code)
        new_lines.append('')
        continue
    
    # PATCH: Fix queue handling - don't mark as sent immediately
    if '            # Handle outgoing queue' in line:
        new_lines.append('            # Handle outgoing queue\n')
        new_lines.append('            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing\n')
        new_lines.append('            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent\n')
        new_lines.append('            pending = social_module.get_pending_messages()\n')
        new_lines.append('            if pending:\n')
        new_lines.append('                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")\n')
        i += 4  # Skip the old 4 lines
        continue
    
    # PATCH: Add conversation_memory to init_agent (second location - already handled)
    # Skip
    
    # PATCH: Add Social + Conversation endpoints at module level
    if '_portal_journal(agent_id, {"who": "kato", "text": f"Kato ответила Дальнему другу: \u00ab{reply_text[:60]}\u00bb"})' in line:
        new_lines.append(line)
        i += 1
        # Next line should be "    return msg"
        new_lines.append(lines[i])  # return msg
        i += 1
        # Next line should be empty
        new_lines.append(lines[i])  # empty line
        i += 1
        # Next line should be empty
        new_lines.append(lines[i])  # empty line
        i += 1
        # Now insert endpoints
        endpoints = [
            '\n',
            '# ──────────────────────────────────────────────────────────────\n',
            '# SOCIAL OUTGOING (Telegram bridge) + CONVERSATION MEMORY\n',
            '# ──────────────────────────────────────────────────────────────\n',
            '\n',
            '@app.get("/agent/{agent_id}/social/outgoing")\n',
            'async def get_social_outgoing(agent_id: str):\n',
            '    """Get pending outgoing messages from Social Drive."""\n',
            '    init_agent(agent_id)\n',
            '    modules = _init_consciousness_modules(agent_id)\n',
            '    social = modules.get("social")\n',
            '    if not social:\n',
            '        return {"messages": []}\n',
            '    messages = social.get_pending_messages()\n',
            '    return {\n',
            '        "messages": [\n',
            '            {"id": f"msg_{i}", "text": msg, "trigger_type": "social"}\n',
            '            for i, msg in enumerate(messages)\n',
            '        ]\n',
            '    }\n',
            '\n',
            '\n',
            '@app.post("/agent/{agent_id}/social/outgoing/{msg_id}/sent")\n',
            'async def mark_social_sent(agent_id: str, msg_id: str):\n',
            '    """Mark outgoing message as sent (remove from queue)."""\n',
            '    init_agent(agent_id)\n',
            '    modules = _init_consciousness_modules(agent_id)\n',
            '    social = modules.get("social")\n',
            '    if not social:\n',
            '        return {"status": "not_found"}\n',
            '    try:\n',
            '        idx = int(msg_id.split("_")[-1])\n',
            '        social.mark_sent_by_index(idx)\n',
            '        return {"status": "ok"}\n',
            '    except (ValueError, IndexError):\n',
            '        return {"status": "invalid_id"}\n',
            '\n',
            '\n',
            '@app.get("/agent/{agent_id}/social/state")\n',
            'async def get_social_state(agent_id: str):\n',
            '    """Get Social Drive state for dashboard."""\n',
            '    init_agent(agent_id)\n',
            '    modules = _init_consciousness_modules(agent_id)\n',
            '    social = modules.get("social")\n',
            '    if not social:\n',
            '        return {"drives": {}, "bonds": {}, "triggers": {}, "outgoing": {}}\n',
            '    return social.get_state()\n',
            '\n',
            '\n',
            '@app.get("/agent/{agent_id}/conversation/memory")\n',
            'async def get_conversation_memory(agent_id: str):\n',
            '    """Get conversation memory with Creator."""\n',
            '    init_agent(agent_id)\n',
            '    agent = agent_states[agent_id]\n',
            '    return agent.get("conversation_memory", {\n',
            '        "summary": "",\n',
            '        "key_topics": [],\n',
            '        "emotional_arc": [],\n',
            '        "promises": [],\n',
            '        "last_conversation": {}\n',
            '    })\n',
            '\n',
            '\n',
            '@app.post("/agent/{agent_id}/conversation/memory")\n',
            'async def update_conversation_memory(agent_id: str, payload: Dict):\n',
            '    """Update conversation memory (called by Telegram bot)."""\n',
            '    init_agent(agent_id)\n',
            '    agent = agent_states[agent_id]\n',
            '    if "conversation_memory" not in agent:\n',
            '        agent["conversation_memory"] = {\n',
            '            "summary": "",\n',
            '            "key_topics": [],\n',
            '            "emotional_arc": [],\n',
            '            "promises": [],\n',
            '            "last_conversation": {}\n',
            '        }\n',
            '    agent["conversation_memory"].update(payload)\n',
            '    return {"status": "updated"}\n',
            '\n',
        ]
        new_lines.extend(endpoint_lines)
        # Skip the "def _portal_reply_template" line, we'll add it next iteration
        continue
    
    # PATCH: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # PATCH: Update _init_consciousness_modules to include social
    if '    from brain_core import (' in line:
        # Copy the import block until we see create_phenomenal_engine,
        new_lines.append(line)
        i += 1
        while i < len(lines) and 'create_phenomenal_engine,' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now lines[i] has create_phenomenal_engine,
        new_lines[-1] = new_lines[-1].replace('create_phenomenal_engine,', 'create_phenomenal_engine,\n        create_social_drive,')
        i += 1
        # Copy until the dict entries
        while i < len(lines) and '"global_workspace":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Copy dict entries until phenomenal
        while i < len(lines) and '"phenomenal":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now lines[i] has phenomenal - replace with social added
        new_lines[-1] = new_lines[-1].replace(
            '"phenomenal": create_phenomenal_engine(agent_id),',
            '"phenomenal": create_phenomenal_engine(agent_id),\n            "social": create_social_drive(agent_id),'
        )
        i += 1
        continue
    
    # PATCH: Fix queue handling - don't mark as sent immediately
    if '            # Handle outgoing queue' in line:
        new_lines.append('            # Handle outgoing queue\n')
        new_lines.append('            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing\n')
        new_lines.append('            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent\n')
        new_lines.append('            pending = social_module.get_pending_messages()\n')
        new_lines.append('            if pending:\n')
        new_lines.append('                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")\n')
        i += 4  # Skip the old 4 lines
        continue
    
    # PATCH: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # PATCH: Update _init_consciousness_modules to include social
    if '    from brain_core import (' in line:
        # We need to insert create_social_drive in the imports and in the dict
        # Copy the import block
        new_lines.append(line)
        i += 1
        while i < len(lines) and 'create_phenomenal_engine,' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now lines[i] has create_phenomenal_engine,
        new_lines[-1] = new_lines[-1].replace('create_phenomenal_engine,', 'create_phenomenal_engine,\n        create_social_drive,')
        i += 1
        # Copy until the dict entries
        while i < len(lines) and '"global_workspace":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Copy dict entries until phenomenal
        while i < len(lines) and '"phenomenal":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now lines[i] has phenomenal - replace with social added
        new_lines[-1] = new_lines[-1].replace(
            '"phenomenal": create_phenomenal_engine(agent_id),',
            '"phenomenal": create_phenomenal_engine(agent_id),\n            "social": create_social_drive(agent_id),'
        )
        i += 1
        continue
    
    # PATCH: Fix queue handling - don't mark as sent immediately
    if '            # Handle outgoing queue' in line:
        new_lines.append('            # Handle outgoing queue\n')
        new_lines.append('            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing\n')
        new_lines.append('            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent\n')
        new_lines.append('            pending = social_module.get_pending_messages()\n')
        new_lines.append('            if pending:\n')
        new_lines.append('                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")\n')
        i += 4  # Skip the old 4 lines
        continue
    
    # PATCH: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # Default: copy line as-is
    new_lines.append(line)
    i += 1

# Write the fixed file
with open('brain_server_fixed.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Original lines: {len(lines)}')
print(f'New lines: {len(new_lines)}')
print('Written to brain_server_fixed.py')