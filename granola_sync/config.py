"""
Configuration management for Granola Sync

Handles loading, validation, and access to configuration settings
from granola_config.yaml with environment variable overrides.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class APIConfig:
    """API configuration settings"""
    base_url: str
    endpoints: Dict[str, str]
    request_delay: float
    batch_size: int
    max_retries: int
    timeout: int


@dataclass
class PathConfig:
    """File path configuration settings"""
    credentials: Path
    user_preferences: Path
    last_sync_file: Path
    document_mapping: Path
    obsidian_vault: Path
    log_directory: Path
    backup_directory: Path
    
    def __post_init__(self):
        """Expand user paths and ensure directories exist"""
        for field_name in ['credentials', 'user_preferences', 'last_sync_file', 
                          'document_mapping', 'obsidian_vault', 'log_directory', 'backup_directory']:
            path = getattr(self, field_name)
            if isinstance(path, str):
                expanded_path = Path(path).expanduser().resolve()
                setattr(self, field_name, expanded_path)
        
        # Ensure directories exist (but not files)
        self.obsidian_vault.mkdir(parents=True, exist_ok=True)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.backup_directory.mkdir(parents=True, exist_ok=True)


class GranolaConfig:
    """Main configuration manager for Granola Sync"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config file, defaults to granola_config.yaml in current dir
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._raw_config = self._load_config()
        self._validate_config()
        
        # Parse structured configs
        self.api = APIConfig(**self._raw_config['api'])
        self.paths = PathConfig(**self._raw_config['paths'])
        
        # Direct access to other sections
        self.sync = self._raw_config['sync']
        self.documents = self._raw_config['documents'] 
        self.obsidian = self._raw_config['obsidian']
        self.data = self._raw_config['data']
        self.logging = self._raw_config['logging']
        self.error_handling = self._raw_config['error_handling']
        self.development = self._raw_config['development']
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config_text = f.read()
        
        # Simple environment variable substitution
        config_text = os.path.expandvars(config_text)
        
        try:
            config = yaml.safe_load(config_text)
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def _validate_config(self):
        """Validate required configuration sections and fields"""
        required_sections = ['api', 'paths', 'sync', 'documents', 'obsidian', 'data', 'logging', 'error_handling']
        
        for section in required_sections:
            if section not in self._raw_config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate critical fields
        api_config = self._raw_config['api']
        required_api_fields = ['base_url', 'endpoints', 'request_delay', 'batch_size', 'max_retries', 'timeout']
        for field in required_api_fields:
            if field not in api_config:
                raise ValueError(f"Missing required API configuration field: {field}")
        
        required_endpoints = ['documents', 'document_lists', 'transcript']
        for endpoint in required_endpoints:
            if endpoint not in api_config['endpoints']:
                raise ValueError(f"Missing required API endpoint: {endpoint}")
    
    def get_api_url(self, endpoint_name: str) -> str:
        """Get full API URL for a specific endpoint"""
        if endpoint_name not in self.api.endpoints:
            raise ValueError(f"Unknown API endpoint: {endpoint_name}")
        
        return f"{self.api.base_url}{self.api.endpoints[endpoint_name]}"
    
    def get_safe_filename_pattern(self) -> str:
        """Get regex pattern for safe filename generation"""
        return self.documents['safe_filename_pattern']
    
    def get_frontmatter_fields(self) -> list:
        """Get list of YAML frontmatter fields to include"""
        return self.obsidian['frontmatter_fields']
    
    def should_auto_refresh_mapping(self) -> bool:
        """Check if mapping should be auto-refreshed"""
        return self.data.get('auto_refresh_mapping', True)
    
    def get_mapping_max_age_hours(self) -> int:
        """Get maximum age in hours before mapping refresh"""
        return self.data.get('mapping_max_age_hours', 24)
    
    def is_dry_run(self) -> bool:
        """Check if running in dry-run mode"""
        return self.development.get('dry_run', False)
    
    def should_continue_on_error(self, error_type: str) -> bool:
        """Check if sync should continue on specific error types"""
        field_name = f'continue_on_{error_type}_error'
        return self.error_handling.get(field_name, True)
    
    def reload(self):
        """Reload configuration from file"""
        self.__init__(str(self.config_path))