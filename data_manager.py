#!/usr/bin/env python3
"""
Data persistence manager for Reddit Poster Bot
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import asdict

from models import PostData, ProxyData, AccountData

logger = logging.getLogger(__name__)


class DataManager:
    """Handles data persistence for accounts, posts, proxies, and config"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.accounts_file = self.data_dir / "accounts.json"
        self.posts_file = self.data_dir / "posts.json"
        self.config_file = self.data_dir / "config.json"
        self.proxies_file = self.data_dir / "proxies.json"
        
        self.accounts: Dict[str, AccountData] = {}
        self.posts: List[PostData] = []
        self.proxies: Dict[str, ProxyData] = {}
        self.config = self._load_config()
        
        self._load_accounts()
        self._load_posts()
        self._load_proxies()
        self._migrate_data()

    def _load_config(self) -> Dict:
        """Load configuration settings"""
        default_config = {
            "min_delay_between_posts": 300,  # Account cooldown: 5 minutes between posts from same account
            "max_delay_between_posts": 1800,  # Legacy setting - no longer used for scheduled posts
            "scroll_delay_min": 2,
            "scroll_delay_max": 8,
            "typing_delay_min": 0.1,
            "typing_delay_max": 0.3,
            "page_load_timeout": 30,
            "max_retries": 3,
            "use_proxies": False,
            "proxy_rotation": True,
            "proxy_test_timeout": 10,
            "proxy_max_failures": 3
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        # Save default config
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config

    def _load_accounts(self):
        """Load account data from file"""
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, 'r') as f:
                    data = json.load(f)
                    for username, account_data in data.items():
                        if 'last_used' in account_data and account_data['last_used']:
                            account_data['last_used'] = datetime.fromisoformat(account_data['last_used'])
                        self.accounts[username] = AccountData(**account_data)
            except Exception as e:
                logger.error(f"Error loading accounts: {e}")

    def save_accounts(self):
        """Save account data to file"""
        try:
            data = {}
            for username, account in self.accounts.items():
                account_dict = asdict(account)
                if account_dict['last_used']:
                    account_dict['last_used'] = account_dict['last_used'].isoformat()
                data[username] = account_dict
            
            with open(self.accounts_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving accounts: {e}")

    def _load_posts(self):
        """Load posts data from file"""
        if self.posts_file.exists():
            try:
                with open(self.posts_file, 'r') as f:
                    data = json.load(f)
                    for post_data in data:
                        if 'scheduled_time' in post_data and post_data['scheduled_time']:
                            post_data['scheduled_time'] = datetime.fromisoformat(post_data['scheduled_time'])
                        self.posts.append(PostData(**post_data))
            except Exception as e:
                logger.error(f"Error loading posts: {e}")

    def save_posts(self):
        """Save posts data to file"""
        try:
            data = []
            for post in self.posts:
                post_dict = asdict(post)
                if post_dict['scheduled_time']:
                    post_dict['scheduled_time'] = post_dict['scheduled_time'].isoformat()
                data.append(post_dict)
            
            with open(self.posts_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving posts: {e}")

    def _load_proxies(self):
        """Load proxy data from file"""
        if self.proxies_file.exists():
            try:
                with open(self.proxies_file, 'r') as f:
                    data = json.load(f)
                    for proxy_id, proxy_data in data.items():
                        if 'last_used' in proxy_data and proxy_data['last_used']:
                            proxy_data['last_used'] = datetime.fromisoformat(proxy_data['last_used'])
                        self.proxies[proxy_id] = ProxyData(**proxy_data)
            except Exception as e:
                logger.error(f"Error loading proxies: {e}")

    def save_proxies(self):
        """Save proxy data to file"""
        try:
            data = {}
            for proxy_id, proxy in self.proxies.items():
                proxy_dict = asdict(proxy)
                if proxy_dict['last_used']:
                    proxy_dict['last_used'] = proxy_dict['last_used'].isoformat()
                data[proxy_id] = proxy_dict
            
            with open(self.proxies_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving proxies: {e}")

    def _migrate_data(self):
        """Migrate existing data to support new features"""
        # Migrate posts to include use_proxy and headless fields
        posts_updated = False
        for post in self.posts:
            if not hasattr(post, 'use_proxy'):
                post.use_proxy = True  # Default to using proxy
                posts_updated = True
            if not hasattr(post, 'headless'):
                post.headless = True  # Default to headless mode
                posts_updated = True
        
        if posts_updated:
            self.save_posts()
            logger.info("Migrated posts to include proxy usage and headless mode settings")