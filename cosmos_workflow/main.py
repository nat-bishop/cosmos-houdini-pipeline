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
