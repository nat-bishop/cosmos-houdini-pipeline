#!/usr/bin/env python3
"""
Test script to demonstrate PromptSpec auto-naming functionality.
"""

from cosmos_workflow.utils.smart_naming import generate_smart_name

# Test prompts
test_prompts = [
    "Futuristic cyberpunk city with neon lights and flying cars",
    "Transform this into a Van Gogh style painting with swirling skies",
    "A serene Japanese garden with cherry blossoms and a koi pond",
    "Epic medieval battle scene with dragons breathing fire",
    "Underwater coral reef ecosystem with tropical fish",
    "Abstract geometric patterns with vibrant colors",
    "Cozy cabin in a snowy forest during winter",
    "Steampunk airship flying through cloudy skies",
]

print("PromptSpec Smart Naming Examples")
print("=" * 50)
print("\nPrompt -> Generated Name")
print("-" * 50)

for prompt in test_prompts:
    name = generate_smart_name(prompt, max_length=30)
    print(f"\n{prompt[:60]}...")
    print(f"  -> {name}")

print("\n" + "=" * 50)
print("\nCLI Usage Examples:")
print("-" * 50)
print('\n# Auto-generate name:')
print('python -m cosmos_workflow.cli create-spec "Futuristic city with neon lights"')
print('# Result: futuristic_city_neon')

print('\n# Provide explicit name:')
print('python -m cosmos_workflow.cli create-spec "My prompt" --name my_custom_name')
print('# Result: my_custom_name')