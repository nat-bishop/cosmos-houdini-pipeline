#!/usr/bin/env python3
"""Converter for transforming PromptSpec and RunSpec to NVIDIA Cosmos Transfer format.

This module handles the conversion from our internal schema to the controlnet_specs
format expected by NVIDIA Cosmos Transfer inference.
"""

import json
from pathlib import Path
from typing import Any

from .schemas import PromptSpec, RunSpec


class CosmosConverter:
    """Converts internal schemas to NVIDIA Cosmos Transfer format."""

    @staticmethod
    def prompt_spec_to_cosmos(
        prompt_spec: PromptSpec, run_spec: RunSpec | None = None
    ) -> dict[str, Any]:
        """Convert PromptSpec (and optionally RunSpec) to Cosmos Transfer controlnet_specs format.

        Args:
            prompt_spec: The PromptSpec containing prompt and control inputs
            run_spec: Optional RunSpec containing weights and parameters

        Returns:
            Dictionary in Cosmos Transfer controlnet_specs format
        """
        # Start with base structure
        cosmos_spec = {
            "prompt": prompt_spec.prompt,
            "input_video_path": prompt_spec.input_video_path,
        }

        # Note: negative_prompt is handled as a command-line parameter to the inference script,
        # not as part of the controlnet_specs JSON

        # Process control inputs and weights
        if run_spec:
            # Use weights from RunSpec
            control_weights = run_spec.control_weights

            # Add seed if specified in parameters
            if "seed" in run_spec.parameters:
                cosmos_spec["seed"] = run_spec.parameters["seed"]

            # Add num_video_frames if specified
            if "num_video_frames" in run_spec.parameters:
                cosmos_spec["num_video_frames"] = run_spec.parameters["num_video_frames"]
        else:
            # Default weights if no RunSpec provided
            control_weights = {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}

        # Map control inputs to Cosmos format
        for modality, input_path in prompt_spec.control_inputs.items():
            if modality in control_weights:
                weight = control_weights.get(modality, 0.0)

                # Skip if weight is 0
                if weight == 0:
                    continue

                # Create control entry
                control_entry = {"control_weight": weight}

                # Add input_control for modalities that need explicit input
                if modality in ["depth", "seg", "keypoint"] and input_path:
                    control_entry["input_control"] = input_path

                cosmos_spec[modality] = control_entry

        # Add any control weights for modalities not in control_inputs
        # (e.g., vis and edge which don't always need input videos)
        for modality, weight in control_weights.items():
            if modality not in cosmos_spec and weight > 0:
                cosmos_spec[modality] = {"control_weight": weight}

        return cosmos_spec

    @staticmethod
    def run_spec_to_cosmos_params(
        run_spec: RunSpec, prompt_spec: PromptSpec | None = None
    ) -> dict[str, Any]:
        """Extract Cosmos Transfer inference parameters from RunSpec.

        These are parameters that would be passed to the inference script
        rather than included in the controlnet_specs JSON.

        Args:
            run_spec: The RunSpec containing parameters
            prompt_spec: Optional PromptSpec for additional parameters like negative_prompt

        Returns:
            Dictionary of Cosmos Transfer inference parameters
        """
        params = {}

        # Map our parameters to Cosmos parameters
        param_mapping = {
            "num_steps": "num_steps",
            "guidance": "guidance_scale",
            "sigma_max": "sigma_max",
            "fps": "fps",
            "seed": "seed",
            "blur_strength": "blur_strength",
            "canny_threshold": "canny_threshold",
        }

        for our_param, cosmos_param in param_mapping.items():
            if our_param in run_spec.parameters:
                params[cosmos_param] = run_spec.parameters[our_param]

        # Add execution-specific parameters
        params["output_dir"] = run_spec.output_path if run_spec.output_path else "outputs"
        params["video_save_name"] = f"{run_spec.name}_{run_spec.id}"

        # Add negative prompt if provided in PromptSpec
        if prompt_spec and prompt_spec.negative_prompt:
            params["negative_prompt"] = prompt_spec.negative_prompt

        return params

    @staticmethod
    def save_cosmos_spec(cosmos_spec: dict[str, Any], output_path: str | Path) -> Path:
        """Save Cosmos Transfer controlnet_specs to JSON file.

        Args:
            cosmos_spec: The Cosmos format specification
            output_path: Path where to save the JSON file

        Returns:
            Path to the saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(cosmos_spec, f, indent=2)

        return output_path

    @staticmethod
    def validate_cosmos_spec(cosmos_spec: dict[str, Any]) -> bool:
        """Validate that a specification meets Cosmos Transfer requirements.

        Args:
            cosmos_spec: The specification to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if "prompt" not in cosmos_spec:
            print("[ERROR] Missing required field: prompt")
            return False

        if "input_video_path" not in cosmos_spec:
            print("[ERROR] Missing required field: input_video_path")
            return False

        # Check that at least one control modality is present
        control_modalities = ["vis", "edge", "depth", "seg", "keypoint", "upscale"]
        has_control = any(mod in cosmos_spec for mod in control_modalities)

        if not has_control:
            print("[WARNING] No control modalities specified")

        # Validate control weights
        for modality in control_modalities:
            if modality in cosmos_spec:
                control = cosmos_spec[modality]

                if not isinstance(control, dict):
                    print(f"[ERROR] {modality} must be a dictionary")
                    return False

                if "control_weight" not in control:
                    print(f"[ERROR] {modality} missing control_weight")
                    return False

                # Check weight is valid (number or path to .pt file)
                weight = control["control_weight"]
                if not isinstance(weight, int | float | str):
                    print(f"[ERROR] {modality} control_weight must be number or string")
                    return False

                if isinstance(weight, str) and not weight.endswith(".pt"):
                    print(f"[WARNING] {modality} control_weight string should be .pt file")

        return True

    @staticmethod
    def create_upscaler_spec(input_video_path: str, upscale_weight: float = 0.7) -> dict[str, Any]:
        """Create a Cosmos Transfer upscaler specification.

        Args:
            input_video_path: Path to video to upscale
            upscale_weight: Weight for upscaling control (0.0-1.0)

        Returns:
            Dictionary in Cosmos Transfer upscaler format
        """
        return {"input_video_path": input_video_path, "upscale": {"control_weight": upscale_weight}}

    @staticmethod
    def merge_specs(base_spec: dict[str, Any], override_spec: dict[str, Any]) -> dict[str, Any]:
        """Merge two Cosmos specifications, with override taking precedence.

        Useful for combining base specs with run-specific overrides.

        Args:
            base_spec: The base specification
            override_spec: Specification with overrides

        Returns:
            Merged specification
        """
        import copy

        merged = copy.deepcopy(base_spec)

        for key, value in override_spec.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Merge nested dictionaries (e.g., control modalities)
                merged[key].update(value)
            else:
                # Override completely
                merged[key] = value

        return merged


def main():
    """Example usage of the CosmosConverter."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Convert specs to Cosmos Transfer format")
    parser.add_argument("prompt_spec_path", help="Path to PromptSpec JSON")
    parser.add_argument("--run-spec", help="Path to RunSpec JSON")
    parser.add_argument("--output", help="Output path for Cosmos spec", default="cosmos_spec.json")
    parser.add_argument("--validate", action="store_true", help="Validate the output spec")

    args = parser.parse_args()

    try:
        # Load PromptSpec
        prompt_spec = PromptSpec.load(Path(args.prompt_spec_path))

        # Load RunSpec if provided
        run_spec = None
        if args.run_spec:
            run_spec = RunSpec.load(Path(args.run_spec))

        # Convert to Cosmos format
        converter = CosmosConverter()
        cosmos_spec = converter.prompt_spec_to_cosmos(prompt_spec, run_spec)

        # Validate if requested
        if args.validate:
            if converter.validate_cosmos_spec(cosmos_spec):
                print("[SUCCESS] Cosmos spec is valid")
            else:
                print("[ERROR] Cosmos spec validation failed")
                sys.exit(1)

        # Save the spec
        output_path = converter.save_cosmos_spec(cosmos_spec, args.output)
        print(f"[SUCCESS] Saved Cosmos spec to: {output_path}")

        # Print the spec for review
        print("\nGenerated Cosmos Transfer controlnet_specs:")
        print(json.dumps(cosmos_spec, indent=2))

        # If RunSpec provided, also show inference parameters
        if run_spec:
            params = converter.run_spec_to_cosmos_params(run_spec, prompt_spec)
            print("\nInference parameters:")
            print(json.dumps(params, indent=2))

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
