#!/usr/bin/env python3
"""
Instagram Story Archiver
Archive Instagram stories and post them to Twitter/X in per-account threads.

Designed to run once per invocation - orchestrated by GitHub Actions every 1 hour.
"""

import logging
import sys
from datetime import datetime

from config import Config
from story_archiver import StoryArchiver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('archiver.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


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

    args = parser.parse_args()

    try:
        config = Config()
        config.validate()
        logger.info("Configuration loaded successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    archiver = StoryArchiver(config)

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
    archiver.archive_all_stories()
    archiver.print_status()
    logger.info("Archive check completed")


if __name__ == '__main__':
    main()
