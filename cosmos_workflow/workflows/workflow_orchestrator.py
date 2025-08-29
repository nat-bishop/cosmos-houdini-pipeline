#!/usr/bin/env python3
"""
Workflow orchestrator for Cosmos-Transfer1.
Coordinates all services to run complete workflows with proper error handling and logging.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.execution.docker_executor import DockerExecutor
import logging

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates complete Cosmos-Transfer1 workflows."""
    
    def __init__(self, config_file: str = "scripts/config.sh"):
        self.config_manager = ConfigManager(config_file)
        self.ssh_manager: Optional[SSHManager] = None
        self.file_transfer: Optional[FileTransferService] = None
        self.docker_executor: Optional[DockerExecutor] = None
    
    def _initialize_services(self):
        """Initialize all workflow services."""
        if not self.ssh_manager:
            remote_config = self.config_manager.get_remote_config()
            ssh_options = self.config_manager.get_ssh_options()
            
            self.ssh_manager = SSHManager(ssh_options)
            self.file_transfer = FileTransferService(
                self.ssh_manager, 
                remote_config.remote_dir
            )
            self.docker_executor = DockerExecutor(
                self.ssh_manager,
                remote_config.remote_dir,
                remote_config.docker_image
            )
    
    def run_full_cycle(
        self, 
        prompt_file: Path, 
        videos_subdir: Optional[str] = None,
        no_upscale: bool = False,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0"
    ) -> Dict[str, Any]:
        """
        Run complete workflow: upload → inference → upscaling → download.
        
        Args:
            prompt_file: Path to prompt JSON file
            videos_subdir: Optional override for video directory
            no_upscale: Skip upscaling step
            upscale_weight: Control weight for upscaling
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
            
        Returns:
            Workflow execution results
        """
        self._initialize_services()
        
        start_time = datetime.now()
        prompt_name = prompt_file.stem
        
        logger.info(f"Starting full cycle workflow for {prompt_name}")
        print(f"🚀 Starting full cycle workflow for {prompt_name}")
        
        try:
            with self.ssh_manager:
                # Step 1: Upload files
                print("\n📤 Step 1: Uploading prompt and videos...")
                
                # Determine video directories to upload
                if videos_subdir:
                    video_dirs = [Path(f"inputs/videos/{videos_subdir}")]
                else:
                    # Extract from prompt filename
                    prompt_name = prompt_file.stem
                    video_dirs = [Path(f"inputs/videos/{prompt_name}")]
                
                self.file_transfer.upload_prompt_and_videos(prompt_file, video_dirs)
                
                # Step 2: Run inference
                print(f"\n🎬 Step 2: Running inference with {num_gpu} GPU(s)...")
                self.docker_executor.run_inference(
                    prompt_file, 
                    num_gpu, 
                    cuda_devices
                )
                
                # Step 3: Run upscaling (if enabled)
                if not no_upscale:
                    print(f"\n🔍 Step 3: Running 4K upscaling with weight {upscale_weight}...")
                    self.docker_executor.run_upscaling(
                        prompt_file, 
                        upscale_weight, 
                        num_gpu, 
                        cuda_devices
                    )
                else:
                    print("\n⏭️  Step 3: Skipping upscaling (--no-upscale flag used)")
                
                # Step 4: Download results
                print("\n📥 Step 4: Downloading results...")
                self.file_transfer.download_results(prompt_file)
                
                # Step 5: Log workflow completion
                self._log_workflow_completion(
                    prompt_file, 
                    not no_upscale, 
                    upscale_weight,
                    num_gpu
                )
                
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"\n✅ Full cycle workflow completed successfully!")
                print(f"⏱️  Total duration: {duration}")
                
                return {
                    "status": "success",
                    "prompt_name": prompt_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                    "upscaled": not no_upscale,
                    "upscale_weight": upscale_weight,
                    "num_gpu": num_gpu,
                    "cuda_devices": cuda_devices
                }
                
        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time
            
            error_result = {
                "status": "failed",
                "prompt_name": prompt_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "error": str(e)
            }
            
            logger.error(f"Workflow failed: {e}")
            print(f"\n❌ Workflow failed: {e}")
            
            # Log failed workflow
            self._log_workflow_failure(prompt_file, str(e), duration)
            
            raise RuntimeError(f"Workflow failed: {e}") from e
    
    def run_inference_only(
        self, 
        prompt_file: Path,
        videos_subdir: Optional[str] = None,
        num_gpu: int = 1,
        cuda_devices: str = "0"
    ) -> Dict[str, Any]:
        """Run only inference without upscaling."""
        self._initialize_services()
        
        start_time = datetime.now()
        prompt_name = prompt_file.stem
        
        logger.info(f"Running inference only for {prompt_name}")
        print(f"🎬 Running inference only for {prompt_name}")
        
        try:
            with self.ssh_manager:
                # Upload files
                print("\n📤 Uploading prompt and videos...")
                
                # Determine video directories to upload
                if videos_subdir:
                    video_dirs = [Path(f"inputs/videos/{videos_subdir}")]
                else:
                    # Extract from prompt filename
                    prompt_name = prompt_file.stem
                    video_dirs = [Path(f"inputs/videos/{prompt_name}")]
                
                self.file_transfer.upload_prompt_and_videos(prompt_file, video_dirs)
                
                # Run inference
                print(f"\n🎬 Running inference with {num_gpu} GPU(s)...")
                self.docker_executor.run_inference(prompt_file, num_gpu, cuda_devices)
                
                # Download results
                print("\n📥 Downloading results...")
                self.file_transfer.download_results(prompt_file)
                
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"\n✅ Inference completed successfully in {duration}")
                
                return {
                    "status": "success",
                    "prompt_name": prompt_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                    "num_gpu": num_gpu,
                    "cuda_devices": cuda_devices
                }
                
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise RuntimeError(f"Inference failed: {e}") from e
    
    def run_upscaling_only(
        self, 
        prompt_file: Path,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0"
    ) -> Dict[str, Any]:
        """Run only upscaling on existing inference output."""
        self._initialize_services()
        
        start_time = datetime.now()
        prompt_name = prompt_file.stem
        
        logger.info(f"Running upscaling only for {prompt_name}")
        print(f"🔍 Running upscaling only for {prompt_name}")
        
        try:
            with self.ssh_manager:
                # Run upscaling
                print(f"\n🔍 Running 4K upscaling with weight {upscale_weight}...")
                self.docker_executor.run_upscaling(
                    prompt_file, 
                    upscale_weight, 
                    num_gpu, 
                    cuda_devices
                )
                
                # Download results
                print("\n📥 Downloading upscaled results...")
                self.file_transfer.download_results(prompt_file)
                
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"\n✅ Upscaling completed successfully in {duration}")
                
                return {
                    "status": "success",
                    "prompt_name": prompt_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                    "upscale_weight": upscale_weight,
                    "num_gpu": num_gpu,
                    "cuda_devices": cuda_devices
                }
                
        except Exception as e:
            logger.error(f"Upscaling failed: {e}")
            raise RuntimeError(f"Upscaling failed: {e}") from e
    
    def check_remote_status(self) -> Dict[str, Any]:
        """Check remote instance and Docker status."""
        self._initialize_services()
        
        try:
            with self.ssh_manager:
                # Check SSH connection
                ssh_status = "connected"
                
                # Check Docker status
                docker_status = self.docker_executor.get_docker_status()
                
                # Check remote directory
                remote_config = self.config_manager.get_remote_config()
                remote_dir_exists = self.file_transfer.file_exists_remote(remote_config.remote_dir)
                
                return {
                    "ssh_status": ssh_status,
                    "docker_status": docker_status,
                    "remote_directory_exists": remote_dir_exists,
                    "remote_directory": remote_config.remote_dir
                }
                
        except Exception as e:
            return {
                "ssh_status": "failed",
                "error": str(e)
            }
    
    def _log_workflow_completion(
        self, 
        prompt_file: Path, 
        upscaled: bool, 
        upscale_weight: float,
        num_gpu: int
    ) -> None:
        """Log successful workflow completion."""
        local_config = self.config_manager.get_local_config()
        remote_config = self.config_manager.get_remote_config()
        
        # Ensure notes directory exists
        local_config.notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt_name = prompt_file.stem
        
        log_entry = (
            f"{timestamp} | prompt={prompt_file.name} | "
            f"outputs=outputs/{prompt_name} | host={remote_config.host} | "
            f"num_gpu={num_gpu} | upscaled={upscaled} | "
            f"upscale_weight={upscale_weight}\n"
        )
        
        # Append to run history
        run_history_file = local_config.notes_dir / "run_history.log"
        with open(run_history_file, 'a') as f:
            f.write(log_entry)
        
        logger.info(f"Workflow logged to {run_history_file}")
    
    def _log_workflow_failure(
        self, 
        prompt_file: Path, 
        error: str, 
        duration
    ) -> None:
        """Log failed workflow."""
        local_config = self.config_manager.get_local_config()
        
        # Ensure notes directory exists
        local_config.notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Create failure log entry
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt_name = prompt_file.stem
        
        log_entry = (
            f"{timestamp} | FAILED | prompt={prompt_file.name} | "
            f"error={error} | duration={duration}\n"
        )
        
        # Append to run history
        run_history_file = local_config.notes_dir / "run_history.log"
        with open(run_history_file, 'a') as f:
            f.write(log_entry)
        
        logger.info(f"Workflow failure logged to {run_history_file}")
