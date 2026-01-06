#!/usr/bin/env python3
"""
Instagram Story Archiver
Archive Instagram stories and post them to Twitter/X in per-account threads.

Designed to be run on a schedule - orchestrated by GitHub Actions every 8 hours.
Posts stories at the start of the next day.
"""

import logging
import os
import sys
from datetime import datetime

from config import Config
from discord_notifier import DiscordNotifier
from story_archiver import StoryArchiver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('archiver.log', mode='a'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

for handler in logger.handlers:
    handler.flush = lambda: None


def _github_context() -> dict:
    return {
        'workflow': os.getenv('GITHUB_WORKFLOW', 'Manual Run'),
        'actor': os.getenv('GITHUB_ACTOR', 'Local User'),
        'repository': os.getenv('GITHUB_REPOSITORY', 'Local Repository'),
        'branch': os.getenv('GITHUB_REF_NAME', 'main'),
        'run_url': (
            os.getenv('GITHUB_SERVER_URL', 'https://github.com')
            + '/'
            + os.getenv('GITHUB_REPOSITORY', 'user/repo')
            + '/actions/runs/'
            + os.getenv('GITHUB_RUN_ID', '0')
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description='Instagram Story Archiver - archive and post stories to Twitter'
    )
    parser.add_argument('--story-id', type=str, help='Archive a specific story by ID')
    parser.add_argument(
        '--username',
        type=str,
        help='Instagram username for --story-id (defaults to primary configured account)',
    )
    parser.add_argument('--status', action='store_true', help='Show archive status and exit')
    parser.add_argument('--post', action='store_true', help='Force post pending stories')
    parser.add_argument(
        '--post-daily',
        action='store_true',
        help='Post stories from previous days grouped by day',
    )
    parser.add_argument('--fetch-only', action='store_true', help='Only fetch and archive, do not post')
    parser.add_argument(
        '--archive-only',
        action='store_true',
        help='Archive stories without posting (for testing)',
    )
    parser.add_argument(
        '--verify-twitter',
        action='store_true',
        help='Verify Twitter API credentials and permissions',
    )
    parser.add_argument(
        '--cleanup-only',
        action='store_true',
        help='Run media cache cleanup only (no archiving or posting)',
    )

    args = parser.parse_args()

    try:
        config = Config()
        config.validate()
        logger.info('Configuration loaded successfully')
    except ValueError as e:
        logger.error(f'Configuration error: {e}')
        sys.exit(1)

    discord = DiscordNotifier(
        config.DISCORD_WEBHOOK_SUCCESS_URL,
        config.DISCORD_WEBHOOK_FAILURE_URL,
    )

    github_context = _github_context()

    if os.getenv('GITHUB_ACTIONS'):
        discord.notify_github_action_start(
            workflow_name=github_context['workflow'],
            actor=github_context['actor'],
            repository=github_context['repository'],
            branch=github_context['branch'],
        )

    archiver = StoryArchiver(config, discord)

    try:
        if args.verify_twitter:
            logger.info('Verifying Twitter API credentials...')
            if archiver.twitter_api.verify_credentials():
                logger.info('✓ Twitter API credentials are valid')
                logger.info('✓ Your Twitter app has the correct permissions')
                sys.exit(0)
            logger.error('✗ Twitter API verification failed')
            sys.exit(1)

        if args.status:
            archiver.print_status()
            return

        if args.story_id:
            username = (args.username or config.INSTAGRAM_USERNAME).strip().lstrip('@')
            logger.info(f'Archiving specific story for {username}: {args.story_id}')
            success = archiver.process_story(username, args.story_id)
            if success:
                logger.info('Story archived successfully')
                return

            logger.error('Failed to archive story')
            sys.exit(1)

        logger.info(f'Starting archive check at {datetime.now()}')
        logger.info(f"Watching Instagram accounts: {', '.join(config.INSTAGRAM_USERNAMES)}")

        # Initialize failure counter
        new_failed = 0

        # Post only (no archiving)
        if args.post_daily:
            logger.info('Running in daily post mode...')

            before_posted_counts = {}
            before_archived_totals = {}
            for username in config.INSTAGRAM_USERNAMES:
                uname = username.strip().lstrip('@')
                stats = archiver.archive_manager.get_statistics(uname)
                stories = stats.get('stories', [])
                before_archived_totals[uname] = len(stories)
                before_posted_counts[uname] = sum(
                    1 for s in stories if isinstance(s, dict) and s.get('tweet_ids')
                )

            new_posted, new_failed = archiver.post_pending_stories_daily()
            logger.info(f'Posted {new_posted} stories from previous days')
            logger.info(f'Failed to post {new_failed} stories from previous days')

            # Cleanup media cache after posting (only if no failures)
            if new_posted > 0 and new_failed == 0:
                cleaned_count = archiver.cleanup_media_cache()
                logger.info(f'Cleaned up {cleaned_count} media files from cache')

            after_posted_counts = {}
            for username in config.INSTAGRAM_USERNAMES:
                uname = username.strip().lstrip('@')
                stats = archiver.archive_manager.get_statistics(uname)
                stories = stats.get('stories', [])
                after_posted_counts[uname] = sum(
                    1 for s in stories if isinstance(s, dict) and s.get('tweet_ids')
                )

            if os.getenv('GITHUB_ACTIONS'):
                per_user = {}
                for username in config.INSTAGRAM_USERNAMES:
                    uname = username.strip().lstrip('@')
                    before_posted = before_posted_counts.get(uname, 0)
                    after_posted = after_posted_counts.get(uname, 0)
                    per_user[uname] = {
                        'posted_now': max(0, after_posted - before_posted),
                        'archived_total': before_archived_totals.get(uname, 0),
                        'already_posted': before_posted,
                    }

                discord.notify_post_daily_summary(
                    workflow_name=github_context['workflow'],
                    actor=github_context['actor'],
                    repository=github_context['repository'],
                    branch=github_context['branch'],
                    run_url=github_context['run_url'],
                    per_user=per_user,
                )

            archiver.log_pending_story_count()
            archiver.print_status()
            logger.info('Daily post check completed')

            # Exit with error code if any posts failed
            if new_failed > 0:
                logger.error(f'❌ {new_failed} stories failed to post. Check logs for details.')
                sys.exit(1)

            return

        # Cleanup only (no archiving or posting)
        if args.cleanup_only:
            logger.info('Running in cleanup-only mode...')
            cleaned_count = archiver.cleanup_media_cache()
            logger.info(f'Cleaned up {cleaned_count} media files from cache')
            archiver.print_status()
            logger.info('Cleanup completed')
            return

        # Archive (always do this unless --post-daily)
        if args.fetch_only and not args.archive_only:
            new_archived, fetch_summary = archiver.archive_all_stories_with_summary()
        elif args.archive_only:
            new_archived = archiver.archive_only()
            fetch_summary = None
        else:
            new_archived = archiver.archive_all_stories()
            fetch_summary = None

        logger.info(f'Archived {new_archived} new stories')

        if not args.fetch_only and not args.archive_only:
            logger.info('Checking for pending stories to post...')
            new_posted, new_failed = archiver.post_pending_stories()
            logger.info(f'Posted {new_posted} pending stories')
            logger.info(f'Failed to post {new_failed} pending stories')

            # Cleanup media cache after posting (only if no failures)
            if new_posted > 0 and new_failed == 0:
                cleaned_count = archiver.cleanup_media_cache()
                logger.info(f'Cleaned up {cleaned_count} media files from cache')
        elif args.fetch_only:
            logger.info('Skipping post step (--fetch-only)')
        elif args.archive_only:
            logger.info('Skipping post step (--archive-only)')

        archiver.log_pending_story_count()
        archiver.print_status()
        logger.info('Archive check completed')

        # Exit with error code if any posts failed (for non-daily posting)
        if not args.fetch_only and not args.archive_only and new_failed > 0:
            logger.error(f'❌ {new_failed} stories failed to post. Check logs for details.')
            sys.exit(1)

        if os.getenv('GITHUB_ACTIONS'):
            if args.fetch_only and fetch_summary is not None:
                discord.notify_fetch_only_summary(
                    workflow_name=github_context['workflow'],
                    actor=github_context['actor'],
                    repository=github_context['repository'],
                    branch=github_context['branch'],
                    run_url=github_context['run_url'],
                    per_user=fetch_summary,
                )
            else:
                with open('archiver.log', 'r') as log_file:
                    logs = log_file.read()
                discord.notify_github_action_success(
                    workflow_name=github_context['workflow'],
                    actor=github_context['actor'],
                    repository=github_context['repository'],
                    branch=github_context['branch'],
                    run_url=github_context['run_url'],
                    logs=logs[-2000:] if len(logs) > 2000 else logs,
                )

    except Exception as e:
        logger.error(f'Fatal error: {str(e)}', exc_info=True)

        if os.getenv('GITHUB_ACTIONS'):
            import traceback

            error_trace = traceback.format_exc()
            logs = ''
            try:
                with open('archiver.log', 'r') as log_file:
                    logs = log_file.read()
            except Exception:
                pass

            status_code = None
            response_text = None
            if hasattr(e, 'response') and getattr(e, 'response') is not None:
                status_code = getattr(e.response, 'status_code', None)
                response_text = getattr(e.response, 'text', None)

            discord.notify_github_action_failure(
                workflow_name=github_context['workflow'],
                actor=github_context['actor'],
                repository=github_context['repository'],
                branch=github_context['branch'],
                error=error_trace,
                run_url=github_context['run_url'],
                logs=logs[-2000:] if len(logs) > 2000 else logs,
                status_code=status_code,
                response_text=response_text,
            )

        sys.exit(1)


if __name__ == '__main__':
    main()
