#!/usr/bin/env python3
"""
Core Reddit posting functionality
"""

import asyncio
import random
import logging
import os
from datetime import datetime
from typing import Any

from models import PostData

logger = logging.getLogger(__name__)


class RedditPosterCore:
    """Core Reddit posting functionality"""
    
    def __init__(self, browser_manager, reddit_actions, data_manager, selector_config):
        self.browser_manager = browser_manager
        self.reddit_actions = reddit_actions
        self.data_manager = data_manager
        self.selector_config = selector_config

    async def post_to_reddit(self, post_data: PostData) -> bool:
        """Post content to Reddit with stealth measures"""
        try:
            # Clean subreddit name - remove r/ prefix if present
            subreddit = post_data.subreddit.strip()
            if subreddit.startswith('r/'):
                subreddit = subreddit[2:]
            post_data.subreddit = subreddit
            
            logger.info(f"Starting post: {post_data.title} to r/{post_data.subreddit}")
            
            logger.debug("Creating browser session...")
            browser_instance, account = await self.browser_manager.create_browser_session(
                post_data.account_name, 
                post_data.use_proxy, 
                post_data.headless
            )
            logger.debug(f"Browser session created successfully (headless: {post_data.headless})")
            
            async with browser_instance as browser:
                page = await browser.new_page()
                
                # Set cookies
                if account and hasattr(account, 'cookies') and account.cookies:
                    cookie_list = [
                        {"name": name, "value": value, "domain": ".reddit.com", "path": "/"}
                        for name, value in account.cookies.items()
                    ]
                    logger.info(f"Setting {len(cookie_list)} cookies for account {post_data.account_name}")
                    await page.context.add_cookies(cookie_list)
                else:
                    logger.warning(f"No cookies available for account {post_data.account_name}")
                
                # Visit random pages first
                await self.browser_manager._visit_random_pages(page)
                
                # Go to Reddit homepage with increased timeout and more lenient wait condition
                logger.info("Attempting to navigate to Reddit...")
                try:
                    await page.goto("https://www.reddit.com", wait_until="domcontentloaded", timeout=60000)
                    logger.info("Successfully navigated to Reddit")
                except Exception as e:
                    logger.warning(f"Failed to navigate to Reddit with domcontentloaded, trying with load: {e}")
                    try:
                        await page.goto("https://www.reddit.com", wait_until="load", timeout=60000)
                        logger.info("Successfully navigated to Reddit with load condition")
                    except Exception as e2:
                        logger.warning(f"Failed with load condition, trying without wait condition: {e2}")
                        try:
                            await page.goto("https://www.reddit.com", timeout=60000)
                            logger.info("Successfully navigated to Reddit without wait condition")
                            # Wait for page to settle with fluctuations
                            settle_delay = random.uniform(4000, 6000)  # 4-6 seconds with fluctuations
                            await page.wait_for_timeout(int(settle_delay))
                        except Exception as e3:
                            logger.error(f"Failed to navigate to Reddit entirely: {e3}")
                            raise
                
                await self.reddit_actions._random_delay(2, 4)
                await self.browser_manager._random_scroll(page)
                
                # Navigate directly to subreddit submit page based on post type
                post_type_param = "TEXT" if post_data.post_type != "image" else "IMAGE"
                submit_url = f"https://www.reddit.com/r/{post_data.subreddit}/submit/?type={post_type_param}"
                
                logger.info(f"Navigating directly to submit page: {submit_url}")
                try:
                    await page.goto(submit_url, wait_until="domcontentloaded", timeout=30000)
                    logger.info("Successfully navigated to subreddit submit page")
                except Exception as e:
                    logger.warning(f"Failed to navigate with domcontentloaded, trying with load: {e}")
                    try:
                        await page.goto(submit_url, wait_until="load", timeout=30000)
                        logger.info("Successfully navigated to subreddit submit page with load condition")
                    except Exception as e2:
                        logger.warning(f"Failed with load condition, trying without wait condition: {e2}")
                        try:
                            await page.goto(submit_url, timeout=30000)
                            logger.info("Successfully navigated to subreddit submit page without wait condition")
                            # Wait for page to settle with fluctuations
                            settle_delay = random.uniform(2500, 3500)  # 2.5-3.5 seconds with fluctuations
                            await page.wait_for_timeout(int(settle_delay))
                        except Exception as e3:
                            logger.error(f"Failed to navigate to submit page entirely: {e3}")
                            raise
                
                # Wait for page to load
                await self.reddit_actions._random_delay(2, 4)
                logger.debug("Submit page loaded, ready to fill form")
                
                # No need to select post type or subreddit - already handled by URL
                logger.debug(f"Post type ({post_type_param}) and subreddit (r/{post_data.subreddit}) already set via URL")
                
                await self.reddit_actions._random_delay(1, 2)
                
                # Fill title
                logger.debug(f"Filling title: {post_data.title}")
                # Get title selectors from configuration
                title_selectors = self.selector_config.get_selectors("title_input")
                
                title_success = False
                for title_selector in title_selectors:
                    try:
                        logger.debug(f"Trying title selector: {title_selector}")
                        await self.reddit_actions._human_type(page, title_selector, post_data.title)
                        logger.info(f"Successfully filled title with selector: {title_selector}")
                        title_success = True
                        break
                    except Exception as e:
                        logger.debug(f"Title selector {title_selector} failed: {e}")
                        continue
                
                if not title_success:
                    logger.error("Failed to fill title with any selector")
                    raise Exception("Could not find or fill title field")
                await self.reddit_actions._random_delay(1, 2)
                
                # Handle content based on type
                logger.debug(f"Handling content for post type: {post_data.post_type}")
                if post_data.post_type == "text" and post_data.content:
                    logger.debug("Filling text content...")
                    # Get body text selectors from configuration
                    body_selectors = self.selector_config.get_selectors("text_body")
                    
                    body_success = False
                    for body_selector in body_selectors:
                        try:
                            logger.debug(f"Trying body text selector: {body_selector}")
                            await self.reddit_actions._human_type(page, body_selector, post_data.content)
                            logger.info(f"Successfully filled text content with selector: {body_selector}")
                            body_success = True
                            break
                        except Exception as e:
                            logger.debug(f"Body text selector {body_selector} failed: {e}")
                            continue
                    
                    if not body_success:
                        logger.error("Failed to fill body text with any selector")
                        raise Exception("Could not find or fill body text field")
                elif post_data.post_type == "image" and post_data.content:
                    # Handle multiple images
                    image_paths = post_data.image_paths
                    if not image_paths:
                        logger.error("No image paths found in post data")
                        raise Exception("No image paths found")
                    
                    logger.info(f"Starting image upload process for {len(image_paths)} image(s)")
                    
                    # Upload each image
                    upload_success_count = 0
                    for i, image_path in enumerate(image_paths, 1):
                        logger.debug(f"Uploading image {i}/{len(image_paths)}: {image_path}")
                        
                        # Use the helper method to upload the image
                        # First image uses regular upload button, subsequent images use "add more" button
                        is_first_image = (i == 1)
                        upload_success = await self.reddit_actions._upload_image_file(page, image_path, is_first_image)
                        
                        if upload_success:
                            upload_success_count += 1
                            logger.info(f"Successfully uploaded image {i}/{len(image_paths)}: {os.path.basename(image_path)}")
                            
                            # Wait between uploads to avoid overwhelming the server
                            if i < len(image_paths):  # Don't wait after the last image
                                logger.debug(f"Waiting before uploading next image ({i+1}/{len(image_paths)})...")
                                await self.reddit_actions._random_delay(delay_type="between_uploads")
                        else:
                            logger.warning(f"Failed to upload image {i}/{len(image_paths)}: {os.path.basename(image_path)}")
                            # Still continue with remaining images
                    
                    if upload_success_count == 0:
                        logger.error("Failed to upload any images")
                        raise Exception("Could not upload any image files")
                    elif upload_success_count < len(image_paths):
                        logger.warning(f"Only uploaded {upload_success_count}/{len(image_paths)} images successfully")
                    
                    logger.info(f"Image upload process completed successfully - {upload_success_count}/{len(image_paths)} images uploaded")
                else:
                    logger.debug("No content to add or content is empty")
                
                # Mark as NSFW if needed
                if post_data.nsfw:
                    logger.debug("Marking post as NSFW...")
                    nsfw_success = await self.reddit_actions._mark_post_nsfw(page)
                    
                    if not nsfw_success:
                        logger.warning("Could not mark post as NSFW with any method")
                
                await self.reddit_actions._random_delay(delay_type="pre_submit")
                logger.debug("Pre-submission delay completed")
                
                # Submit post
                logger.debug("Submitting post...")
                submit_selectors = self.selector_config.get_selectors("submit_buttons")
                submit_success = False
                
                for submit_selector in submit_selectors:
                    try:
                        logger.debug(f"Trying submit selector: {submit_selector}")
                        await page.click(submit_selector)
                        logger.info(f"Successfully clicked submit button with selector: {submit_selector}")
                        submit_success = True
                        break
                    except Exception as e:
                        logger.debug(f"Submit selector {submit_selector} failed: {e}")
                        continue
                
                if not submit_success:
                    logger.error("Failed to click submit button with any selector")
                    raise Exception("Could not submit post")
                
                # Wait for post to be created (with fluctuations)
                logger.debug("Waiting for post submission to complete...")
                submit_timeout = self.selector_config.get_timeout("submit_wait")
                base_delay = submit_timeout / 1000  # Convert ms to seconds
                fluctuation = random.uniform(0.8, 1.2)  # ±20% fluctuation
                delay = base_delay * fluctuation
                logger.debug(f"Submit wait delay: {delay:.2f} seconds (base: {base_delay:.2f}, fluctuation: {fluctuation:.2f})")
                await asyncio.sleep(delay)
                logger.debug("Post submission wait completed")
                
                # Check if post was successful
                current_url = page.url
                logger.debug(f"Current URL after submission: {current_url}")
                
                if "/comments/" in current_url or "reddit.com/r/" in current_url:
                    logger.info(f"Post created successfully: {post_data.title}")
                    logger.debug(f"Success URL: {current_url}")
                    post_data.status = "posted"
                    
                    # Update account stats
                    if hasattr(account, 'post_count'):
                        account.post_count += 1
                    else:
                        account.post_count = 1
                    account.last_used = datetime.now()
                    logger.debug(f"Updated account stats for {post_data.account_name}")
                    
                    # Wait 5 seconds (with random fluctuations) before closing browser
                    logger.debug("Waiting before closing browser...")
                    await self.reddit_actions._random_delay(min_seconds=4.0, max_seconds=6.0, delay_type="post_completion")
                    logger.debug("Post completion wait finished")
                    
                    return True
                else:
                    logger.warning(f"Post may have failed - unexpected URL: {current_url}")
                    # Check for error messages
                    logger.debug("Checking for error messages...")
                    error_elements = await page.query_selector_all('[role="alert"], .error, [data-testid="error"]')
                    error_message = ""
                    for element in error_elements:
                        text = await element.text_content()
                        if text:
                            error_message += text + " "
                            logger.debug(f"Found error text: {text}")
                    
                    post_data.status = "failed"
                    post_data.error_message = error_message.strip() or "Unknown error - unexpected URL after submission"
                    logger.error(f"Post failed: {post_data.error_message}")
                    logger.debug(f"Final URL: {current_url}")
                    return False
                    
        except Exception as e:
            import traceback
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(f"Error posting to Reddit: {e}")
            logger.error(f"Exception type: {exc_type.__name__}")
            logger.error(f"Exception occurred at line {exc_traceback.tb_lineno}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            post_data.status = "failed"
            post_data.error_message = str(e)
            return False
        finally:
            self.data_manager.save_posts()
            self.data_manager.save_accounts()