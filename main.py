#!/usr/bin/env python3
"""
Instagram Story Archiver
Archive Instagram stories and post them to Twitter/X in per-account threads.

Designed to be run on a schedule - orchestrated by GitHub Actions every 8 hours.
Posts stories at the start of the next day.
"""

import logging
import sys
from datetime import datetime

from config import Config
from story_archiver import StoryArchiver

# Configure logging to ensure logs are written and flushed immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('archiver.log', mode='a'),  # Append mode
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Force log flushing
for handler in logger.handlers:
    handler.flush = lambda: None  # Disable buffering


def main():
    """Main entry point - runs archiver once and exits."""
    import argparse

    parser = argparse.ArgumentParser(description='Instagram Story Archiver - archive and post stories to Twitter')
    parser.add_argument('--story-id', type=str, help='Archive a specific story by ID')
    parser.add_argument(
        '--username',
        type=str,
        help='Instagram username for --story-id (defaults to primary configured account)',
    )
    parser.add_argument('--status', action='store_true', help='Show archive status and exit')
    parser.add_argument('--post', action='store_true', help='Force post pending stories')
    parser.add_argument('--post-daily', action='store_true', help='Post stories from yesterday grouped by day')
    parser.add_argument('--fetch-only', action='store_true', help='Only fetch and archive, do not post')
    parser.add_argument('--archive-only', action='store_true', help='Archive stories without posting (for testing)')
    parser.add_argument('--verify-twitter', action='store_true', help='Verify Twitter API credentials and permissions')

    args = parser.parse_args()

    try:
        config = Config()
        config.validate()
        logger.info("Configuration loaded successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    archiver = StoryArchiver(config)

    if args.verify_twitter:
        logger.info("Verifying Twitter API credentials...")
        if archiver.twitter.verify_credentials():
            logger.info("✓ Twitter API credentials are valid")
            logger.info("✓ Your Twitter app has the correct permissions")
            sys.exit(0)
        else:
            logger.error("✗ Twitter API verification failed")
            sys.exit(1)

    if args.status:
        archiver.print_status()
        return

    if args.story_id:
        username = (args.username or config.INSTAGRAM_USERNAME).strip().lstrip('@')
        logger.info(f"Archiving specific story for {username}: {args.story_id}")
        success = archiver.process_story(username, args.story_id)
        if success:
            logger.info("Story archived successfully")
            return

        logger.error("Failed to archive story")
        sys.exit(1)

    logger.info(f"Starting archive check at {datetime.now()}")
    logger.info(f"Watching Instagram accounts: {', '.join(config.INSTAGRAM_USERNAMES)}")

    # Handle --post-daily flag (post only, no archiving)
    if args.post_daily:
        logger.info("Running in daily post mode...")
        new_posted = archiver.post_pending_stories_daily()
        logger.info(f"Posted {new_posted} stories from yesterday")
        archiver.log_pending_story_count()
        archiver.print_status()
        logger.info("Daily post check completed")
        return

    # Archive all stories (always do this unless --post-daily)
    if args.archive_only:
        new_archived = archiver.archive_only()
    else:
        new_archived = archiver.archive_all_stories()
    logger.info(f"Archived {new_archived} new stories")

    # Post pending stories unless --fetch-only is set
    if not args.fetch_only and not args.archive_only:
        logger.info("Checking for pending stories to post...")
        new_posted = archiver.post_pending_stories()
        logger.info(f"Posted {new_posted} pending stories")
    elif args.fetch_only:
        logger.info("Skipping post step (--fetch-only)")
    elif args.archive_only:
        logger.info("Skipping post step (--archive-only)")

    archiver.log_pending_story_count()

    archiver.print_status()
    logger.info("Archive check completed")


if __name__ == '__main__':
    main()
