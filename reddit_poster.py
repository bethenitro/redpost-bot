#!/usr/bin/env python3
"""
Reddit Posting Bot with Stealth Measures
Supports multiple accounts, scheduling, and various post types
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from models import PostData, ProxyData, AccountData
from data_manager import DataManager
from proxy_manager import ProxyManager
from browser_manager import BrowserManager
from reddit_actions import RedditActions
from scheduler import PostScheduler
from selector_config import selector_config

# Configure logging with file and line information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
    handlers=[
        logging.FileHandler('reddit_poster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedditPoster:
    """Main Reddit posting bot with stealth capabilities"""
    
    def __init__(self, data_dir: str = "data"):
        # Initialize data manager
        self.data_manager = DataManager(data_dir)
        
        # Initialize component managers
        self.proxy_manager = ProxyManager(self.data_manager, self.data_manager.config)
        self.browser_manager = BrowserManager(self.data_manager, self.proxy_manager, self.data_manager.config)
        self.reddit_actions = RedditActions(self.data_manager.config)
        self.scheduler = PostScheduler(self.data_manager, self, self.data_manager.config)
        
        # Load selector configuration
        self.selector_config = selector_config

    # Delegate data management methods to data_manager
    @property
    def accounts(self):
        return self.data_manager.accounts
    
    @property
    def posts(self):
        return self.data_manager.posts
    
    @property
    def proxies(self):
        return self.data_manager.proxies
    
    @property
    def config(self):
        return self.data_manager.config

    # Delegate proxy management methods to proxy_manager
    def add_proxy(self, host: str, port: int, username: str = None, password: str = None, 
                  rotation_url: str = None, protocol: str = "http") -> str:
        return self.proxy_manager.add_proxy(host, port, username, password, rotation_url, protocol)

    def remove_proxy(self, proxy_id: str):
        return self.proxy_manager.remove_proxy(proxy_id)

    def rotate_proxy_ip(self, proxy_id: str) -> bool:
        return self.proxy_manager.rotate_proxy_ip(proxy_id)

    def get_working_proxies(self) -> List[str]:
        return self.proxy_manager.get_working_proxies()

    def get_random_proxy(self) -> Optional[ProxyData]:
        return self.proxy_manager.get_random_proxy()

    # Delegate proxy testing methods to proxy_manager
    async def test_proxy(self, proxy: ProxyData) -> bool:
        return await self.proxy_manager.test_proxy(proxy)

    async def test_all_proxies(self):
        return await self.proxy_manager.test_all_proxies()

    async def test_all_proxies_with_progress(self, progress_callback=None):
        return await self.proxy_manager.test_all_proxies_with_progress(progress_callback)

    # Delegate account management methods to browser_manager
    async def add_account(self, username: str, use_proxy: bool = None, preferred_proxy: str = None, login_callback=None) -> bool:
        return await self.browser_manager.add_account(username, use_proxy, preferred_proxy, login_callback)

    async def create_browser_session(self, account_name: str, use_proxy: bool = None, headless: bool = None):
        return await self.browser_manager.create_browser_session(account_name, use_proxy, headless)

    # Delegate helper methods to reddit_actions
    async def _random_delay(self, min_seconds: float = None, max_seconds: float = None, delay_type: str = "random"):
        return await self.reddit_actions._random_delay(min_seconds, max_seconds, delay_type)

    async def _human_type(self, page, selector: str, text: str):
        return await self.reddit_actions._human_type(page, selector, text)

    # Delegate Reddit action methods to reddit_actions
    async def _upload_image_file(self, page, image_path: str) -> bool:
        return await self.reddit_actions._upload_image_file(page, image_path)

    async def _visit_random_pages(self, page):
        return await self.browser_manager._visit_random_pages(page)

    async def _mark_post_nsfw(self, page) -> bool:
        return await self.reddit_actions._mark_post_nsfw(page)

    # Initialize the core poster
    def _get_poster_core(self):
        if not hasattr(self, '_poster_core'):
            from reddit_poster_core import RedditPosterCore
            self._poster_core = RedditPosterCore(
                self.browser_manager, 
                self.reddit_actions, 
                self.data_manager, 
                self.selector_config
            )
        return self._poster_core

    async def post_to_reddit(self, post_data: PostData) -> bool:
        """Post content to Reddit with stealth measures"""
        return await self._get_poster_core().post_to_reddit(post_data)

    def _save_posts(self):
        """Save posts data to file"""
        self.data_manager.save_posts()

    def _save_accounts(self):
        """Save accounts data to file"""
        self.data_manager.save_accounts()

    def _save_proxies(self):
        """Save proxies data to file"""
        self.data_manager.save_proxies()

    def add_post(self, subreddit: str, title: str, content: str = "", 
                 post_type: str = "text", nsfw: bool = False, 
                 account_name: str = "", scheduled_time: Optional[datetime] = None,
                 use_proxy: bool = True, headless: bool = True):
        """Add a new post to the queue"""
        post = PostData(
            subreddit=subreddit,
            title=title,
            content=content,
            post_type=post_type,
            nsfw=nsfw,
            account_name=account_name,
            scheduled_time=scheduled_time,
            use_proxy=use_proxy,
            headless=headless
        )
        
        self.posts.append(post)
        self.data_manager.save_posts()
        logger.info(f"Added post: {title} to r/{subreddit}")

    async def post_now(self, subreddit: str, title: str, content: str = "", 
                      post_type: str = "text", nsfw: bool = False, 
                      account_name: str = "", headless: bool = True, 
                      use_proxy: bool = True) -> bool:
        """Post immediately without adding to queue"""
        post = PostData(
            subreddit=subreddit,
            title=title,
            content=content,
            post_type=post_type,
            nsfw=nsfw,
            account_name=account_name,
            scheduled_time=None,
            use_proxy=use_proxy,
            headless=headless
        )
        
        logger.info(f"Posting immediately: {title} to r/{subreddit} (headless: {headless})")
        
        success = await self.post_to_reddit(post)
        if success:
            logger.info(f"Successfully posted: {title}")
        else:
            logger.error(f"Failed to post: {title}")
        return success

    # Delegate scheduling methods to scheduler
    def get_pending_posts(self) -> List[PostData]:
        return self.scheduler.get_pending_posts()

    def get_account_names(self) -> List[str]:
        return list(self.accounts.keys())
    
    def reschedule_pending_posts_to_future(self, minutes_from_now: int = 5):
        return self.scheduler.reschedule_pending_posts_to_future(minutes_from_now)

    # Delegate proxy list methods to proxy_manager
    def get_proxy_list(self) -> List[Dict]:
        return self.proxy_manager.get_proxy_list()

    def import_proxies_from_file(self, file_path: str) -> int:
        return self.proxy_manager.import_proxies_from_file(file_path)

    # Delegate scheduler to scheduler
    async def run_scheduler(self):
        return await self.scheduler.run_scheduler()

if __name__ == "__main__":
    poster = RedditPoster()
    
    # Example usage
    print("Reddit Poster Bot")
    print("1. Add account")
    print("2. Add post")
    print("3. Start scheduler")
    
    choice = input("Enter choice: ")
    
    if choice == "1":
        username = input("Enter username: ")
        asyncio.run(poster.add_account(username))
    elif choice == "2":
        subreddit = input("Enter subreddit: ")
        title = input("Enter title: ")
        content = input("Enter content (or image path): ")
        post_type = input("Enter post type (text/image): ") or "text"
        nsfw = input("NSFW? (y/n): ").lower() == 'y'
        account = input("Enter account name: ")
        
        poster.add_post(subreddit, title, content, post_type, nsfw, account)
        print("Post added to queue")
    elif choice == "3":
        asyncio.run(poster.run_scheduler())