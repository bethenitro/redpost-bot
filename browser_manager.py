#!/usr/bin/env python3
"""
Browser session management for Reddit Poster Bot
"""

import asyncio
import random
import logging
from datetime import datetime
from typing import Any, Optional

from camoufox import AsyncCamoufox
from models import AccountData
from selector_config import selector_config

logger = logging.getLogger(__name__)


class BrowserManager:
    """Handles browser session creation and management"""
    
    def __init__(self, data_manager, proxy_manager, config: dict):
        self.data_manager = data_manager
        self.proxy_manager = proxy_manager
        self.config = config
        self.selector_config = selector_config
        
        # Stealth settings
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.random_sites = [
            "https://www.google.com",
            "https://www.youtube.com",
            "https://www.wikipedia.org",
            "https://www.github.com",
            "https://www.stackoverflow.com"
        ]

    async def add_account(self, username: str, use_proxy: bool = None, preferred_proxy: str = None, login_callback=None) -> bool:
        """Add a new account by logging in and storing cookies"""
        try:
            logger.info(f"Adding account: {username}")
            
            # Browser configuration - simplified to avoid potential issues
            browser_config = {
                "headless": False,
                "humanize": True,
                "geoip": True
            }
            
            # Add proxy if requested or enabled by default
            proxy_used = None
            if use_proxy or (use_proxy is None and self.config.get("use_proxies", False)):
                proxy = None
                # Use preferred proxy if specified
                if preferred_proxy and preferred_proxy in self.data_manager.proxies:
                    proxy = self.data_manager.proxies[preferred_proxy]
                    if proxy.status != "active":
                        logger.warning(f"Preferred proxy {preferred_proxy} is not active, using random proxy")
                        proxy = self.proxy_manager.get_random_proxy()
                else:
                    proxy = self.proxy_manager.get_random_proxy()
                
                if proxy:
                    browser_config["proxy"] = self.proxy_manager.format_proxy_for_camoufox(proxy)
                    proxy_used = proxy.url
                    logger.info(f"Using proxy {proxy.url} for account setup")
            
            # Use proper async context manager
            logger.debug(f"Creating browser with config: {browser_config}")
            async with AsyncCamoufox(**browser_config) as browser:
                logger.info("Browser context entered successfully")
                
                # Create a new page
                logger.debug("Creating new page...")
                page = await browser.new_page()
                logger.debug("New page created successfully")
                
                # Go to Reddit login
                logger.debug("Navigating to Reddit login page...")
                await page.goto("https://www.reddit.com/login/", wait_until="networkidle")
                logger.debug("Navigation completed")
                await self._random_delay(2, 5)
                
                # Wait for user to login manually
                if login_callback:
                    await login_callback(f"Please login to Reddit account: {username}")
                else:
                    print(f"Please login to Reddit account: {username}")
                    print("Press Enter after successful login...")
                    input()
                
                # Get cookies after login
                logger.debug("Getting cookies from browser...")
                cookies = await page.context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                logger.debug(f"Retrieved {len(cookie_dict)} cookies")
                
                # Trust manual login - if user pressed Enter and we have cookies, consider it successful
                logger.debug("Trusting manual login process...")
                if len(cookie_dict) > 0:
                    logger.info(f"Successfully logged in as {username} (manual login confirmed with {len(cookie_dict)} cookies)")
                else:
                    logger.error(f"Login failed for {username} - no cookies retrieved")
                    return False
                
                # Store account data
                logger.debug("Creating AccountData object...")
                # Set a placeholder user agent since Camoufox handles user agent automatically
                default_user_agent = "Mozilla/5.0 (managed-by-camoufox)"
                account = AccountData(
                    username=username,
                    cookies=cookie_dict,
                    user_agent=default_user_agent,
                    last_used=datetime.now(),
                    post_count=0,
                    status="active",
                    preferred_proxy=proxy_used
                )
                
                logger.debug("Storing account in accounts dictionary...")
                self.data_manager.accounts[username] = account
                logger.debug("Saving accounts to file...")
                self.data_manager.save_accounts()
                
                logger.info(f"Account {username} added successfully")
                return True
                
        except Exception as e:
            import traceback
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(f"Error adding account {username}: {e}")
            logger.error(f"Exception type: {exc_type.__name__}")
            logger.error(f"Exception occurred at line {exc_traceback.tb_lineno}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False

    async def create_browser_session(self, account_name: str, use_proxy: bool = None, headless: bool = None):
        """Create a browser session with account cookies and proxy"""
        if not account_name or account_name.strip() == "":
            raise ValueError("Account name cannot be empty")
            
        account_name = account_name.strip()
        if account_name not in self.data_manager.accounts:
            available_accounts = list(self.data_manager.accounts.keys())
            raise ValueError(f"Account '{account_name}' not found. Available accounts: {available_accounts}")
        
        account = self.data_manager.accounts[account_name]
        if account is None:
            raise ValueError(f"Account {account_name} is None")
            
        # Ensure account has required attributes
        if not hasattr(account, 'cookies') or account.cookies is None:
            raise ValueError(f"Account {account_name} has no cookies - please login first")
        
        logger.info(f"Creating browser session for account: {account_name}")
        
        # Browser configuration
        browser_config = {
            "headless": headless if headless is not None else self.config.get("headless", True),
            "humanize": True,
            "geoip": True,
            "locale": "en-US"  # Force English language
        }
        
        # Add proxy if enabled and requested
        proxy_enabled = use_proxy if use_proxy is not None else self.config.get("use_proxies", False)
        if proxy_enabled:
            proxy = None
            
            # Try to use account's preferred proxy first
            if account.preferred_proxy and account.preferred_proxy in self.data_manager.proxies:
                preferred_proxy = self.data_manager.proxies[account.preferred_proxy]
                if preferred_proxy.status == "active":
                    proxy = preferred_proxy
            
            # If no preferred proxy or it's not working, get a random one
            if not proxy:
                proxy = self.proxy_manager.get_random_proxy()
            
            if proxy:
                browser_config["proxy"] = self.proxy_manager.format_proxy_for_camoufox(proxy)
                logger.info(f"Using proxy {proxy.url} for account {account_name}")
            else:
                logger.warning(f"No working proxies available for account {account_name}")
        else:
            logger.info(f"Proxy usage is disabled for account {account_name}")
        
        return AsyncCamoufox(**browser_config), account

    async def _random_delay(self, min_seconds: float = None, max_seconds: float = None, delay_type: str = "random"):
        """Add random delay to mimic human behavior with fluctuations"""
        if min_seconds is None or max_seconds is None:
            min_seconds, max_seconds = self.selector_config.get_delay(delay_type)
        
        # Add random fluctuations to make timing less predictable
        fluctuation = random.uniform(0.8, 1.2)  # ±20% fluctuation
        min_seconds *= fluctuation
        max_seconds *= fluctuation
        
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Random delay: {delay:.2f} seconds (type: {delay_type}, fluctuation: {fluctuation:.2f})")
        await asyncio.sleep(delay)

    async def _visit_random_pages(self, page: Any):
        """Visit random pages before posting to avoid detection"""
        if random.random() < 0.7:  # 70% chance to visit random pages
            site = random.choice(self.random_sites)
            try:
                logger.debug(f"Visiting random site: {site}")
                await page.goto(site, wait_until="domcontentloaded", timeout=30000)
                await self._random_delay(2, 5)
                await self._random_scroll(page)
                logger.debug(f"Successfully visited {site}")
            except Exception as e:
                logger.debug(f"Failed to visit random site {site}: {e}")
                pass  # Ignore errors for random page visits

    async def _random_scroll(self, page: Any):
        """Perform random scrolling to mimic human behavior"""
        scroll_count = random.randint(1, 3)
        for _ in range(scroll_count):
            await page.evaluate(f"window.scrollBy(0, {random.randint(100, 500)})")
            await self._random_delay(delay_type="scroll")