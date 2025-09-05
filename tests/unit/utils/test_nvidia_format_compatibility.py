"""Test nvidia_format.py produces correct NVIDIA Cosmos JSON format.

This test verifies that our conversion functions create JSON that matches
the exact format expected by NVIDIA Cosmos Transfer scripts.
"""

import json

from cosmos_workflow.utils import nvidia_format


def test_inference_format_matches_nvidia_requirements():
    """Test that inference JSON matches NVIDIA's expected format."""
    # Create sample database dicts (what we store in our DB)
    prompt_dict = {
        "id": "ps_test",
        "prompt_text": "A futuristic cyberpunk city at night",
        "negative_prompt": "bad quality, low resolution",
        "inputs": {
            "video": "inputs/videos/test/color.mp4",
            "depth": "inputs/videos/test/depth.mp4",
            "seg": "inputs/videos/test/segmentation.mp4",
        },
        "parameters": {},
    }

    run_dict = {
        "id": "rs_test123",
        "execution_config": {
            "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
            "num_steps": 35,
            "guidance": 7.0,
            "seed": 42,
            "fps": 8,
        },
    }

    # Convert using our function
    result = nvidia_format.to_cosmos_inference_json(prompt_dict, run_dict)

    # Verify top-level fields that NVIDIA expects
    assert "prompt" in result
    assert result["prompt"] == "A futuristic cyberpunk city at night"

    assert "negative_prompt" in result
    assert result["negative_prompt"] == "bad quality, low resolution"

    assert "input_video_path" in result
    assert result["input_video_path"] == "inputs/videos/test/color.mp4"

    # Verify control weight structure matches NVIDIA format
    # Each control type should be its own object with control_weight field
    assert "vis" in result
    assert isinstance(result["vis"], dict)
    assert "control_weight" in result["vis"]
    assert result["vis"]["control_weight"] == 0.25

    assert "edge" in result
    assert isinstance(result["edge"], dict)
    assert "control_weight" in result["edge"]
    assert result["edge"]["control_weight"] == 0.25

    assert "depth" in result
    assert isinstance(result["depth"], dict)
    assert "control_weight" in result["depth"]
    assert result["depth"]["control_weight"] == 0.25
    assert "input_control" in result["depth"]
    assert result["depth"]["input_control"] == "inputs/videos/test/depth.mp4"

    assert "seg" in result
    assert isinstance(result["seg"], dict)
    assert "control_weight" in result["seg"]
    assert result["seg"]["control_weight"] == 0.25
    assert "input_control" in result["seg"]
    assert result["seg"]["input_control"] == "inputs/videos/test/segmentation.mp4"

    # Verify additional parameters
    assert result["num_steps"] == 35
    assert result["guidance"] == 7.0
    assert result["seed"] == 42
    assert result["fps"] == 8

    # Ensure NO nested control_weights or control_inputs objects (old wrong format)
    assert "control_weights" not in result
    assert "control_inputs" not in result

    # Verify JSON is serializable
    json_str = json.dumps(result, indent=2)
    assert json_str  # Should not raise


def test_upscale_format_matches_nvidia_requirements():
    """Test that upscale JSON matches NVIDIA's expected format."""
    # Create sample database dicts
    prompt_dict = {
        "id": "ps_test",
        "prompt_text": "A beautiful landscape",
        "negative_prompt": "",
        "inputs": {
            "video": "outputs/test_run/output.mp4",
            "depth": "inputs/videos/test/depth.mp4",
            "seg": "inputs/videos/test/segmentation.mp4",
        },
        "parameters": {},
    }

    run_dict = {
        "id": "rs_upscale_test",
        "execution_config": {"weights": {"vis": 0.3, "edge": 0.2, "depth": 0.3, "seg": 0.2}},
    }

    # Convert for upscaling
    result = nvidia_format.to_cosmos_upscale_json(prompt_dict, run_dict, upscale_weight=0.7)

    # Should have all the same fields as inference
    assert "prompt" in result
    assert "input_video_path" in result
    assert "vis" in result
    assert "edge" in result
    assert "depth" in result
    assert "seg" in result

    # Plus upscale-specific fields
    assert "upscale" in result
    assert isinstance(result["upscale"], dict)
    assert "control_weight" in result["upscale"]
    assert result["upscale"]["control_weight"] == 0.7

    # Upscaling uses fewer steps
    assert result["num_steps"] == 10

    # Verify JSON is serializable
    json_str = json.dumps(result, indent=2)
    assert json_str


def test_format_matches_nvidia_documentation_example():
    """Test against the exact example from NVIDIA documentation."""
    # This is the expected format from NVIDIA docs
    expected_structure = {
        "prompt": "The video is set in a modern, well-lit office environment...",
        "input_video_path": "assets/example1_input_video.mp4",
        "vis": {"control_weight": 0.25},
        "edge": {"control_weight": 0.25},
        "depth": {"input_control": "assets/example1_depth.mp4", "control_weight": 0.25},
        "seg": {"input_control": "assets/example1_seg.mp4", "control_weight": 0.25},
    }

    # Create our database format
    prompt_dict = {
        "prompt_text": "The video is set in a modern, well-lit office environment...",
        "inputs": {
            "video": "assets/example1_input_video.mp4",
            "depth": "assets/example1_depth.mp4",
            "seg": "assets/example1_seg.mp4",
        },
    }

    run_dict = {
        "execution_config": {"weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}}
    }

    # Convert
    result = nvidia_format.to_cosmos_inference_json(prompt_dict, run_dict)

    # Check structure matches (ignoring extra fields like num_steps)
    for key in expected_structure:
        assert key in result
        if key in ["vis", "edge", "depth", "seg"]:
            assert "control_weight" in result[key]
            assert result[key]["control_weight"] == expected_structure[key]["control_weight"]
            if "input_control" in expected_structure[key]:
                assert "input_control" in result[key]
                assert result[key]["input_control"] == expected_structure[key]["input_control"]


def test_handles_missing_fields_gracefully():
    """Test that missing fields are handled with defaults."""
    # Minimal prompt dict
    prompt_dict = {"prompt_text": "Test prompt", "inputs": {}}

    # Minimal run dict
    run_dict = {"id": "rs_minimal", "execution_config": {}}

    # Should not crash
    result = nvidia_format.to_cosmos_inference_json(prompt_dict, run_dict)

    # Should have defaults
    assert result["prompt"] == "Test prompt"
    assert result["negative_prompt"] == ""
    assert result["input_video_path"] == ""

    # Control weights should default to 0.25
    assert result["vis"]["control_weight"] == 0.25
    assert result["edge"]["control_weight"] == 0.25
    assert result["depth"]["control_weight"] == 0.25
    assert result["seg"]["control_weight"] == 0.25

    # Other defaults
    assert result["num_steps"] == 35
    assert result["guidance"] == 7.0
    assert result["seed"] == 42
    assert result["fps"] == 8
