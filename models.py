#!/usr/bin/env python3
"""
Data models for Reddit Poster Bot
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class PostData:
    """Data structure for a Reddit post"""
    subreddit: str
    title: str
    content: str = ""  # Text content or image path(s) - for images, can be semicolon-separated paths
    post_type: str = "text"  # "text" or "image"
    nsfw: bool = False
    account_name: str = ""
    scheduled_time: Optional[datetime] = None
    status: str = "pending"  # pending, posted, failed
    error_message: str = ""
    use_proxy: bool = True  # Whether to use proxy for this post
    headless: bool = True  # Whether to run browser in headless mode
    
    @property
    def image_paths(self) -> List[str]:
        """Get list of image paths for image posts"""
        if self.post_type == "image" and self.content:
            return [path.strip() for path in self.content.split(';') if path.strip()]
        return []
    
    @image_paths.setter
    def image_paths(self, paths: List[str]):
        """Set image paths for image posts"""
        if self.post_type == "image":
            self.content = ';'.join(paths)


@dataclass
class ProxyData:
    """Data structure for proxy configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    rotation_url: Optional[str] = None  # URL to rotate IP
    protocol: str = "http"  # http, https, socks4, socks5
    status: str = "active"  # active, failed, banned
    last_used: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    location: Optional[str] = None  # City, Country format
    
    @property
    def url(self) -> str:
        """Get the proxy URL"""
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class AccountData:
    """Data structure for Reddit account"""
    username: str
    cookies: Dict
    user_agent: str
    last_used: Optional[datetime] = None
    post_count: int = 0
    status: str = "active"  # active, banned, suspended
    preferred_proxy: Optional[str] = None  # proxy identifier