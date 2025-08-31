#!/usr/bin/env python3
"""
Test script to verify AI functionality with real models.
This tests the actual BLIP model loading and inference.
"""

import sys
import io
import numpy as np
from pathlib import Path
from PIL import Image

# Fix Unicode output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_ai_description():
    """Test AI description generation with real models."""
    print("Testing AI Description Generation with Real Models")
    print("=" * 50)
    
    try:
        # Test 1: Import transformers
        print("\n1. Testing transformers import...")
        from transformers import BlipProcessor, BlipForConditionalGeneration
        print("   [OK] Transformers imported successfully")
        
        # Test 2: Load models
        print("\n2. Loading BLIP models...")
        print("   This may take a moment on first run (downloading ~400MB)...")
        
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        print("   [OK] Processor loaded")
        
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        print("   [OK] Model loaded")
        
        # Test 3: Create a test image
        print("\n3. Creating test image...")
        # Create a simple test image (red square on blue background)
        test_image = Image.new('RGB', (224, 224), color='blue')
        pixels = test_image.load()
        for i in range(50, 150):
            for j in range(50, 150):
                pixels[i, j] = (255, 0, 0)  # Red square
        print("   [OK] Test image created (red square on blue background)")
        
        # Test 4: Generate description
        print("\n4. Generating AI description...")
        inputs = processor(test_image, return_tensors="pt")
        out = model.generate(**inputs, max_length=50)
        description = processor.decode(out[0], skip_special_tokens=True)
        print(f"   [OK] Generated description: '{description}'")
        
        # Test 5: Test with our actual code
        print("\n5. Testing with CosmosVideoConverter...")
        from cosmos_workflow.local_ai.cosmos_sequence import CosmosVideoConverter
        
        converter = CosmosVideoConverter()
        
        # Test smart name generation
        test_descriptions = [
            "a modern staircase with dramatic lighting",
            "a red car driving on a highway",
            "a person walking in a park",
            "a futuristic city skyline at night"
        ]
        
        print("\n   Smart Name Generation Tests:")
        for desc in test_descriptions:
            name = converter._generate_smart_name(desc)
            print(f"   '{desc}' → '{name}'")
        
        print("\n[SUCCESS] All AI functionality tests passed!")
        return True
        
    except ImportError as e:
        print(f"\n[ERROR] Import Error: {e}")
        print("   Make sure transformers and torch are installed:")
        print("   pip install transformers torch torchvision pillow accelerate")
        return False
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_real_png():
    """Test with a real PNG file if available."""
    print("\n" + "=" * 50)
    print("Testing with Real PNG Files")
    print("=" * 50)
    
    try:
        from cosmos_workflow.local_ai.cosmos_sequence import CosmosVideoConverter
        import cv2
        
        converter = CosmosVideoConverter()
        
        # Look for test PNG files
        test_dirs = [
            Path("F:/Art/cosmos-houdini-experiments/inputs/renders/v3"),
            Path("./test_images"),
            Path("./inputs/renders")
        ]
        
        png_found = False
        for test_dir in test_dirs:
            if test_dir.exists():
                png_files = list(test_dir.glob("*.png"))
                if png_files:
                    print(f"\nFound {len(png_files)} PNG files in {test_dir}")
                    
                    # Test with first PNG
                    test_file = png_files[0]
                    print(f"Testing with: {test_file.name}")
                    
                    # Try to generate description
                    description = converter._generate_ai_description([test_file])
                    print(f"Generated description: '{description}'")
                    
                    if description and "Sequence with" not in description:
                        # Successfully generated AI description
                        name = converter._generate_smart_name(description)
                        print(f"Generated smart name: '{name}'")
                        print("[SUCCESS] Real PNG test successful!")
                    else:
                        print("[WARNING] AI description generation fell back to default")
                    
                    png_found = True
                    break
        
        if not png_found:
            print("[INFO] No PNG files found for testing")
            print("  You can create a test_images directory with PNG files to test")
            
    except Exception as e:
        print(f"[ERROR] Error testing with real PNG: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run tests
    success = test_ai_description()
    
    if success:
        test_with_real_png()
    
    sys.exit(0 if success else 1)