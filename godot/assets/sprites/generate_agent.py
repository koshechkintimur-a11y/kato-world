#!/usr/bin/env python3
"""Generate agent sprite (simple pixel art)"""
from PIL import Image, ImageDraw

# Agent sprite sheet: 4 directions x 2 frames (idle/walk) = 8 frames, each 16x24
img = Image.new('RGBA', (64, 96), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Colors
BODY_COLOR = (100, 180, 220, 255)  # Light blue
OUTLINE_COLOR = (40, 80, 120, 255)
EYE_COLOR = (255, 255, 255, 255)
PUPIL_COLOR = (40, 40, 40, 255)

def draw_agent(draw, x, y, direction, walking=False):
    """Draw agent at position (x,y) facing direction"""
    # Body (16x20)
    # Head
    draw.ellipse([x+4, y, x+11, y+7], fill=BODY_COLOR, outline=OUTLINE_COLOR)
    # Body
    draw.rectangle([x+3, y+7, x+12, y+19], fill=BODY_COLOR, outline=OUTLINE_COLOR)
    
    # Eyes based on direction
    if direction == "down":
        # Front view - two eyes
        draw.ellipse([x+5, y+2, x+7, y+4], fill=EYE_COLOR)
        draw.ellipse([x+9, y+2, x+11, y+4], fill=EYE_COLOR)
        draw.ellipse([x+5, y+2, x+6, y+3], fill=PUPIL_COLOR)
        draw.ellipse([x+9, y+2, x+10, y+3], fill=PUPIL_COLOR)
    elif direction == "up":
        # Back view - no eyes visible, maybe hair
        draw.rectangle([x+4, y+1, x+11, y+3], fill=(60, 40, 30, 255))
    elif direction == "left":
        # Left profile
        draw.ellipse([x+4, y+2, x+6, y+4], fill=EYE_COLOR)
        draw.ellipse([x+4, y+2, x+5, y+3], fill=PUPIL_COLOR)
    elif direction == "right":
        # Right profile
        draw.ellipse([x+9, y+2, x+11, y+4], fill=EYE_COLOR)
        draw.ellipse([x+10, y+2, x+11, y+3], fill=PUPIL_COLOR)
    
    # Legs for walking animation
    if walking:
        draw.rectangle([x+4, y+18, x+7, y+23], fill=BODY_COLOR, outline=OUTLINE_COLOR)
        draw.rectangle([x+9, y+19, x+12, y+24], fill=BODY_COLOR, outline=OUTLINE_COLOR)
    else:
        draw.rectangle([x+4, y+19, x+7, y+24], fill=BODY_COLOR, outline=OUTLINE_COLOR)
        draw.rectangle([x+9, y+19, x+12, y+24], fill=BODY_COLOR, outline=OUTLINE_COLOR)

# Directions: down, up, left, right
directions = ["down", "up", "left", "right"]
frame_h = 24

for i, direction in enumerate(directions):
    y = i * frame_h
    # Idle frame
    draw_agent(draw, 0, y, direction, walking=False)
    # Walk frame
    draw_agent(draw, 16, y, direction, walking=True)

img.save('agent_spritesheet.png')
print("Generated agent_spritesheet.png")