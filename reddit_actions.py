#!/usr/bin/env python3
"""
Reddit-specific actions and posting logic
"""

import asyncio
import random
import logging
import os
from typing import Any

from selector_config import selector_config

logger = logging.getLogger(__name__)


class RedditActions:
    """Handles Reddit-specific posting actions"""
    
    def __init__(self, config: dict):
        self.config = config
        self.selector_config = selector_config

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

    async def _human_type(self, page: Any, selector: str, text: str):
        """Type text with human-like delays"""
        logger.debug(f"Looking for element with selector: {selector}")
        try:
            timeout = self.selector_config.get_timeout("element_wait")
            element = await page.wait_for_selector(selector, timeout=timeout)
            logger.debug(f"Found element, clicking...")
            await element.click()
            logger.debug(f"Clicked element, waiting before typing...")
            await self._random_delay(delay_type="random")
            
            logger.debug(f"Starting to type text: '{text}' ({len(text)} characters)")
            typing_min = self.selector_config.get_delay("typing_min")
            typing_max = self.selector_config.get_delay("typing_max")
            
            for i, char in enumerate(text):
                await element.type(char)
                if i % 10 == 0:  # Log progress every 10 characters
                    logger.debug(f"Typed {i+1}/{len(text)} characters")
                
                # Add fluctuations to typing delays
                fluctuation = random.uniform(0.7, 1.3)  # ±30% fluctuation for more natural typing
                delay = random.uniform(typing_min, typing_max) * fluctuation
                await asyncio.sleep(delay)
            logger.debug(f"Finished typing text: '{text}'")
        except Exception as e:
            logger.error(f"Failed to type text '{text}' into selector '{selector}': {e}")
            raise

    async def _upload_image_file(self, page: Any, image_path: str) -> bool:
        """Helper method to handle image file uploads with file dialog automation"""
        # Verify image file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return False
        
        logger.info(f"Attempting to upload image: {image_path}")
        
        # Strategy 1: Use file chooser event to handle file dialog automatically
        upload_button_selectors = self.selector_config.get_selectors("upload_buttons")
        
        for button_selector in upload_button_selectors:
            try:
                logger.debug(f"Looking for upload button: {button_selector}")
                
                # Wait for the button to be available
                timeout = self.selector_config.get_timeout("element_wait")
                button = await page.wait_for_selector(button_selector, timeout=timeout)
                if not button:
                    continue
                    
                logger.debug(f"Found upload button: {button_selector}")
                
                # Set up file chooser event handler BEFORE clicking the button
                async def handle_file_chooser(file_chooser):
                    logger.debug(f"File chooser dialog opened, selecting file: {image_path}")
                    await file_chooser.set_files(image_path)
                    logger.info(f"File selected in dialog: {image_path}")
                
                # Listen for file chooser events
                page.on("filechooser", handle_file_chooser)
                
                try:
                    # Click the upload button to trigger file dialog
                    logger.debug(f"Clicking upload button: {button_selector}")
                    await button.click()
                    logger.debug(f"Clicked upload button, waiting for file chooser or upload completion...")
                    
                    # Wait a bit for the file chooser to appear and be handled (with fluctuations)
                    file_chooser_timeout = self.selector_config.get_timeout("file_chooser_wait")
                    base_delay = file_chooser_timeout / 1000  # Convert ms to seconds
                    fluctuation = random.uniform(0.8, 1.2)  # ±20% fluctuation
                    delay = base_delay * fluctuation
                    await asyncio.sleep(delay)
                    
                    # Check if upload was successful by looking for upload indicators
                    success_indicators = self.selector_config.get_selectors("success_indicators")
                    
                    for indicator in success_indicators:
                        try:
                            element = await page.query_selector(indicator)
                            if element:
                                logger.info(f"Upload success confirmed with indicator: {indicator}")
                                return True
                        except:
                            continue
                    
                    # If no visual indicators, assume success if no errors occurred
                    logger.info(f"File chooser handled successfully for button: {button_selector}")
                    return True
                    
                finally:
                    # Remove the event listener
                    page.remove_listener("filechooser", handle_file_chooser)
                        
            except Exception as e:
                logger.debug(f"Upload button {button_selector} failed: {e}")
                continue
        
        # Strategy 2: Try direct file input approach (fallback)
        logger.debug("Trying direct file input approach as fallback")
        file_selectors = self.selector_config.get_selectors("file_inputs")
        
        for file_selector in file_selectors:
            try:
                logger.debug(f"Trying direct file input: {file_selector}")
                await page.set_input_files(file_selector, image_path)
                logger.info(f"Successfully uploaded image with direct file input: {file_selector}")
                return True
            except Exception as e:
                logger.debug(f"Direct file input {file_selector} failed: {e}")
                continue
        
        # Strategy 3: Try drag and drop simulation (advanced fallback)
        logger.debug("Trying drag and drop simulation as advanced fallback")
        try:
            # Look for the drag and drop area
            drop_zone_selectors = self.selector_config.get_selectors("drop_zones")
            
            for drop_selector in drop_zone_selectors:
                try:
                    logger.debug(f"Looking for drop zone: {drop_selector}")
                    drop_zone = await page.wait_for_selector(drop_selector, timeout=5000)
                    if not drop_zone:
                        continue
                    
                    # Read the file as base64
                    with open(image_path, 'rb') as f:
                        file_content = f.read()
                    
                    import base64
                    file_base64 = base64.b64encode(file_content).decode()
                    file_name = os.path.basename(image_path)
                    
                    # Detect MIME type based on file extension
                    mime_type = 'image/jpeg'  # default
                    if file_name.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif file_name.lower().endswith('.gif'):
                        mime_type = 'image/gif'
                    elif file_name.lower().endswith('.webp'):
                        mime_type = 'image/webp'
                    elif file_name.lower().endswith(('.jpg', '.jpeg')):
                        mime_type = 'image/jpeg'
                    
                    # Simulate drag and drop using JavaScript
                    await page.evaluate(f"""
                        const dropZone = document.querySelector('{drop_selector}');
                        if (dropZone) {{
                            const file = new File([Uint8Array.from(atob('{file_base64}'), c => c.charCodeAt(0))], '{file_name}', {{
                                type: '{mime_type}'
                            }});
                            
                            const dataTransfer = new DataTransfer();
                            dataTransfer.items.add(file);
                            
                            const dropEvent = new DragEvent('drop', {{
                                bubbles: true,
                                cancelable: true,
                                dataTransfer: dataTransfer
                            }});
                            
                            dropZone.dispatchEvent(dropEvent);
                        }}
                    """)
                    
                    logger.info(f"Successfully simulated drag and drop on {drop_selector}")
                    return True
                    
                except Exception as e:
                    logger.debug(f"Drop zone {drop_selector} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Drag and drop approach failed: {e}")
        
        logger.error("All image upload strategies failed")
        return False

    async def _mark_post_nsfw(self, page: Any) -> bool:
        """Mark post as NSFW using the flair dropdown approach (primary method)"""
        logger.debug("Attempting to mark post as NSFW using flair dropdown...")
        
        # Primary Strategy: Flair dropdown approach (new Reddit interface)
        try:
            # Step 1: Click the flair dropdown button to open "Add tags" modal
            flair_selectors = self.selector_config.get_selectors("flair_dropdown_button")
            flair_clicked = False
            
            for flair_selector in flair_selectors:
                try:
                    logger.debug(f"Looking for flair dropdown button: {flair_selector}")
                    timeout = self.selector_config.get_timeout("element_wait")
                    element = await page.wait_for_selector(flair_selector, timeout=timeout)
                    if element:
                        logger.debug(f"Found flair button, clicking to open modal...")
                        await element.click()
                        logger.info(f"Successfully clicked flair dropdown with selector: {flair_selector}")
                        flair_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"Flair dropdown selector {flair_selector} failed: {e}")
                    continue
            
            if not flair_clicked:
                logger.warning("Could not find or click flair dropdown button - trying fallback methods")
                return await self._mark_post_nsfw_fallback(page)
            
            # Step 2: Wait for modal to appear
            logger.debug("Waiting for flair modal to appear...")
            await self._random_delay(1, 3)
            
            # Step 3: Look for NSFW switch in the modal
            logger.debug("Looking for NSFW switch in modal...")
            nsfw_switch_selectors = self.selector_config.get_selectors("nsfw_switch")
            nsfw_switched = False
            
            for switch_selector in nsfw_switch_selectors:
                try:
                    logger.debug(f"Trying NSFW switch selector in modal: {switch_selector}")
                    timeout = self.selector_config.get_timeout("element_wait")
                    switch_element = await page.wait_for_selector(switch_selector, timeout=timeout)
                    if switch_element:
                        # Check if already enabled
                        is_checked = await switch_element.get_attribute("data-checked")
                        logger.debug(f"NSFW switch current state: {is_checked}")
                        
                        if is_checked != "true":
                            logger.debug("NSFW switch is off, clicking to enable...")
                            await switch_element.click()
                            logger.info(f"Successfully toggled NSFW switch ON with selector: {switch_selector}")
                            nsfw_switched = True
                            break
                        else:
                            logger.info(f"NSFW switch already enabled with selector: {switch_selector}")
                            nsfw_switched = True
                            break
                except Exception as e:
                    logger.debug(f"NSFW switch selector {switch_selector} failed: {e}")
                    continue
            
            if not nsfw_switched:
                logger.warning("Could not find or toggle NSFW switch in modal")
                return False
            
            # Step 4: Click the "Add" button to apply changes and close modal
            logger.debug("Looking for Add/Apply button to close modal...")
            modal_submit_selectors = self.selector_config.get_selectors("modal_submit")
            modal_closed = False
            
            for submit_selector in modal_submit_selectors:
                try:
                    logger.debug(f"Trying modal submit selector: {submit_selector}")
                    timeout = self.selector_config.get_timeout("element_wait")
                    submit_element = await page.wait_for_selector(submit_selector, timeout=timeout)
                    if submit_element:
                        logger.debug("Found Add/Apply button, clicking...")
                        await submit_element.click()
                        logger.info(f"Successfully clicked Add button with selector: {submit_selector}")
                        modal_closed = True
                        break
                except Exception as e:
                    logger.debug(f"Modal submit selector {submit_selector} failed: {e}")
                    continue
            
            if not modal_closed:
                logger.warning("Could not find Add button, trying to close modal with Escape")
                try:
                    await page.keyboard.press("Escape")
                    logger.info("Closed modal using Escape key")
                except Exception as e:
                    logger.debug(f"Could not close modal with Escape: {e}")
            
            # Step 5: Wait for modal to close
            await self._random_delay(1, 2)
            logger.info("✅ Successfully marked post as NSFW using flair dropdown method")
            return True
            
        except Exception as e:
            logger.warning(f"Flair dropdown approach failed: {e}")
            return await self._mark_post_nsfw_fallback(page)

    async def _mark_post_nsfw_fallback(self, page: Any) -> bool:
        """Fallback methods for marking post as NSFW"""
        logger.debug("Trying fallback NSFW methods...")
        
        # Fallback 1: Try direct NSFW checkbox/switch
        logger.debug("Trying direct NSFW selectors...")
        nsfw_selectors = self.selector_config.get_selectors("nsfw_checkbox")
        for nsfw_selector in nsfw_selectors:
            try:
                logger.debug(f"Trying direct NSFW selector: {nsfw_selector}")
                element = await page.query_selector(nsfw_selector)
                if element:
                    # Check if it's a switch input or regular checkbox
                    if "faceplate-switch-input" in nsfw_selector:
                        # For switch inputs, click to toggle
                        await element.click()
                        logger.info(f"Successfully toggled NSFW switch with selector: {nsfw_selector}")
                        return True
                    else:
                        # For regular checkboxes, use check method
                        await page.check(nsfw_selector)
                        logger.info(f"Successfully checked NSFW checkbox with selector: {nsfw_selector}")
                        return True
            except Exception as e:
                logger.debug(f"Direct NSFW selector {nsfw_selector} failed: {e}")
                continue
        
        # Fallback 2: Try alternative NSFW selectors
        logger.debug("Trying alternative NSFW selectors...")
        alternative_selectors = [
            "input[name=\"isNsfw\"]",
            "[data-testid*=\"nsfw\"]",
            "label:has-text(\"NSFW\")",
            "button:has-text(\"NSFW\")"
        ]
        
        for alt_selector in alternative_selectors:
            try:
                logger.debug(f"Trying alternative NSFW selector: {alt_selector}")
                element = await page.query_selector(alt_selector)
                if element:
                    await element.click()
                    logger.info(f"Successfully marked NSFW with alternative selector: {alt_selector}")
                    return True
            except Exception as e:
                logger.debug(f"Alternative NSFW selector {alt_selector} failed: {e}")
                continue
        
        logger.error("❌ All NSFW marking methods failed")
        return False