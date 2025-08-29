#!/usr/bin/env python3
"""
Configuration management for Cosmos-Transfer1 workflows.
Loads and validates settings from config.sh and environment variables.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RemoteConfig:
    """Remote instance configuration."""
    user: str
    host: str
    port: int
    ssh_key: Path
    remote_dir: str
    docker_image: str


@dataclass
class LocalConfig:
    """Local paths configuration."""
    prompts_dir: Path
    videos_dir: Path
    outputs_dir: Path
    notes_dir: Path


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_file: str = "scripts/config.sh"):
        self.config_file = Path(config_file)
        self.remote_config: Optional[RemoteConfig] = None
        self.local_config: Optional[LocalConfig] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.sh file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        config_vars = {}
        
        # Read config.sh and parse variables
        with open(self.config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove inline comments
                    if '#' in value:
                        value = value.split('#')[0].strip()
                    
                    # Remove quotes (both single and double)
                    value = value.strip('"\'')
                    
                    # Handle variable expansion
                    if '$HOME' in value:
                        value = value.replace('$HOME', str(Path.home()))
                    
                    # Handle shell-style default values: ${VAR:-default}
                    import re
                    var_pattern = r'\$\{([^:]+):-([^}]+)\}'
                    for match in re.finditer(var_pattern, value):
                        var_name, default_val = match.groups()
                        env_value = os.getenv(var_name, default_val)
                        value = value.replace(match.group(0), env_value)
                    
                    # Handle simple variable substitution: ${VAR}
                    simple_pattern = r'\$\{([^}]+)\}'
                    for match in re.finditer(simple_pattern, value):
                        var_name = match.group(1)
                        env_value = os.getenv(var_name, '')
                        value = value.replace(match.group(0), env_value)
                    
                    config_vars[key] = value
        
        # Build remote configuration
        self.remote_config = RemoteConfig(
            user=config_vars.get('REMOTE_USER', 'ubuntu'),
            host=config_vars.get('REMOTE_HOST', ''),
            port=int(config_vars.get('REMOTE_PORT', '22')),
            ssh_key=Path(config_vars.get('SSH_KEY', '')),
            remote_dir=config_vars.get('REMOTE_DIR', ''),
            docker_image=config_vars.get('DOCKER_IMAGE', '')
        )
        
        # Build local configuration
        self.local_config = LocalConfig(
            prompts_dir=Path(config_vars.get('LOCAL_PROMPTS_DIR', './inputs/prompts')),
            videos_dir=Path(config_vars.get('LOCAL_VIDEOS_DIR', './inputs/videos')),
            outputs_dir=Path(config_vars.get('LOCAL_OUTPUTS_DIR', './outputs')),
            notes_dir=Path(config_vars.get('LOCAL_NOTES_DIR', './notes'))
        )
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values."""
        if not self.remote_config.host:
            raise ValueError("REMOTE_HOST not configured")
        
        if not self.remote_config.ssh_key.exists():
            raise FileNotFoundError(f"SSH key not found: {self.remote_config.ssh_key}")
        
        if not self.remote_config.remote_dir:
            raise ValueError("REMOTE_DIR not configured")
        
        if not self.remote_config.docker_image:
            raise ValueError("DOCKER_IMAGE not configured")
    
    def get_remote_config(self) -> RemoteConfig:
        """Get remote configuration."""
        return self.remote_config
    
    def get_local_config(self) -> LocalConfig:
        """Get local configuration."""
        return self.local_config
    
    def get_ssh_options(self) -> Dict[str, str]:
        """Get SSH connection options."""
        return {
            'hostname': self.remote_config.host,
            'username': self.remote_config.user,
            'key_filename': str(self.remote_config.ssh_key),
            'port': self.remote_config.port
        }
