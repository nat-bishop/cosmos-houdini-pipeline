#!/usr/bin/env python3
"""
Main CLI interface for Cosmos-Transfer1 Python workflows.
Provides a user-friendly command-line interface for all workflow operations.
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Optional
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator
from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec, SchemaUtils


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def validate_prompt_file(prompt_file: str) -> Path:
    """Validate prompt file exists and return Path object."""
    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_path


def run_full_cycle(
    prompt_file: Path,
    videos_subdir: Optional[str],
    no_upscale: bool,
    upscale_weight: float,
    num_gpu: int,
    cuda_devices: str,
    verbose: bool
) -> None:
    """Run complete workflow cycle."""
    setup_logging(verbose)
    
    try:
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run_full_cycle(
            prompt_file=prompt_file,
            videos_subdir=videos_subdir,
            no_upscale=no_upscale,
            upscale_weight=upscale_weight,
            num_gpu=num_gpu,
            cuda_devices=cuda_devices
        )
        
        if verbose:
            print(f"\n📊 Workflow Results:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        sys.exit(1)


def run_inference_only(
    prompt_file: Path,
    videos_subdir: Optional[str],
    num_gpu: int,
    cuda_devices: str,
    verbose: bool
) -> None:
    """Run only inference step."""
    setup_logging(verbose)
    
    try:
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run_inference_only(
            prompt_file=prompt_file,
            videos_subdir=videos_subdir,
            num_gpu=num_gpu,
            cuda_devices=cuda_devices
        )
        
        if verbose:
            print(f"\n📊 Inference Results:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Inference failed: {e}")
        sys.exit(1)


def run_upscaling_only(
    prompt_file: Path,
    upscale_weight: float,
    num_gpu: int,
    cuda_devices: str,
    verbose: bool
) -> None:
    """Run only upscaling step."""
    setup_logging(verbose)
    
    try:
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run_upscaling_only(
            prompt_file=prompt_file,
            upscale_weight=upscale_weight,
            num_gpu=num_gpu,
            cuda_devices=cuda_devices
        )
        
        if verbose:
            print(f"\n📊 Upscaling Results:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Upscaling failed: {e}")
        sys.exit(1)


def check_status(verbose: bool) -> None:
    """Check remote instance status."""
    setup_logging(verbose)
    
    try:
        orchestrator = WorkflowOrchestrator()
        status = orchestrator.check_remote_status()
        
        print("\n🔍 Remote Instance Status:")
        print(f"  SSH Status: {status['ssh_status']}")
        
        if status['ssh_status'] == 'connected':
            print(f"  Remote Directory: {status['remote_directory']}")
            print(f"  Directory Exists: {status['remote_directory_exists']}")
            
            docker_status = status['docker_status']
            print(f"  Docker Running: {docker_status['docker_running']}")
            
            if verbose and docker_status['docker_running']:
                print(f"\n🐳 Docker Images:")
                print(docker_status['available_images'])
                
                print(f"\n📦 Running Containers:")
                print(docker_status['running_containers'])
        else:
            print(f"  Error: {status['error']}")
        
    except Exception as e:
        print(f"\n❌ Status check failed: {e}")
        sys.exit(1)


def create_prompt_spec(
    name: str,
    prompt_text: str,
    negative_prompt: str,
    input_video_path: Optional[str],
    control_inputs: Optional[list],
    is_upsampled: bool,
    parent_prompt_text: Optional[str],
    verbose: bool
) -> None:
    """Create a new PromptSpec using the new schema system."""
    setup_logging(verbose)
    
    try:
        # Parse control inputs
        control_inputs_dict = {}
        if control_inputs:
            for i in range(0, len(control_inputs), 2):
                if i + 1 < len(control_inputs):
                    modality = control_inputs[i]
                    path = control_inputs[i + 1]
                    control_inputs_dict[modality] = path
        
        # Build video path
        if input_video_path:
            video_path = input_video_path
        else:
            video_path = f"inputs/videos/{name}/color.mp4"
        
        # Default control inputs
        if not control_inputs_dict:
            control_inputs_dict = {
                "depth": f"inputs/videos/{name}/depth.mp4",
                "seg": f"inputs/videos/{name}/segmentation.mp4"
            }
        
        # Generate unique ID
        prompt_id = SchemaUtils.generate_prompt_id(prompt_text, video_path, control_inputs_dict)
        
        # Create PromptSpec
        from datetime import datetime
        timestamp = datetime.now().isoformat() + "Z"
        prompt_spec = PromptSpec(
            id=prompt_id,
            name=name,
            prompt=prompt_text,
            negative_prompt=negative_prompt,
            input_video_path=video_path,
            control_inputs=control_inputs_dict,
            timestamp=timestamp,
            is_upsampled=is_upsampled,
            parent_prompt_text=parent_prompt_text
        )
        
        # Save to file
        from cosmos_workflow.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        local_config = config_manager.get_local_config()
        
        # Create date-based directory structure
        from cosmos_workflow.prompts.schemas import DirectoryManager
        dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)
        dir_manager.ensure_directories_exist()
        
        file_path = dir_manager.get_prompt_file_path(name, timestamp, prompt_id)
        prompt_spec.save(file_path)
        
        print(f"\n✅ Created PromptSpec: {prompt_id}")
        print(f"   Saved to: {file_path}")
        print(f"   Name: {name}")
        print(f"   Video: {video_path}")
        print(f"   Control Inputs: {list(control_inputs_dict.keys())}")
        print(f"\n💡 To create a RunSpec for this prompt:")
        print(f"   python -m cosmos_workflow.main create-run {file_path}")
        
    except Exception as e:
        print(f"\n❌ Failed to create PromptSpec: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def create_run_spec(
    prompt_spec_path: str,
    control_weights: Optional[list],
    num_steps: int,
    guidance: float,
    sigma_max: float,
    blur_strength: str,
    canny_threshold: str,
    fps: int,
    seed: int,
    custom_output_path: Optional[str],
    verbose: bool
) -> None:
    """Create a new RunSpec for executing a PromptSpec."""
    setup_logging(verbose)
    
    try:
        # Load the PromptSpec
        prompt_spec_file = Path(prompt_spec_path)
        if not prompt_spec_file.exists():
            print(f"❌ PromptSpec file not found: {prompt_spec_path}")
            sys.exit(1)
        
        prompt_spec = PromptSpec.load(prompt_spec_file)
        
        # Build control weights
        if control_weights:
            weights_dict = {
                "vis": control_weights[0],
                "edge": control_weights[1],
                "depth": control_weights[2],
                "seg": control_weights[3]
            }
        else:
            weights_dict = SchemaUtils.get_default_control_weights()
        
        # Build parameters
        parameters = {
            "num_steps": num_steps,
            "guidance": guidance,
            "sigma_max": sigma_max,
            "blur_strength": blur_strength,
            "canny_threshold": canny_threshold,
            "fps": fps,
            "seed": seed
        }
        
        # Validate inputs
        if not SchemaUtils.validate_control_weights(weights_dict):
            print("❌ Invalid control weights")
            sys.exit(1)
        
        if not SchemaUtils.validate_parameters(parameters):
            print("❌ Invalid parameters")
            sys.exit(1)
        
        # Generate unique run ID
        run_id = SchemaUtils.generate_run_id(prompt_spec.id, weights_dict, parameters)
        
        # Build output path
        if custom_output_path:
            output_path = custom_output_path
        else:
            output_path = f"outputs/{prompt_spec.name}_{run_id}"
        
        # Create RunSpec
        from datetime import datetime
        timestamp = datetime.now().isoformat() + "Z"
        run_spec = RunSpec(
            id=run_id,
            prompt_id=prompt_spec.id,
            control_weights=weights_dict,
            parameters=parameters,
            timestamp=timestamp,
            execution_status="pending",
            output_path=output_path
        )
        
        # Save to file
        from cosmos_workflow.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        local_config = config_manager.get_local_config()
        
        # Create date-based directory structure
        from cosmos_workflow.prompts.schemas import DirectoryManager
        dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)
        dir_manager.ensure_directories_exist()
        
        file_path = dir_manager.get_run_file_path(prompt_spec.name, timestamp, run_id)
        run_spec.save(file_path)
        
        print(f"\n✅ Created RunSpec: {run_id}")
        print(f"   Saved to: {file_path}")
        print(f"   Prompt: {prompt_spec.id}")
        print(f"   Control Weights: {weights_dict}")
        print(f"   Output: {output_path}")
        print(f"\n🚀 To run this specification:")
        print(f"   python -m cosmos_workflow.main run {file_path}")
        
    except Exception as e:
        print(f"\n❌ Failed to create RunSpec: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Cosmos-Transfer1 Python Workflow CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete workflow
  python -m cosmos_workflow.main run prompt.json
  
  # Run with custom videos subdirectory
  python -m cosmos_workflow.main run prompt.json --videos-subdir custom_videos
  
  # Run without upscaling
  python -m cosmos_workflow.main run prompt.json --no-upscale
  
  # Run with custom upscale weight
  python -m cosmos_workflow.main run prompt.json --upscale-weight 0.7
  
  # Run only inference
  python -m cosmos_workflow.main inference prompt.json
  
  # Run only upscaling
  python -m cosmos_workflow.main upscale prompt.json --upscale-weight 0.6
  
  # Check remote status
  python -m cosmos_workflow.main status
  
  # Use multiple GPUs
  python -m cosmos_workflow.main run prompt.json --num-gpu 2 --cuda-devices "0,1"
  
  # Create new PromptSpec
  python -m cosmos_workflow.main create-spec "cyberpunk_city" "Cyberpunk city at night with neon lights"
  
  # Create new RunSpec
  python -m cosmos_workflow.main create-run prompt_spec.json --weights 0.3 0.4 0.2 0.1
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command (full cycle)
    run_parser = subparsers.add_parser('run', help='Run complete workflow')
    run_parser.add_argument('prompt_file', help='Path to prompt JSON file')
    run_parser.add_argument('--videos-subdir', help='Custom videos subdirectory override')
    run_parser.add_argument('--no-upscale', action='store_true', help='Skip upscaling step')
    run_parser.add_argument('--upscale-weight', type=float, default=0.5, help='Upscaling control weight')
    run_parser.add_argument('--num-gpu', type=int, default=1, help='Number of GPUs to use')
    run_parser.add_argument('--cuda-devices', default='0', help='CUDA device IDs to use')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Inference command
    inference_parser = subparsers.add_parser('inference', help='Run only inference')
    inference_parser.add_argument('prompt_file', help='Path to prompt JSON file')
    inference_parser.add_argument('--videos-subdir', help='Custom videos subdirectory override')
    inference_parser.add_argument('--num-gpu', type=int, default=1, help='Number of GPUs to use')
    inference_parser.add_argument('--cuda-devices', default='0', help='CUDA device IDs to use')
    inference_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Upscale command
    upscale_parser = subparsers.add_parser('upscale', help='Run only upscaling')
    upscale_parser.add_argument('prompt_file', help='Path to prompt JSON file')
    upscale_parser.add_argument('--upscale-weight', type=float, default=0.5, help='Upscaling control weight')
    upscale_parser.add_argument('--num-gpu', type=int, default=1, help='Number of GPUs to use')
    upscale_parser.add_argument('--cuda-devices', default='0', help='CUDA device IDs to use')
    upscale_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check remote instance status')
    status_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Create PromptSpec command
    create_spec_parser = subparsers.add_parser('create-spec', help='Create a new PromptSpec (new format)')
    create_spec_parser.add_argument('name', help='Name for the prompt')
    create_spec_parser.add_argument('prompt_text', help='The text prompt for generation')
    create_spec_parser.add_argument('--negative-prompt', default='bad quality, blurry, low resolution, cartoonish',
                                  help='Negative prompt for improved quality')
    create_spec_parser.add_argument('--video-path', help='Custom video path override')
    create_spec_parser.add_argument('--control-inputs', nargs='*', metavar=('MODALITY', 'PATH'),
                                  help='Control input file paths (e.g., depth inputs/videos/name/depth.mp4)')
    create_spec_parser.add_argument('--upsampled', action='store_true', help='Mark as upsampled prompt')
    create_spec_parser.add_argument('--parent-prompt', help='Original prompt text if upsampled')
    create_spec_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Create RunSpec command
    create_run_parser = subparsers.add_parser('create-run', help='Create a new RunSpec')
    create_run_parser.add_argument('prompt_spec_path', help='Path to PromptSpec JSON file')
    create_run_parser.add_argument('--weights', nargs=4, type=float, metavar=('VIS', 'EDGE', 'DEPTH', 'SEG'),
                                  help='Control weights (default: 0.25 each)')
    create_run_parser.add_argument('--num-steps', type=int, default=35, help='Number of inference steps')
    create_run_parser.add_argument('--guidance', type=float, default=7.0, help='Guidance scale')
    create_run_parser.add_argument('--sigma-max', type=float, default=70.0, help='Sigma max value')
    create_run_parser.add_argument('--blur-strength', choices=['very_low', 'low', 'medium', 'high', 'very_high'],
                                  default='medium', help='Blur strength for vis controlnet')
    create_run_parser.add_argument('--canny-threshold', choices=['very_low', 'low', 'medium', 'high', 'very_high'],
                                  default='medium', help='Canny threshold for edge controlnet')
    create_run_parser.add_argument('--fps', type=int, default=24, help='Output FPS')
    create_run_parser.add_argument('--seed', type=int, default=1, help='Random seed')
    create_run_parser.add_argument('--output-path', help='Custom output path')
    create_run_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'run':
            prompt_file = validate_prompt_file(args.prompt_file)
            run_full_cycle(
                prompt_file=prompt_file,
                videos_subdir=args.videos_subdir,
                no_upscale=args.no_upscale,
                upscale_weight=args.upscale_weight,
                num_gpu=args.num_gpu,
                cuda_devices=args.cuda_devices,
                verbose=args.verbose
            )
        
        elif args.command == 'inference':
            prompt_file = validate_prompt_file(args.prompt_file)
            run_inference_only(
                prompt_file=prompt_file,
                videos_subdir=args.videos_subdir,
                num_gpu=args.num_gpu,
                cuda_devices=args.cuda_devices,
                verbose=args.verbose
            )
        
        elif args.command == 'upscale':
            prompt_file = validate_prompt_file(args.prompt_file)
            run_upscaling_only(
                prompt_file=prompt_file,
                upscale_weight=args.upscale_weight,
                num_gpu=args.num_gpu,
                cuda_devices=args.cuda_devices,
                verbose=args.verbose
            )
        
        elif args.command == 'status':
            check_status(args.verbose)
        
        elif args.command == 'create-spec':
            create_prompt_spec(
                name=args.name,
                prompt_text=args.prompt_text,
                negative_prompt=args.negative_prompt,
                input_video_path=args.video_path,
                control_inputs=args.control_inputs,
                is_upsampled=args.upsampled,
                parent_prompt_text=args.parent_prompt,
                verbose=args.verbose
            )
        
        elif args.command == 'create-run':
            create_run_spec(
                prompt_spec_path=args.prompt_spec_path,
                control_weights=args.weights,
                num_steps=args.num_steps,
                guidance=args.guidance,
                sigma_max=args.sigma_max,
                blur_strength=args.blur_strength,
                canny_threshold=args.canny_threshold,
                fps=args.fps,
                seed=args.seed,
                custom_output_path=args.output_path,
                verbose=args.verbose
            )
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
