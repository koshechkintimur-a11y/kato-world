extends Node

# Central event bus for decoupled communication between all systems
class_name EventBus

# Perception events
signal perceived_object(object_id: String, object_data: Dictionary)
signal perceived_npc(npc_id: String, npc_data: Dictionary)
signal perceived_event(event_type: String, data: Dictionary)

# Action events
signal action_proposed(action: String, params: Dictionary, confidence: float, source: String)
signal action_executed(action: String, params: Dictionary, result: Dictionary)
signal action_failed(action: String, params: Dictionary, reason: String)

# Body/Emotion events
signal body_changed(param: String, old_value: float, new_value: float)
signal emotion_changed(emotion: String, intensity: float)
signal homeostasis_shifted(hormone: String, value: float)

# Memory events
signal memory_formed(memory_type: String, event_data: Dictionary, salience: float)
signal memory_recalled(memory_type: String, memories: Array)
signal memory_consolidated(count: int)

# Self-model events
signal self_model_updated(changes: Dictionary)
signal goal_changed(goal: Dictionary, added: bool)
signal belief_changed(belief: String, value: float)

# Cognitive events
signal system1_triggered(action: String, confidence: float)
signal system2_engaged(reason: String, working_memory: Dictionary)
signal arbitration_result(chosen_action: Dictionary, mode: String)

# Dream/Divine events
signal dream_generated(dream_content: Dictionary)
signal divine_whisper_received(content: String, source: String, intensity: float)
signal sleep_cycle_started
signal sleep_cycle_ended

# World events
signal world_state_changed(state: Dictionary)
signal time_changed(time_of_day: float)
signal weather_changed(weather: String)

# NPC events
signal npc_dialogue_started(npc_id: String, dialogue_data: Dictionary)
signal npc_dialogue_ended(npc_id: String)
signal relationship_changed(npc_id: String, relationship_type: String, value: float)

func _ready():
    print("EventBus initialized - all systems can communicate")

# Helper methods for common event patterns
func emit_perception(obj_id: String, data: Dictionary):
    emit_signal("perceived_object", obj_id, data)

func emit_action(action: String, params: Dictionary, confidence: float = 1.0, source: String = "system1"):
    emit_signal("action_proposed", action, params, confidence, source)

func emit_body_change(param: String, old_val: float, new_val: float):
    emit_signal("body_changed", param, old_val, new_val)

func emit_emotion(emotion: String, intensity: float):
    emit_signal("emotion_changed", emotion, intensity)

func emit_memory(memory_type: String, data: Dictionary, salience: float):
    emit_signal("memory_formed", memory_type, data, salience)

func emit_self_model_change(changes: Dictionary):
    emit_signal("self_model_updated", changes)

func emit_dream(content: Dictionary):
    emit_signal("dream_generated", content)

func emit_divine_whisper(content: String, source: String = "creator", intensity: float = 0.5):
    emit_signal("divine_whisper_received", content, source, intensity)