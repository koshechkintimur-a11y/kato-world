extends Node

# Client for communicating with the Python brain server (FastAPI)
# Handles: perception -> brain, action proposals <- brain, state sync, dream gateway
class_name BrainClient

# Configuration
@export var brain_server_url: String = "http://localhost:8080"
@export var request_timeout: float = 5.0
@export var tick_batch_size: int = 1  # Send perception every N ticks

# Internal state
var _http_client: HTTPRequest
var _pending_requests: Dictionary = {}
var _request_id_counter: int = 0
var _last_perception_tick: int = 0
var _brain_connected: bool = false
var _agent_id: String = "kato"

# Signal for brain responses
signal brain_response_received(response_type: String, data: Dictionary)
signal brain_connection_changed(connected: bool)
signal action_received(action: Dictionary)
signal dream_received(dream: Dictionary)
signal divine_whisper_received(whisper: Dictionary)
signal memory_query_result(memories: Array, memory_type: String)
signal emotion_state_received(emotions: Dictionary, mood: Dictionary)

func _ready():
    _http_client = HTTPRequest.new()
    add_child(_http_client)
    _http_client.request_completed.connect(_on_request_completed)
    _http_client.connect("request_completed", Callable(self, "_on_request_completed"))
    
    # Register with brain server
    call_deferred("register_agent")
    
    # Listen for world ticks to send perception
    GlobalState.world_tick.connect(_on_world_tick)
    
    # Listen for divine whispers from EventBus (for dream gateway)
    EventBus.divine_whisper_received.connect(_on_divine_whisper)
    
    print("BrainClient initialized, connecting to ", brain_server_url)

func _on_world_tick(tick: int, delta: float):
    _last_perception_tick = tick
    
    # Send perception periodically
    if tick % tick_batch_size == 0:
        send_perception()
    
    # Request action from brain every tick (brain decides timing)
    request_action()

func register_agent():
    var payload = {
        "agent_id": _agent_id,
        "capabilities": ["perception", "action", "memory", "emotion", "dream", "divine_whisper"],
        "world_schema_version": 1
    }
    _post("/agent/register", payload, "register")

func send_perception():
    var perception = _build_perception_payload()
    _post("/perception", perception, "perception")

func request_action():
    var payload = {
        "agent_id": _agent_id,
        "tick": GlobalState.current_tick,
        "working_memory": _get_working_memory_snapshot()
    }
    _post("/action/propose", payload, "action_propose")

func send_action_result(action: String, params: Dictionary, result: Dictionary, success: bool):
    var payload = {
        "agent_id": _agent_id,
        "tick": GlobalState.current_tick,
        "action": action,
        "params": params,
        "result": result,
        "success": success
    }
    _post("/action/result", payload, "action_result")

func send_memory_consolidation(memories: Array):
    var payload = {
        "agent_id": _agent_id,
        "tick": GlobalState.current_tick,
        "memories": memories
    }
    _post("/memory/consolidate", payload, "memory_consolidate")

func request_dream_processing():
    var payload = {
        "agent_id": _agent_id,
        "tick": GlobalState.current_tick,
        "recent_events": WorldState.get_recent_events(30),
        "emotional_state": _get_emotional_state_snapshot()
    }
    _post("/dream/process", payload, "dream_process")

func _build_perception_payload() -> Dictionary:
    var agent_state = WorldState.get_agent_state()
    var nearby_objects = _get_nearby_objects(agent_state.position, 5)
    var nearby_npcs = _get_nearby_npcs(agent_state.position, 5)
    
    return {
        "agent_id": _agent_id,
        "tick": GlobalState.current_tick,
        "time_of_day": GlobalState.time_of_day,
        "agent": agent_state,
        "nearby_objects": nearby_objects,
        "nearby_npcs": nearby_npcs,
        "recent_events": WorldState.get_recent_events(10)
    }

func _get_nearby_objects(pos: Array, radius: int) -> Array:
    var result = []
    var agent_tile = Vector2i(pos[0], pos[1])
    for obj in WorldState.world_state.objects:
        var obj_tile = Vector2i(obj.position[0], obj.position[1])
        if agent_tile.distance_to(obj_tile) <= radius:
            result.append(obj.duplicate(true))
    return result

func _get_nearby_npcs(pos: Array, radius: int) -> Array:
    var result = []
    var agent_tile = Vector2i(pos[0], pos[1])
    for npc in WorldState.world_state.npcs:
        var npc_tile = Vector2i(npc.position[0], npc.position[1])
        if agent_tile.distance_to(npc_tile) <= radius:
            result.append(npc.duplicate(true))
    return result

func _get_working_memory_snapshot() -> Dictionary:
    # This would come from the agent's cognitive system
    # For now, return a minimal snapshot
    return {
        "current_goal": "explore",
        "attention_focus": [],
        "active_thoughts": []
    }

func _get_emotional_state_snapshot() -> Dictionary:
    # Placeholder - will come from emotion system
    return {
        "joy": 0.0,
        "fear": 0.0,
        "anger": 0.0,
        "sadness": 0.0,
        "curiosity": 0.5,
        "trust": 0.5,
        "attachment": 0.0
    }

func _post(endpoint: String, payload: Dictionary, request_type: String):
    var request_id = _request_id_counter
    _request_id_counter += 1
    
    var headers = ["Content-Type: application/json"]
    var body = JSON.stringify(payload)
    
    _pending_requests[request_id] = {
        "type": request_type,
        "timestamp": GlobalState.current_tick
    }
    
    var error = _http_client.request(brain_server_url + endpoint, headers, HTTPClient.METHOD_POST, body)
    if error != OK:
        push_error("HTTP request failed: ", error)
        _pending_requests.erase(request_id)

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
    var request_id = -1
    # Find the matching request (simplified - in production use proper correlation)
    for id in _pending_requests:
        request_id = id
        break
    
    if request_id == -1:
        return
    
    var request_info = _pending_requests[request_id]
    _pending_requests.erase(request_id)
    
    if response_code != 200:
        push_error("Brain server error: ", response_code, body.get_string_from_utf8())
        _check_connection(false)
        return
    
    _check_connection(true)
    
    var response_text = body.get_string_from_utf8()
    var parse_result = JSON.parse_string(response_text)
    if parse_result.error != OK:
        push_error("Failed to parse brain response: ", parse_result.error_string)
        return
    
    var response = parse_result
    _handle_response(request_info.type, response)

func _handle_response(request_type: String, response: Dictionary):
    match request_type:
        "register":
            print("Agent registered with brain: ", response)
            _brain_connected = true
            emit_signal("brain_connection_changed", true)
        
        "action_propose":
            if response.has("action"):
                emit_signal("action_received", response.action)
        
        "dream_process":
            if response.has("dream"):
                emit_signal("dream_received", response.dream)
                # Also emit to EventBus for memory/emotion processing
                EventBus.emit_dream(response.dream)
        
        "memory_query":
            if response.has("memories"):
                var mem_type = "episodic"
                # Try to infer from request - in real impl we'd correlate
                emit_signal("memory_query_result", response.memories, mem_type)
        
        "perception":
            # Perception response now carries emotions + mood for UI
            if response.has("emotions"):
                emit_signal("emotion_state_received",
                            response.emotions,
                            response.get("mood", {}))
        
        "action_result", "memory_consolidate":
            # Acknowledgment responses
            pass
        
        _:
            print("Unhandled response type: ", request_type, response)

func _on_divine_whisper(content: String, source: String, intensity: float):
    # Forward divine whisper to brain for dream integration
    var payload = {
        "agent_id": _agent_id,
        "tick": GlobalState.current_tick,
        "whisper": {
            "content": content,
            "source": source,
            "intensity": intensity,
            "received_at": GlobalState.current_tick
        }
    }
    _post("/divine/whisper", payload, "divine_whisper")

func _check_connection(connected: bool):
    if connected != _brain_connected:
        _brain_connected = connected
        emit_signal("brain_connection_changed", connected)

func is_connected() -> bool:
    return _brain_connected

func set_server_url(url: String):
    brain_server_url = url

func query_memory(memory_type: String = "episodic", cue: String = "", limit: int = 20, min_salience: float = 0.0):
    var payload = {
        "agent_id": _agent_id,
        "memory_type": memory_type,
        "cue": cue if cue != "" else null,
        "limit": limit,
        "min_salience": min_salience
    }
    _post("/memory/query", payload, "memory_query")