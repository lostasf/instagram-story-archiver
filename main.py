#!/usr/bin/env python3
"""
Gendis Instagram Story Archiver
Archive Instagram stories and post them to Twitter/X in threads.
"""

import logging
import schedule
import time
import sys
from datetime import datetime

from config import Config
from story_archiver import StoryArchiver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('archiver.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ArchiverScheduler:
    def __init__(self):
        try:
            self.config = Config()
            self.config.validate()
            logger.info("Configuration loaded successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        self.archiver = StoryArchiver(self.config)
        self.is_running = False
    
    def job(self):
        """Scheduled job to archive stories."""
        try:
            logger.info(f"Starting scheduled check at {datetime.now()}")
            self.archiver.archive_all_stories()
            self.archiver.print_status()
            logger.info("Scheduled check completed")
        except Exception as e:
            logger.error(f"Error in scheduled job: {e}", exc_info=True)
    
    def run_once(self):
        """Run archiver once and exit."""
        logger.info("Running archiver once")
        self.job()
    
    def start_scheduler(self):
        """Start the scheduler with configured interval."""
        logger.info(f"Starting scheduler - will check every {self.config.CHECK_INTERVAL_HOURS} hour(s)")
        
        schedule.every(self.config.CHECK_INTERVAL_HOURS).hours.do(self.job)
        
        self.is_running = True
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            self.stop_scheduler()
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stopped")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Gendis Instagram Story Archiver - Archive and post stories to Twitter'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit instead of starting scheduler'
    )
    parser.add_argument(
        '--story-id',
        type=str,
        help='Archive a specific story by ID'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show archive status and exit'
    )
    
    args = parser.parse_args()
    
    scheduler = ArchiverScheduler()
    
    if args.status:
        scheduler.archiver.print_status()
    elif args.story_id:
        logger.info(f"Archiving specific story: {args.story_id}")
        success = scheduler.archiver.process_story(
            scheduler.config.INSTAGRAM_USERNAME,
            args.story_id
        )
        if success:
            logger.info("Story archived successfully")
        else:
            logger.error("Failed to archive story")
    elif args.once:
        scheduler.run_once()
    else:
        scheduler.start_scheduler()


if __name__ == '__main__':
    main()
