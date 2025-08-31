#!/usr/bin/env python3
"""
Create a test image and test the full AI pipeline.
"""

from PIL import Image, ImageDraw
import numpy as np
from pathlib import Path

# Create test directory
test_dir = Path("test_images")
test_dir.mkdir(exist_ok=True)

# Create a more complex test image
print("Creating test image...")
img = Image.new('RGB', (512, 512), color='skyblue')
draw = ImageDraw.Draw(img)

# Draw a simple scene - a house with a tree
# House
draw.rectangle([150, 250, 350, 400], fill='brown', outline='black', width=2)
# Roof
draw.polygon([(150, 250), (250, 150), (350, 250)], fill='red', outline='black', width=2)
# Door
draw.rectangle([225, 320, 275, 400], fill='#654321', outline='black')  # Dark brown
# Window
draw.rectangle([180, 280, 220, 320], fill='#ADD8E6', outline='black')  # Light blue
draw.rectangle([280, 280, 320, 320], fill='#ADD8E6', outline='black')  # Light blue

# Tree
draw.rectangle([380, 350, 420, 400], fill='brown')  # Trunk
draw.ellipse([360, 280, 440, 360], fill='green', outline='#006400')  # Leaves (dark green)

# Sun
draw.ellipse([30, 30, 90, 90], fill='yellow', outline='orange')

# Save as color.0001.png (Cosmos format)
test_file = test_dir / "color.0001.png"
img.save(test_file)
print(f"Test image saved to: {test_file}")

# Now test with the converter
print("\nTesting AI description generation...")
from cosmos_workflow.local_ai.cosmos_sequence import CosmosVideoConverter

converter = CosmosVideoConverter()

# Test description generation
description = converter._generate_ai_description([test_file])
print(f"Generated description: '{description}'")

if description and "Sequence with" not in description:
    # Test smart name generation
    name = converter._generate_smart_name(description)
    print(f"Generated smart name: '{name}'")
    print("\n[SUCCESS] Full AI pipeline working correctly!")
else:
    print("\n[WARNING] AI description fell back to default")

# Clean up
print(f"\nTest image saved in: {test_file}")
print("You can manually inspect it to verify the description makes sense.")