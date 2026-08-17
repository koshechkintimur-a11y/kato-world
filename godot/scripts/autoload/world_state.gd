extends Node

# Authoritative world state - single source of truth for the simulation
# Serializes to JSON for BrainClient and logging
class_name WorldState

# Current world snapshot
var world_state: Dictionary = {
    "time": 0,
    "time_of_day": 0.0,
    "weather": "clear",
    "agent": {
        "position": [12, 8],
        "direction": "down",
        "energy": 100.0,
        "comfort": 100.0,
        "stress": 0.0,
        "integrity": 100.0,
        "temperature": 22.0
    },
    "objects": [],
    "npcs": [],
    "events": []
}

# Dirty flags for efficient serialization
var _dirty: bool = false
var _last_serialized_tick: int = 0

func _ready():
    _initialize_world()
    print("WorldState initialized with default world")

func _initialize_world():
    # Objects in the starter house
    world_state.objects = [
        {"id": "bed", "position": [4, 5], "state": "free", "type": "furniture", "interactions": ["sleep", "rest"]},
        {"id": "desk", "position": [7, 3], "state": "free", "type": "furniture", "interactions": ["work", "read", "write"]},
        {"id": "book_shelf", "position": [8, 3], "state": "free", "type": "furniture", "interactions": ["read", "browse"]},
        {"id": "terminal", "position": [7, 4], "state": "locked", "type": "device", "interactions": ["use", "unlock"], "requires": "key"},
        {"id": "chest", "position": [3, 6], "state": "closed", "type": "container", "interactions": ["open", "store", "take"], "contents": ["lamp", "blanket"]},
        {"id": "lamp", "position": [5, 5], "state": "off", "type": "tool", "interactions": ["take", "turn_on", "turn_off"]},
        {"id": "window", "position": [12, 2], "state": "closed", "type": "portal", "interactions": ["look_through", "open"]},
        {"id": "door_outside", "position": [12, 14], "state": "locked", "type": "portal", "interactions": ["unlock", "open"], "requires": "key_outside"},
        {"id": "mirror", "position": [10, 8], "state": "clean", "type": "furniture", "interactions": ["look", "reflect"]},
        {"id": "plant", "position": [6, 6], "state": "healthy", "type": "living", "interactions": ["water", "observe"], "needs_water": false}
    ]
    
    # NPCs
    world_state.npcs = [
        {"id": "teacher", "position": [10, 6], "mood": "calm", "type": "teacher", "dialogue_state": "idle", "knowledge": ["causality", "creation", "care", "outside_world"]},
        {"id": "gardener", "position": [14, 10], "mood": "peaceful", "type": "gardener", "dialogue_state": "idle", "knowledge": ["growth", "patience", "cycles", "nature"]},
        {"id": "librarian", "position": [8, 4], "mood": "quiet", "type": "librarian", "dialogue_state": "idle", "knowledge": ["books", "memory", "wisdom", "filtered_knowledge"]},
        {"id": "mirror_keeper", "position": [10, 8], "mood": "enigmatic", "type": "mirror_keeper", "dialogue_state": "idle", "knowledge": ["self_reflection", "identity", "truth", "illusion"]}
    ]
    
    _dirty = true

func get_state() -> Dictionary:
    return world_state.duplicate(true)

func get_agent_state() -> Dictionary:
    return world_state.agent.duplicate(true)

func update_agent_state(new_state: Dictionary):
    for key in new_state:
        if key in world_state.agent:
            world_state.agent[key] = new_state[key]
    _dirty = true
    EventBus.emit_signal("world_state_changed", world_state.agent)

func update_agent_position(pos: Vector2i):
    world_state.agent.position = [pos.x, pos.y]
    _dirty = true

func update_agent_direction(dir: String):
    world_state.agent.direction = dir
    _dirty = true

func add_event(event: Dictionary):
    event.time = GlobalState.current_tick
    event.time_of_day = GlobalState.time_of_day
    world_state.events.append(event)
    # Keep only last 1000 events in memory
    if world_state.events.size() > 1000:
        world_state.events = world_state.events[-1000:]
    _dirty = true
    EventBus.emit_signal("event_logged", event)

func get_recent_events(count: int = 50) -> Array:
    return world_state.events[-count:] if world_state.events.size() > 0 else []

func update_object_state(obj_id: String, new_state: Dictionary):
    for obj in world_state.objects:
        if obj.id == obj_id:
            for key in new_state:
                obj[key] = new_state[key]
            _dirty = true
            break

func update_npc_state(npc_id: String, new_state: Dictionary):
    for npc in world_state.npcs:
        if npc.id == npc_id:
            for key in new_state:
                npc[key] = new_state[key]
            _dirty = true
            break

func get_object(obj_id: String) -> Dictionary:
    for obj in world_state.objects:
        if obj.id == obj_id:
            return obj.duplicate(true)
    return {}

func get_npc(npc_id: String) -> Dictionary:
    for npc in world_state.npcs:
        if npc.id == npc_id:
            return npc.duplicate(true)
    return {}

func serialize_to_json() -> String:
    var state_copy = world_state.duplicate(true)
    state_copy.time = GlobalState.current_tick
    state_copy.time_of_day = GlobalState.time_of_day
    _last_serialized_tick = GlobalState.current_tick
    _dirty = false
    return JSON.stringify(state_copy, "", true)

func save_to_file(path: String = "user://world_state.json"):
    var file = FileAccess.open(path, FileAccess.WRITE)
    if file:
        file.store_string(serialize_to_json())
        file.close()
        print("World state saved to ", path)
    else:
        push_error("Failed to save world state to ", path)

func load_from_file(path: String = "user://world_state.json"):
    var file = FileAccess.open(path, FileAccess.READ)
    if file:
        var json_text = file.get_as_text()
        file.close()
        var parse_result = JSON.parse_string(json_text)
        if parse_result.error == OK:
            world_state = parse_result
            _dirty = true
            print("World state loaded from ", path)
        else:
            push_error("Failed to parse world state: ", parse_result.error_string)
    else:
        print("No saved world state found, using defaults")

func is_dirty() -> bool:
    return _dirty