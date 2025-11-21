#!/usr/bin/env python3
"""
Proxy management for Reddit Poster Bot
"""

import asyncio
import random
import logging
import requests
import aiohttp
from datetime import datetime
from typing import List, Optional, Dict
import concurrent.futures

from models import ProxyData

logger = logging.getLogger(__name__)


class ProxyManager:
    """Handles proxy operations and testing"""
    
    def __init__(self, data_manager, config: Dict):
        self.data_manager = data_manager
        self.config = config

    def add_proxy(self, host: str, port: int, username: str = None, password: str = None, 
                  rotation_url: str = None, protocol: str = "http") -> str:
        """Add a new proxy"""
        proxy_id = f"{protocol}://{host}:{port}"
        
        proxy = ProxyData(
            host=host,
            port=port,
            username=username,
            password=password,
            rotation_url=rotation_url,
            protocol=protocol,
            status="active"
        )
        
        self.data_manager.proxies[proxy_id] = proxy
        self.data_manager.save_proxies()
        logger.info(f"Added proxy: {proxy_id}")
        return proxy_id

    def remove_proxy(self, proxy_id: str):
        """Remove a proxy"""
        if proxy_id in self.data_manager.proxies:
            del self.data_manager.proxies[proxy_id]
            self.data_manager.save_proxies()
            logger.info(f"Removed proxy: {proxy_id}")

    def rotate_proxy_ip(self, proxy_id: str) -> bool:
        """Rotate IP for a specific proxy using its rotation URL"""
        if proxy_id not in self.data_manager.proxies:
            logger.error(f"Proxy {proxy_id} not found")
            return False
        
        proxy = self.data_manager.proxies[proxy_id]
        if not proxy.rotation_url:
            logger.error(f"Proxy {proxy_id} has no rotation URL")
            return False
        
        try:
            response = requests.get(proxy.rotation_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully rotated IP for proxy {proxy_id}")
                return True
            else:
                logger.error(f"Failed to rotate IP for proxy {proxy_id}: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error rotating IP for proxy {proxy_id}: {e}")
            return False

    def get_working_proxies(self) -> List[str]:
        """Get list of working proxy IDs"""
        return [
            proxy_id for proxy_id, proxy in self.data_manager.proxies.items()
            if proxy.status == "active" and proxy.failure_count < self.config["proxy_max_failures"]
        ]

    def get_random_proxy(self) -> Optional[ProxyData]:
        """Get a random working proxy"""
        working_proxies = self.get_working_proxies()
        if not working_proxies:
            return None
        
        proxy_id = random.choice(working_proxies)
        proxy = self.data_manager.proxies[proxy_id]
        proxy.last_used = datetime.now()
        return proxy

    async def test_proxy(self, proxy: ProxyData) -> bool:
        """Test if a proxy is working"""
        try:
            # For SOCKS proxies, use requests with PySocks in a thread
            if proxy.protocol in ["socks4", "socks5"]:
                return await self._test_socks_proxy(proxy)
            else:
                # For HTTP/HTTPS proxies, use aiohttp
                return await self._test_http_proxy(proxy)
                        
        except Exception as e:
            logger.warning(f"Proxy {proxy.url} failed: {e}")
            proxy.failure_count += 1
            if proxy.failure_count >= self.config["proxy_max_failures"]:
                proxy.status = "failed"
            return False

    async def _test_http_proxy(self, proxy: ProxyData) -> bool:
        """Test HTTP/HTTPS proxy using aiohttp"""
        proxy_url = self._format_proxy_url(proxy)
        
        timeout = aiohttp.ClientTimeout(total=self.config["proxy_test_timeout"])
        connector = aiohttp.TCPConnector()
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:
            async with session.get(
                "https://httpbin.org/ip",
                proxy=proxy_url
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    current_ip = data.get('origin', 'unknown')
                    logger.info(f"Proxy {proxy.url} working - Current IP: {current_ip}")
                    proxy.success_count += 1
                    proxy.status = "active"
                    return True
                else:
                    raise Exception(f"HTTP {response.status}")

    async def _test_socks_proxy(self, proxy: ProxyData) -> bool:
        """Test SOCKS proxy using requests with PySocks in a thread"""
        def test_socks_sync():
            try:
                import socks
                import socket
                import requests
                
                # Configure SOCKS proxy for requests
                proxy_type = socks.SOCKS5 if proxy.protocol == "socks5" else socks.SOCKS4
                
                # Create a session with SOCKS proxy
                session = requests.Session()
                
                # Set up SOCKS proxy URL
                if proxy.username and proxy.password:
                    proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                else:
                    proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
                
                session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                
                # Test the proxy with multiple fallback services
                test_urls = [
                    "https://httpbin.org/ip",
                    "https://api.ipify.org?format=json",
                    "https://ifconfig.me/ip"
                ]
                
                for test_url in test_urls:
                    try:
                        response = session.get(
                            test_url, 
                            timeout=self.config["proxy_test_timeout"]
                        )
                        
                        if response.status_code == 200:
                            if test_url.endswith("?format=json") or "httpbin" in test_url:
                                try:
                                    data = response.json()
                                    current_ip = data.get('ip') or data.get('origin', 'unknown')
                                except:
                                    current_ip = response.text.strip()
                            else:
                                current_ip = response.text.strip()
                            
                            logger.info(f"SOCKS proxy {proxy.url} working - Current IP: {current_ip}")
                            return True, current_ip
                    except Exception as e:
                        logger.debug(f"Test URL {test_url} failed for SOCKS proxy: {e}")
                        continue
                
                raise Exception("All test URLs failed")
                    
            except ImportError:
                logger.error("PySocks not installed. Install with: pip install pysocks")
                raise Exception("PySocks not installed - run: pip install pysocks")
            except Exception as e:
                logger.debug(f"SOCKS proxy test error: {e}")
                raise e
        
        # Run the synchronous test in a thread
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            try:
                success, current_ip = await loop.run_in_executor(executor, test_socks_sync)
                proxy.success_count += 1
                proxy.status = "active"
                return True
            except Exception as e:
                raise e

    def _format_proxy_url(self, proxy: ProxyData) -> str:
        """Format proxy URL for aiohttp"""
        if proxy.username and proxy.password:
            return f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        else:
            return f"{proxy.protocol}://{proxy.host}:{proxy.port}"

    def format_proxy_for_camoufox(self, proxy: ProxyData) -> Dict:
        """Format proxy configuration for Camoufox"""
        # For SOCKS proxies, include the protocol in the server URL
        if proxy.protocol in ["socks4", "socks5"]:
            server = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
        else:
            # For HTTP/HTTPS proxies, just use the host:port format
            server = f"{proxy.host}:{proxy.port}"
        
        proxy_config = {
            "server": server
        }
        
        if proxy.username and proxy.password:
            proxy_config["username"] = proxy.username
            proxy_config["password"] = proxy.password
        
        return proxy_config

    async def test_all_proxies(self):
        """Test all proxies and update their status"""
        logger.info("Testing all proxies...")
        
        for proxy_id, proxy in self.data_manager.proxies.items():
            await self.test_proxy(proxy)
            # Small delay between tests with fluctuations
            delay = random.uniform(0.8, 1.5)  # 0.8-1.5 seconds with fluctuations
            await asyncio.sleep(delay)
        
        self.data_manager.save_proxies()
        
        working_count = len(self.get_working_proxies())
        total_count = len(self.data_manager.proxies)
        logger.info(f"Proxy test complete: {working_count}/{total_count} working")

    async def test_all_proxies_with_progress(self, progress_callback=None):
        """Test all proxies with progress callback"""
        logger.info("Testing all proxies with progress...")
        
        total_count = len(self.data_manager.proxies)
        current = 0
        
        for proxy_id, proxy in self.data_manager.proxies.items():
            current += 1
            if progress_callback:
                await progress_callback(current, total_count, proxy.url)
            
            await self.test_proxy(proxy)
            # Small delay between tests with fluctuations
            delay = random.uniform(0.8, 1.5)  # 0.8-1.5 seconds with fluctuations
            await asyncio.sleep(delay)
        
        self.data_manager.save_proxies()
        
        working_count = len(self.get_working_proxies())
        logger.info(f"Proxy test complete: {working_count}/{total_count} working")

    def get_proxy_list(self) -> List[Dict]:
        """Get list of proxies with their status"""
        proxy_list = []
        for proxy_id, proxy in self.data_manager.proxies.items():
            proxy_list.append({
                'id': proxy_id,
                'url': proxy.url,
                'protocol': proxy.protocol,
                'status': proxy.status,
                'success_count': proxy.success_count,
                'failure_count': proxy.failure_count,
                'last_used': proxy.last_used,
                'has_rotation_url': bool(proxy.rotation_url),
                'location': proxy.location or 'Unknown'
            })
        return proxy_list

    def import_proxies_from_file(self, file_path: str) -> int:
        """Import proxies from a text file"""
        imported_count = 0
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse proxy format: host:port or username:password@host:port
                    if '@' in line:
                        # Format: username:password@host:port
                        auth_part, host_port = line.split('@', 1)
                        username, password = auth_part.split(':', 1)
                        host, port = host_port.split(':', 1)
                    else:
                        # Format: host:port
                        username = password = None
                        host, port = line.split(':', 1)
                    
                    # Add proxy
                    self.add_proxy(host, int(port), username, password, None, 'http')
                    imported_count += 1
                    
        except Exception as e:
            logger.error(f"Error importing proxies from {file_path}: {e}")
        
        logger.info(f"Imported {imported_count} proxies from {file_path}")
        return imported_count