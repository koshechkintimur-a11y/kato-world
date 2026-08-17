extends CharacterBody2D

# Kato - the agent entity
class_name Agent

signal position_changed(new_pos: Vector2i)
signal action_executed(action: String, params: Dictionary, result: Dictionary)
signal state_changed(param: String, old_value: float, new_value: float)

# Movement
@export var move_speed: float = 120.0  # pixels per second
@export var tile_move_time: float = 0.15  # seconds per tile

# Body parameters
var energy: float = 100.0
var comfort: float = 100.0
var stress: float = 0.0
var integrity: float = 100.0
var temperature: float = 22.0

# Direction
var facing_direction: Vector2i = Vector2i(0, 1)  # down
var _target_tile: Vector2i = Vector2i(12, 8)
var _is_moving: bool = false
var _move_timer: float = 0.0

# Animation
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D

# Input
var _input_direction: Vector2i = Vector2i(0, 0)

func _ready():
    _target_tile = GlobalState.world_to_tile(global_position)
    _setup_animations()
    print("Agent Kato initialized at ", _target_tile)

func _setup_animations():
    if animated_sprite and animated_sprite.sprite_frames:
        animated_sprite.play("idle_down")

func _physics_process(delta: float):
    _handle_movement(delta)
    _update_body(delta)
    _check_interactions()

func _handle_movement(delta: float):
    if _is_moving:
        _move_timer += delta
        var progress = min(_move_timer / tile_move_time, 1.0)
        var start_pos = GlobalState.tile_to_world(_target_tile - facing_direction)
        var end_pos = GlobalState.tile_to_world(_target_tile)
        global_position = start_pos.lerp(end_pos, progress)
        
        if progress >= 1.0:
            _is_moving = false
            _move_timer = 0.0
            global_position = end_pos
            _on_tile_reached()
    else:
        # Check for input (for manual testing)
        _input_direction = Vector2i(0, 0)
        if Input.is_action_pressed("move_up"):
            _input_direction.y = -1
        elif Input.is_action_pressed("move_down"):
            _input_direction.y = 1
        if Input.is_action_pressed("move_left"):
            _input_direction.x = -1
        elif Input.is_action_pressed("move_right"):
            _input_direction.x = 1
        
        if _input_direction != Vector2i(0, 0):
            _try_move(_input_direction)

func _try_move(direction: Vector2i):
    var new_tile = _target_tile + direction
    if GlobalState.is_valid_tile(new_tile) and _is_walkable(new_tile):
        facing_direction = direction
        _target_tile = new_tile
        _is_moving = true
        _move_timer = 0.0
        _update_animation()
        _spend_energy(0.5)  # Movement costs energy

func _is_walkable(tile: Vector2i) -> bool:
    # Check tilemap collision layer
    var tilemap = get_tree().root.get_node("WorldRoot/TileMap", true)
    if tilemap:
        return tilemap.get_cell_atlas_coords(1, tile) == Vector2i(-1, -1)  # No wall
    return true

func _on_tile_reached():
    var new_tile_pos = _target_tile
    emit_signal("position_changed", new_tile_pos)
    
    # Check for object interactions on this tile
    _check_tile_interactions(new_tile_pos)

func _check_tile_interactions(tile_pos: Vector2i):
    var objects = get_tree().root.get_node("WorldRoot/Objects", true)
    if objects:
        for child in objects.get_children():
            var obj_data = child.get_meta("object_data", {})
            if obj_data and obj_data.position == [tile_pos.x, tile_pos.y]:
                EventBus.emit_perception(child.name, obj_data)

func _check_interactions():
    if Input.is_action_just_pressed("interact"):
        _interact_with_front_tile()

func _interact_with_front_tile():
    var front_tile = _target_tile + facing_direction
    var objects = get_tree().root.get_node("WorldRoot/Objects", true)
    if objects:
        for child in objects.get_children():
            var obj_data = child.get_meta("object_data", {})
            if obj_data and obj_data.position == [front_tile.x, front_tile.y]:
                _execute_interaction(child.name, obj_data)
                return
    
    # Check NPCs
    var npcs = get_tree().root.get_node("WorldRoot/NPCs", true)
    if npcs:
        for child in npcs.get_children():
            var npc_data = child.get_meta("npc_data", {})
            if npc_data and npc_data.position == [front_tile.x, front_tile.y]:
                _start_dialogue(child.name, npc_data)
                return

func _execute_interaction(object_id: String, obj_data: Dictionary):
    var interactions = obj_data.interactions if obj_data.has("interactions") else []
    if interactions.size() > 0:
        var action = interactions[0]  # Simple: first available interaction
        var result = {"success": true, "message": "Interacted with %s via %s" % [object_id, action]}
        
        # Apply effects based on interaction
        match action:
            "sleep", "rest":
                _restore_energy(20)
                _reduce_stress(10)
            "take":
                _spend_energy(1)
            "use":
                _spend_energy(2)
        
        emit_signal("action_executed", action, {"object": object_id}, result)
        EventBus.emit_signal("action_executed", action, {"object": object_id}, result)

func _start_dialogue(npc_id: String, npc_data: Dictionary):
    var result = {"success": true, "message": "Started dialogue with %s" % npc_id}
    emit_signal("action_executed", "talk", {"npc": npc_id}, result)
    EventBus.emit_signal("npc_dialogue_started", npc_id, npc_data)

func _update_body(delta: float):
    # Passive body changes
    var old_energy = energy
    var old_comfort = comfort
    var old_stress = stress
    
    # Energy drains over time
    energy = max(0.0, energy - 0.1 * delta)
    
    # Comfort decays
    comfort = max(0.0, comfort - 0.05 * delta)
    
    # Stress increases if energy low
    if energy < 30:
        stress = min(100.0, stress + 0.5 * delta)
    
    # Emit changes
    if abs(energy - old_energy) > 0.1:
        emit_signal("state_changed", "energy", old_energy, energy)
        EventBus.emit_body_change("energy", old_energy, energy)
    if abs(comfort - old_comfort) > 0.1:
        emit_signal("state_changed", "comfort", old_comfort, comfort)
        EventBus.emit_body_change("comfort", old_comfort, comfort)
    if abs(stress - old_stress) > 0.1:
        emit_signal("state_changed", "stress", old_stress, stress)
        EventBus.emit_body_change("stress", old_stress, stress)
    
    # Update world state
    WorldState.update_agent_state({
        "energy": energy,
        "comfort": comfort,
        "stress": stress,
        "integrity": integrity,
        "temperature": temperature
    })

func _spend_energy(amount: float):
    var old = energy
    energy = max(0.0, energy - amount)
    emit_signal("state_changed", "energy", old, energy)
    EventBus.emit_body_change("energy", old, energy)

func _restore_energy(amount: float):
    var old = energy
    energy = min(GlobalState.AGENT_MAX_ENERGY, energy + amount)
    emit_signal("state_changed", "energy", old, energy)
    EventBus.emit_body_change("energy", old, energy)

func _reduce_stress(amount: float):
    var old = stress
    stress = max(0.0, stress - amount)
    emit_signal("state_changed", "stress", old, stress)
    EventBus.emit_body_change("stress", old, stress)

func _update_animation():
    if animated_sprite and animated_sprite.sprite_frames:
        var dir_name = "down"
        if facing_direction == Vector2i(0, -1): dir_name = "up"
        elif facing_direction == Vector2i(-1, 0): dir_name = "left"
        elif facing_direction == Vector2i(1, 0): dir_name = "right"
        
        if _is_moving:
            animated_sprite.play("walk_%s" % dir_name)
        else:
            animated_sprite.play("idle_%s" % dir_name)

# Public API for brain client
func move_to_tile(tile_pos: Vector2i) -> bool:
    if not GlobalState.is_valid_tile(tile_pos) or not _is_walkable(tile_pos):
        return false
    
    var direction = tile_pos - _target_tile
    if direction.length() == 1:
        _try_move(direction)
        return true
    return false

func get_current_tile() -> Vector2i:
    return _target_tile

func get_body_state() -> Dictionary:
    return {
        "energy": energy,
        "comfort": comfort,
        "stress": stress,
        "integrity": integrity,
        "temperature": temperature
    }

func get_facing_direction() -> Vector2i:
    return facing_direction