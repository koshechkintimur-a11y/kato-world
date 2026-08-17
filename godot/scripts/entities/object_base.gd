extends Area2D

# Base object class
class_name WorldObject

signal interacted(action: String, params: Dictionary, result: Dictionary)

@onready var sprite: Sprite2D = $Sprite2D
@onready var collision: CollisionShape2D = $CollisionShape2D

var object_id: String = ""
var object_type: String = ""
var state: String = "free"
var interactions: Array = []

func _ready():
    collision.shape = RectangleShape2D.new()
    (collision.shape as RectangleShape2D).size = Vector2(16, 16)

func setup(obj_data: Dictionary):
    object_id = obj_data.id
    object_type = obj_data.type
    state = obj_data.state
    interactions = obj_data.interactions if obj_data.has("interactions") else []
    
    # Load sprite based on type
    _load_sprite()

func _load_sprite():
    # Placeholder - will load actual sprites later
    sprite.modulate = _get_type_color()

func _get_type_color() -> Color:
    match object_type:
        "furniture": return Color(0.6, 0.4, 0.2)
        "device": return Color(0.3, 0.3, 0.5)
        "container": return Color(0.5, 0.3, 0.4)
        "tool": return Color(0.7, 0.7, 0.3)
        "portal": return Color(0.3, 0.6, 0.6)
        "living": return Color(0.3, 0.6, 0.3)
        _: return Color(0.5, 0.5, 0.5)

func interact(action: String, agent: Node) -> Dictionary:
    if action not in interactions:
        return {"success": false, "reason": "Action not available"}
    
    var result = _execute_action(action, agent)
    emit_signal("interacted", action, {"agent": agent.name}, result)
    return result

func _execute_action(action: String, agent: Node) -> Dictionary:
    # Override in subclasses
    return {"success": true, "message": "%s: %s" % [object_id, action]}

func get_state() -> Dictionary:
    return {
        "id": object_id,
        "type": object_type,
        "state": state,
        "position": GlobalState.world_to_tile(global_position),
        "interactions": interactions
    }