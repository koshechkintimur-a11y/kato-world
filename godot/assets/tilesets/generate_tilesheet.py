#!/usr/bin/env python3
"""Generate a simple tilesheet for Kato World prototype"""
from PIL import Image, ImageDraw

# Create a 48x16 tilesheet (3 tiles of 16x16)
img = Image.new('RGBA', (48, 16), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Tile 0: Floor - light gray
draw.rectangle([0, 0, 15, 15], fill=(180, 180, 180, 255))
# Add subtle pattern
for x in range(0, 16, 4):
    for y in range(0, 16, 4):
        draw.rectangle([x, y, x+1, y+1], fill=(160, 160, 160, 255))

# Tile 1: Wall - dark brown
draw.rectangle([16, 0, 31, 15], fill=(100, 60, 30, 255))
# Brick pattern
for bx in range(16, 32, 8):
    for by in range(0, 16, 4):
        offset = 4 if (by // 4) % 2 == 0 else 0
        draw.rectangle([bx + offset, by, bx + offset + 7, by + 3], outline=(80, 40, 20, 255))

# Tile 2: Grass - green
draw.rectangle([32, 0, 47, 15], fill=(60, 140, 60, 255))
# Grass blades
import random
random.seed(42)
for _ in range(30):
    x = random.randint(32, 47)
    y = random.randint(0, 15)
    h = random.randint(2, 5)
    draw.line([x, y, x, y-h], fill=(40, 120, 40, 255))

img.save('tilesheet.png')
print("Generated tilesheet.png")