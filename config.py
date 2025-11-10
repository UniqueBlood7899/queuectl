import json
from pathlib import Path
from typing import Any


class Config:
    """Configuration management"""
    
    DEFAULT_CONFIG = {
        'max_retries': 3,
        'backoff_base': 2,
        'worker_poll_interval': 1,
    }
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = str(Path.home() / '.queuectl')
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / 'config.json'
        
        # Initialize config file if it doesn't exist
        if not self.config_file.exists():
            self._write_config(self.DEFAULT_CONFIG)
    
    def _read_config(self) -> dict:
        """Read configuration from file"""
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def _write_config(self, config: dict):
        """Write configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get(self, key: str) -> Any:
        """Get a configuration value"""
        config = self._read_config()
        return config.get(key, self.DEFAULT_CONFIG.get(key))
    
    def set(self, key: str, value: Any):
        """Set a configuration value"""
        config = self._read_config()
        config[key] = value
        self._write_config(config)
    
    def get_all(self) -> dict:
        """Get all configuration"""
        return self._read_config()