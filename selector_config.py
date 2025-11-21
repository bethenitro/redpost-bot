#!/usr/bin/env python3
"""
Configuration loader for Reddit bot selectors and settings
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SelectorConfig:
    """Manages selector configuration for Reddit bot"""
    
    def __init__(self, config_file: str = "selectors_config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded selector configuration from {self.config_file}")
                    return config
            else:
                logger.warning(f"Configuration file {self.config_file} not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file is not available"""
        return {
            "reddit_selectors": {
                "title_input": ["textarea[name=\"title\"]"],
                "text_body": ["div[data-testid=\"rtjson-text-editor\"]"],
                "upload_buttons": ["#device-upload-button"],
                "file_inputs": ["input[type=\"file\"]"],
                "submit_buttons": ["button[type=\"submit\"]"],
                "success_indicators": ["img[src*=\"preview\"]"]
            },
            "timeouts": {
                "page_load": 30000,
                "element_wait": 10000,
                "file_chooser_wait": 5000
            },
            "delays": {
                "typing_min": 0.1,
                "typing_max": 0.3,
                "random_min": 1,
                "random_max": 3
            }
        }
    
    def get_selectors(self, selector_type: str) -> List[str]:
        """Get list of selectors for a specific type"""
        try:
            return self.config.get("reddit_selectors", {}).get(selector_type, [])
        except Exception as e:
            logger.error(f"Error getting selectors for {selector_type}: {e}")
            return []
    
    def get_post_type_selectors(self, post_type: str) -> List[str]:
        """Get selectors for specific post type buttons"""
        try:
            post_type_buttons = self.config.get("reddit_selectors", {}).get("post_type_buttons", {})
            return post_type_buttons.get(post_type.lower(), [])
        except Exception as e:
            logger.error(f"Error getting post type selectors for {post_type}: {e}")
            return []
    
    def get_timeout(self, timeout_type: str) -> int:
        """Get timeout value for specific operation"""
        try:
            return self.config.get("timeouts", {}).get(timeout_type, 10000)
        except Exception as e:
            logger.error(f"Error getting timeout for {timeout_type}: {e}")
            return 10000
    
    def get_delay(self, delay_type: str) -> float:
        """Get delay value for specific operation"""
        try:
            delays = self.config.get("delays", {})
            if delay_type.endswith("_min") or delay_type.endswith("_max"):
                return delays.get(delay_type, 1.0)
            else:
                # Return tuple for min/max delays
                min_key = f"{delay_type}_min"
                max_key = f"{delay_type}_max"
                return (delays.get(min_key, 1.0), delays.get(max_key, 3.0))
        except Exception as e:
            logger.error(f"Error getting delay for {delay_type}: {e}")
            return 1.0 if delay_type.endswith("_min") or delay_type.endswith("_max") else (1.0, 3.0)
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        logger.info("Configuration reloaded")

# Global instance
selector_config = SelectorConfig()