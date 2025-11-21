#!/usr/bin/env python3
"""
Post scheduling system for Reddit Poster Bot
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import List

from models import PostData

logger = logging.getLogger(__name__)


class PostScheduler:
    """Handles post scheduling and execution"""
    
    def __init__(self, data_manager, reddit_poster, config: dict):
        self.data_manager = data_manager
        self.reddit_poster = reddit_poster
        self.config = config

    def get_pending_posts(self) -> List[PostData]:
        """Get all pending posts ready to be posted"""
        now = datetime.now()
        ready_posts = []
        
        for post in self.data_manager.posts:
            if post.status == "pending":
                if post.scheduled_time is None:
                    logger.debug(f"Post '{post.title}' has no scheduled time - skipping")
                elif post.scheduled_time <= now:
                    time_diff = (now - post.scheduled_time).total_seconds()
                    logger.debug(f"Post '{post.title}' is ready (scheduled: {post.scheduled_time}, {time_diff:.0f}s overdue)")
                    ready_posts.append(post)
                else:
                    time_until = (post.scheduled_time - now).total_seconds()
                    logger.debug(f"Post '{post.title}' not ready yet (scheduled: {post.scheduled_time}, {time_until:.0f}s remaining)")
        
        return ready_posts

    def reschedule_pending_posts_to_future(self, minutes_from_now: int = 5):
        """Reschedule all pending posts to future times for testing"""
        now = datetime.now()
        updated_count = 0
        
        for i, post in enumerate(self.data_manager.posts):
            if post.status == "pending":
                # Schedule posts 5 minutes apart starting from minutes_from_now
                new_time = now + timedelta(minutes=minutes_from_now + (i * 5))
                old_time = post.scheduled_time
                post.scheduled_time = new_time
                updated_count += 1
                
                old_str = old_time.strftime("%Y-%m-%d %H:%M:%S") if old_time else "None"
                new_str = new_time.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"Rescheduled '{post.title}' from {old_str} to {new_str}")
        
        if updated_count > 0:
            self.data_manager.save_posts()
            logger.info(f"Rescheduled {updated_count} posts to future times")
        
        return updated_count

    async def _process_account_posts(self, account_name: str, posts: List[PostData], posts_processed_start: int) -> int:
        """Process posts for a single account sequentially"""
        account_posts_processed = 0
        
        for i, post in enumerate(posts):
            # Log post attempt
            scheduled_time_str = post.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if post.scheduled_time else "immediate"
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Attempting to post '{post.title}' to r/{post.subreddit} using account {account_name} (scheduled: {scheduled_time_str}, current: {current_time_str})")
            
            # Mark post as currently being processed
            post.status = "posting"
            self.data_manager.save_posts()
            
            # Post to Reddit
            success = await self.reddit_poster.post_to_reddit(post)
            
            if success:
                account_posts_processed += 1
                total_processed = posts_processed_start + account_posts_processed
                logger.info(f"Successfully posted #{total_processed}: '{post.title}' to r/{post.subreddit}")
            else:
                logger.error(f"Failed to post: '{post.title}' to r/{post.subreddit} - {post.error_message}")
            
            # Save posts after each attempt
            self.data_manager.save_posts()
            
            # Update account last used time
            account = self.data_manager.accounts[account_name]
            account.last_used = datetime.now()
            self.data_manager.save_accounts()
            
            # Add safety delay between posts from the same account (except for the last post)
            if i < len(posts) - 1:
                safety_delay = random.randint(30, 60)
                logger.info(f"Adding {safety_delay}s safety delay before next post from account {account_name}")
                await asyncio.sleep(safety_delay)
        
        return account_posts_processed

    async def run_scheduler(self):
        """Run the post scheduler"""
        logger.info("Starting Reddit post scheduler")
        logger.info(f"Scheduler configuration: account_cooldown={self.config['min_delay_between_posts']}s")
        logger.info("Posts will be made at their exact scheduled times with account cooldown protection")
        
        posts_processed = 0
        
        while True:
            try:
                pending_posts = self.get_pending_posts()
                
                if pending_posts:
                    logger.info(f"Found {len(pending_posts)} posts ready for posting")
                    # Log details about ready posts
                    for post in pending_posts:
                        scheduled_str = post.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if post.scheduled_time else "None"
                        logger.info(f"  - '{post.title}' scheduled for {scheduled_str}")
                    
                    # Sort by scheduled time
                    pending_posts.sort(key=lambda x: x.scheduled_time or datetime.min)
                    
                    # Group posts by scheduled time to process simultaneously
                    posts_by_time = {}
                    for post in pending_posts:
                        time_key = post.scheduled_time.replace(second=0, microsecond=0) if post.scheduled_time else datetime.min
                        if time_key not in posts_by_time:
                            posts_by_time[time_key] = []
                        posts_by_time[time_key].append(post)
                    
                    # Process each time group
                    for scheduled_time, time_group_posts in posts_by_time.items():
                        logger.info(f"Processing {len(time_group_posts)} posts scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M:%S') if scheduled_time != datetime.min else 'immediate'}")
                        
                        # Filter posts that can be posted (valid account, not on cooldown)
                        ready_posts = []
                        for post in time_group_posts:
                            if not post.account_name:
                                logger.warning(f"No account specified for post: {post.title}")
                                continue
                            
                            if post.account_name not in self.data_manager.accounts:
                                logger.error(f"Account {post.account_name} not found")
                                post.status = "failed"
                                post.error_message = "Account not found"
                                self.data_manager.save_posts()
                                continue
                            
                            # Check account cooldown
                            account = self.data_manager.accounts[post.account_name]
                            if account.last_used:
                                time_since_last = datetime.now() - account.last_used
                                min_delay = timedelta(seconds=self.config["min_delay_between_posts"])
                                if time_since_last < min_delay:
                                    remaining_cooldown = min_delay - time_since_last
                                    logger.info(f"Account {post.account_name} on cooldown for {remaining_cooldown.total_seconds():.0f} more seconds")
                                    continue
                            
                            ready_posts.append(post)
                        
                        if not ready_posts:
                            logger.info("No posts ready in this time group due to cooldowns or errors")
                            continue
                        
                        # Process posts concurrently if they use different accounts
                        # Group by account to handle same-account posts sequentially
                        posts_by_account = {}
                        for post in ready_posts:
                            if post.account_name not in posts_by_account:
                                posts_by_account[post.account_name] = []
                            posts_by_account[post.account_name].append(post)
                        
                        # Create tasks for concurrent execution
                        tasks = []
                        for account_name, account_posts in posts_by_account.items():
                            task = asyncio.create_task(self._process_account_posts(account_name, account_posts, posts_processed))
                            tasks.append(task)
                        
                        # Wait for all tasks to complete
                        if tasks:
                            logger.info(f"Starting concurrent posting for {len(tasks)} accounts")
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            
                            # Count successful posts
                            for result in results:
                                if isinstance(result, int):
                                    posts_processed += result
                                elif isinstance(result, Exception):
                                    logger.error(f"Error in concurrent posting: {result}")
                        
                        # Add a small delay between time groups to avoid overwhelming Reddit
                        if len(posts_by_time) > 1:
                            group_delay = random.randint(10, 20)
                            logger.info(f"Adding {group_delay}s delay before next time group")
                            await asyncio.sleep(group_delay)
                else:
                    # Log status when no posts are ready
                    current_time = datetime.now()
                    total_pending = len([p for p in self.data_manager.posts if p.status == "pending"])
                    if total_pending > 0:
                        next_scheduled = min([p.scheduled_time for p in self.data_manager.posts if p.status == "pending" and p.scheduled_time], default=None)
                        if next_scheduled:
                            time_until_next = next_scheduled - current_time
                            if time_until_next.total_seconds() > 0:
                                logger.info(f"No posts ready. {total_pending} posts pending. Next post at {next_scheduled.strftime('%H:%M:%S')} (in {time_until_next})")
                            else:
                                logger.info(f"No posts ready. {total_pending} posts pending (some may be on account cooldown)")
                        else:
                            logger.info(f"No posts ready. {total_pending} posts pending (no scheduled times)")
                    else:
                        logger.info("No pending posts in queue")
                    
                    # Show current time for reference
                    logger.debug(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Check every minute for new posts (with slight fluctuations)
                check_delay = random.uniform(55, 65)  # 55-65 seconds
                logger.debug(f"Checking for new posts in {check_delay:.0f} seconds")
                await asyncio.sleep(check_delay)
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Error recovery delay with fluctuations
                error_delay = random.uniform(55, 65)  # 55-65 seconds
                logger.info(f"Recovering from error, waiting {error_delay:.0f} seconds before retry")
                await asyncio.sleep(error_delay)