extends CharacterBody2D

# NPC entity - teacher, gardener, librarian, mirror_keeper
class_name NPC

signal dialogue_started(npc_id: String, dialogue_data: Dictionary)
signal dialogue_ended(npc_id: String)

@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var interaction_area: Area2D = $InteractionArea

var npc_id: String = ""
var npc_type: String = "teacher"
var mood: String = "calm"
var knowledge: Array = []
var dialogue_state: String = "idle"
var _dialogue_tree: Dictionary = {}

func _ready():
    interaction_area.body_entered.connect(_on_agent_entered)
    interaction_area.body_exited.connect(_on_agent_exited)
    _setup_animations()

func _setup_animations():
    if animated_sprite and animated_sprite.sprite_frames:
        animated_sprite.play("idle_down")

func setup(npc_data: Dictionary):
    npc_id = npc_data.id
    npc_type = npc_data.type
    mood = npc_data.mood
    knowledge = npc_data.knowledge
    dialogue_state = npc_data.dialogue_state
    _load_dialogue_tree()

func _load_dialogue_tree():
    # Dialogue trees will be loaded from JSON files later
    _dialogue_tree = {
        "greeting": {
            "text": "Приветствую, малыш. Чем могу помочь?",
            "options": ["question", "learn", "task", "goodbye"]
        },
        "question": {
            "text": "Спроси что угодно. Знания — это свет в темноте.",
            "options": ["causality", "creation", "outside", "back"]
        }
    }

func _on_agent_entered(body: Node):
    if body.name == "Kato":
        EventBus.emit_perception(npc_id, {
            "id": npc_id,
            "type": npc_type,
            "position": GlobalState.world_to_tile(global_position),
            "mood": mood,
            "knowledge": knowledge,
            "can_talk": true
        })

func _on_agent_exited(body: Node):
    if body.name == "Kato":
        # Agent walked away
        pass

func start_dialogue() -> Dictionary:
    dialogue_state = "active"
    var greeting = _dialogue_tree.get("greeting", {"text": "...", "options": []})
    return {
        "npc_id": npc_id,
        "type": npc_type,
        "mood": mood,
        "dialogue": greeting
    }

func respond_to_choice(choice: String) -> Dictionary:
    var response = _dialogue_tree.get(choice, {"text": "Не понимаю...", "options": ["back"]})
    return {
        "npc_id": npc_id,
        "dialogue": response
    }

func end_dialogue():
    dialogue_state = "idle"
    emit_signal("dialogue_ended", npc_id)