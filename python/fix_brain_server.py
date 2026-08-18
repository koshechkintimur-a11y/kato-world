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
    if '            # Creator revelation protocol state' in line and i+5 < len(lines) and '            "revelation": {' in lines[i+1]:
        # Find the closing brace of revelation
        j = i
        brace_count = 0
        while j < len(lines):
            brace_count += lines[j].count('{')
            brace_count -= lines[j].count('}')
            if brace_count == 0 and '            }' in lines[j]:
                break
            j += 1
        # Insert conversation_memory after revelation, before the closing brace of agent dict
        new_lines.extend(lines[i:j+1])
        new_lines.append('            # Conversation memory with Creator (Telegram)\n')
        new_lines.append('            "conversation_memory": {\n')
        new_lines.append('                "summary": "",\n')
        new_lines.append('                "key_topics": [],\n')
        new_lines.append('                "emotional_arc": [],\n')
        new_lines.append('                "promises": [],\n')
        new_lines.append('                "last_conversation": {}\n')
        new_lines.append('            }\n')
        i = j + 1
        continue
    
    # PATCH 3: Update _init_consciousness_modules to include social
    if '    from brain_core import (' in line and i+10 < len(lines) and 'create_phenomenal_engine,' in lines[i+8]:
        # Insert create_social_drive in imports
        new_lines.append(line)
        i += 1
        while i < len(lines) and 'create_phenomenal_engine,' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Replace the last import line
        new_lines[-1] = new_lines[-1].replace('create_phenomenal_engine,', 'create_phenomenal_engine,\n        create_social_drive,')
        # Skip to the dict
        while i < len(lines) and '"global_workspace":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Copy the dict entries
        while i < len(lines) and '"phenomenal":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Replace the last entry
        new_lines[-1] = new_lines[-1].replace('"phenomenal": create_phenomenal_engine(agent_id),', '"phenomenal": create_phenomenal_engine(agent_id),\n            "social": create_social_drive(agent_id),')
        i += 1
        continue
    
    # PATCH 4: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # PATCH 5: Update _consciousness_tick - find the consciousness_modules dict and add social
    if '        agent["consciousness_modules"] = {' in line:
        new_lines.append(line)
        i += 1
        # Skip until we see the closing brace
        while i < len(lines) and '"phenomenal":' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Add social to the dict
        new_lines[-1] = new_lines[-1].replace('"phenomenal": modules["phenomenal"].get_state(),', '"phenomenal": modules["phenomenal"].get_state(),\n            "social": modules["social"].get_state() if "social" in modules else {},')
        # Continue copying until we hit the "except Exception" line
        while i < len(lines) and 'except Exception as exc:' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        # Now insert the Social Drive integration BEFORE the except block
        # We need to find the right indentation level
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
    
    # PATCH 6: Fix queue handling - don't mark as sent immediately
    if '            # Handle outgoing queue' in line and 'for message in social_module.get_pending_messages():' in lines[i+1]:
        # Replace the next few lines
        new_lines.append('            # Handle outgoing queue\n')
        new_lines.append('            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing\n')
        new_lines.append('            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent\n')
        new_lines.append('            pending = social_module.get_pending_messages()\n')
        new_lines.append('            if pending:\n')
        new_lines.append('                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")\n')
        i += 4  # Skip the old 4 lines
        continue
    
    # PATCH 7: Add conversation_memory to init_agent (second location)
    if '            # Creator revelation protocol state' in line:
        # Check if this is the second occurrence (after revelation dict)
        pass  # We'll handle this differently
    
    # PATCH 8: Add Social + Conversation endpoints at module level
    # Find: "    _portal_journal(agent_id, {\"who\": \"kato\", \"text\": f\"Kato ответила Дальнему другу: \u00ab{reply_text[:60]}\u00bb\"})"
    # followed by "    return msg" and then "def _portal_reply_template"
    if '_portal_journal(agent_id, {"who": "kato", "text": f"Kato ответила Дальнему другу: \u00ab{reply_text[:60]}\u00bb"})' in line:
        # Check if next lines match
        if i+2 < len(lines) and 'return msg' in lines[i+1] and i+3 < len(lines) and 'def _portal_reply_template' in lines[i+3]:
            # Insert endpoints here
            new_lines.append(line)
            new_lines.append('    return msg\n')
            new_lines.append('\n')
            new_lines.append('# ──────────────────────────────────────────────────────────────\n')
            new_lines.append('# SOCIAL OUTGOING (Telegram bridge) + CONVERSATION MEMORY\n')
            new_lines.append('# ──────────────────────────────────────────────────────────────\n')
            new_lines.append('\n')
            new_lines.append('@app.get("/agent/{agent_id}/social/outgoing")\n')
            new_lines.append('async def get_social_outgoing(agent_id: str):\n')
            new_lines.append('    """Get pending outgoing messages from Social Drive."""\n')
            new_lines.append('    init_agent(agent_id)\n')
            new_lines.append('    modules = _init_consciousness_modules(agent_id)\n')
            new_lines.append('    social = modules.get("social")\n')
            new_lines.append('    if not social:\n')
            new_lines.append('        return {"messages": []}\n')
            new_lines.append('    messages = social.get_pending_messages()\n')
            new_lines.append('    return {\n')
            new_lines.append('        "messages": [\n')
            new_lines.append('            {"id": f"msg_{i}", "text": msg, "trigger_type": "social"}\n')
            new_lines.append('            for i, msg in enumerate(messages)\n')
            new_lines.append('        ]\n')
            new_lines.append('    }\n')
            new_lines.append('\n')
            new_lines.append('\n')
            new_lines.append('@app.post("/agent/{agent_id}/social/outgoing/{msg_id}/sent")\n')
            new_lines.append('async def mark_social_sent(agent_id: str, msg_id: str):\n')
            new_lines.append('    """Mark outgoing message as sent (remove from queue)."""\n')
            new_lines.append('    init_agent(agent_id)\n')
            new_lines.append('    modules = _init_consciousness_modules(agent_id)\n')
            new_lines.append('    social = modules.get("social")\n')
            new_lines.append('    if not social:\n')
            new_lines.append('        return {"status": "not_found"}\n')
            new_lines.append('    try:\n')
            new_lines.append('        idx = int(msg_id.split("_")[-1])\n')
            new_lines.append('        social.mark_sent_by_index(idx)\n')
            new_lines.append('        return {"status": "ok"}\n')
            new_lines.append('    except (ValueError, IndexError):\n')
            new_lines.append('        return {"status": "invalid_id"}\n')
            new_lines.append('\n')
            new_lines.append('\n')
            new_lines.append('@app.get("/agent/{agent_id}/social/state")\n')
            new_lines.append('async def get_social_state(agent_id: str):\n')
            new_lines.append('    """Get Social Drive state for dashboard."""\n')
            new_lines.append('    init_agent(agent_id)\n')
            new_lines.append('    modules = _init_consciousness_modules(agent_id)\n')
            new_lines.append('    social = modules.get("social")\n')
            new_lines.append('    if not social:\n')
            new_lines.append('        return {"drives": {}, "bonds": {}, "triggers": {}, "outgoing": {}}\n')
            new_lines.append('    return social.get_state()\n')
            new_lines.append('\n')
            new_lines.append('\n')
            new_lines.append('@app.get("/agent/{agent_id}/conversation/memory")\n')
            new_lines.append('async def get_conversation_memory(agent_id: str):\n')
            new_lines.append('    """Get conversation memory with Creator."""\n')
            new_lines.append('    init_agent(agent_id)\n')
            new_lines.append('    agent = agent_states[agent_id]\n')
            new_lines.append('    return agent.get("conversation_memory", {\n')
            new_lines.append('        "summary": "",\n')
            new_lines.append('        "key_topics": [],\n')
            new_lines.append('        "emotional_arc": [],\n')
            new_lines.append('        "promises": [],\n')
            new_lines.append('        "last_conversation": {}\n')
            new_lines.append('    })\n')
            new_lines.append('\n')
            new_lines.append('\n')
            new_lines.append('@app.post("/agent/{agent_id}/conversation/memory")\n')
            new_lines.append('async def update_conversation_memory(agent_id: str, payload: Dict):\n')
            new_lines.append('    """Update conversation memory (called by Telegram bot)."""\n')
            new_lines.append('    init_agent(agent_id)\n')
            new_lines.append('    agent = agent_states[agent_id]\n')
            new_lines.append('    if "conversation_memory" not in agent:\n')
            new_lines.append('        agent["conversation_memory"] = {\n')
            new_lines.append('            "summary": "",\n')
            new_lines.append('            "key_topics": [],\n')
            new_lines.append('            "emotional_arc": [],\n')
            new_lines.append('            "promises": [],\n')
            new_lines.append('            "last_conversation": {}\n')
            new_lines.append('        }\n')
            new_lines.append('    agent["conversation_memory"].update(payload)\n')
            new_lines.append('    return {"status": "updated"}\n')
            new_lines.append('\n')
            i += 1  # We already added the current line
            continue
    
    # PATCH 9: Fix queue handling
    if '            # Handle outgoing queue' in line and 'for message in social_module.get_pending_messages():' in lines[i+1]:
        new_lines.append('            # Handle outgoing queue\n')
        new_lines.append('            # Note: Messages are left in queue for Telegram Bot to poll via /social/outgoing\n')
        new_lines.append('            # The Bot will mark them as sent via /social/outgoing/{msg_id}/sent\n')
        new_lines.append('            pending = social_module.get_pending_messages()\n')
        new_lines.append('            if pending:\n')
        new_lines.append('                logger.info(f"Social outgoing queued ({len(pending)} messages waiting for Telegram Bot)")\n')
        i += 4  # Skip old lines
        continue
    
    # PATCH 10: Fix PORTAL_REPLY_COOLDOWN_SEC
    if 'PORTAL_REPLY_COOLDOWN_SEC = 30.0     # kato: min interval between her replies' in line:
        new_lines.append('PORTAL_REPLY_COOLDOWN_SEC = 5.0      # kato: min interval between her replies (reduced for testing)\n')
        i += 1
        continue
    
    # PATCH 11: Update _init_consciousness_modules to include social
    if '    from brain_core import (' in line and i+10 < len(lines):
        # We need to insert create_social_drive in the imports and in the dict
        # This is complex - skip for now, we'll do it via a different method
        pass
    
    # Default: copy line as-is
    new_lines.append(line)
    i += 1

# Write the fixed file
with open('brain_server_fixed.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Original lines: {len(lines)}')
print(f'New lines: {len(new_lines)}')
print('Written to brain_server_fixed.py')