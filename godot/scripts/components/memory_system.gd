extends Node

# Memory system component for the agent - handles memory queries and display
class_name MemorySystem

signal memory_recalled(memories: Array, query_type: String)
signal memory_formed(memory: Dictionary, memory_type: String)
signal autobiographical_updated(entry: Dictionary)

var _current_query: Dictionary = {}
var _memory_cache: Dictionary = {
    "episodic": [],
    "semantic": [],
    "autobiographical": [],
    "emotional": [],
    "working": []
}

func _ready():
    # Connect to brain client signals
    BrainClient.memory_query_result.connect(_on_memory_query_result)
    EventBus.memory_formed.connect(_on_memory_formed)
    
    print("MemorySystem initialized")

func query_memory(memory_type: String = "episodic", cue: String = "", limit: int = 10, min_salience: float = 0.0):
    _current_query = {
        "memory_type": memory_type,
        "cue": cue,
        "limit": limit,
        "min_salience": min_salience
    }
    
    # Use BrainClient's query_memory method
    BrainClient.query_memory(memory_type, cue, limit, min_salience)

func _on_memory_query_result(memories: Array, memory_type: String):
    _memory_cache[memory_type] = memories
    emit_signal("memory_recalled", memories, memory_type)

func _on_brain_response(response_type: String, data: Dictionary):
    if response_type == "dream_received":
        # Dream may contain consolidated memories
        pass

func _on_memory_formed(memory_type: String, event_data: Dictionary, salience: float):
    # Local notification that memory was formed
    pass

func get_cached_memories(memory_type: String) -> Array:
    return _memory_cache.get(memory_type, [])

func get_memory_summary() -> Dictionary:
    var summary = {}
    for mtype in _memory_cache:
        summary[mtype] = _memory_cache[mtype].size()
    return summary