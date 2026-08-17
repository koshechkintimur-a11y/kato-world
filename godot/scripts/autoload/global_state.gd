extends Node

# Global singleton for shared state and constants
class_name GlobalState

# World constants
const TILE_SIZE = 16
const WORLD_WIDTH = 50
const WORLD_HEIGHT = 30
const TICK_RATE = 10  # ticks per second
const DAY_LENGTH_TICKS = 2400  # 4 minutes = 1 day

# Agent constants
const AGENT_MAX_ENERGY = 100.0
const AGENT_MAX_COMFORT = 100.0
const AGENT_MAX_STRESS = 100.0
const AGENCY_MAX_INTEGRITY = 100.0

# Emotion constants
const BASE_EMOTIONS = ["joy", "fear", "anger", "sadness", "curiosity", "trust", "attachment"]

# Hormone/Homeostasis constants
const HORMONES = ["energy", "stress", "arousal", "reward", "safety", "social", "pain"]

# System 1/2 thresholds
const SYSTEM1_CONFIDENCE_THRESHOLD = 0.7
const STRESS_LIMIT_FOR_SYSTEM2 = 60.0

# Memory constants
const WORKING_MEMORY_CAPACITY = 15
const EPISODIC_SALIENCE_THRESHOLD = 0.5

# Dream Gateway - divine whispers
const DREAM_GATEWAY_ENABLED = true
const DREAM_PROCESSING_CHANCE = 0.3  # 30% chance per sleep cycle to receive divine thought

# Signal definitions
signal world_tick(tick: int, delta: float)
signal agent_state_changed(state: Dictionary)
signal event_logged(event: Dictionary)
signal dream_received(dream: Dictionary)

var current_tick: int = 0
var time_of_day: float = 0.0  # 0.0 - 1.0
var is_paused: bool = false

func _ready():
    print("GlobalState initialized - Kato World ready")

func get_tick() -> int:
    return current_tick

func advance_tick(delta: float):
    if is_paused:
        return
    current_tick += 1
    time_of_day = fmod(current_tick / DAY_LENGTH_TICKS, 1.0)
    emit_signal("world_tick", current_tick, delta)

func pause():
    is_paused = true

func resume():
    is_paused = false

func tile_to_world(tile_pos: Vector2i) -> Vector2:
    return Vector2(tile_pos.x * TILE_SIZE, tile_pos.y * TILE_SIZE)

func world_to_tile(world_pos: Vector2) -> Vector2i:
    return Vector2i(int(world_pos.x / TILE_SIZE), int(world_pos.y / TILE_SIZE))

func is_valid_tile(tile_pos: Vector2i) -> bool:
    return tile_pos.x >= 0 and tile_pos.x < WORLD_WIDTH and tile_pos.y >= 0 and tile_pos.y < WORLD_HEIGHT