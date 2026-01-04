import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

from archive_manager import ArchiveManager
from config import Config
from instagram_api import InstagramAPI
from media_manager import MediaManager
from twitter_api import TwitterAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class StoryArchiver:
    def __init__(self, config: Config, discord_notifier=None):
        self.config = config
        self.discord = discord_notifier
        self.instagram_api = InstagramAPI(config, discord_notifier)
        self.twitter_api = TwitterAPI(config, discord_notifier)
        self.media_manager = MediaManager(config.MEDIA_CACHE_DIR)
        self.archive_manager = ArchiveManager(
            config.ARCHIVE_DB_PATH,
            default_instagram_username=config.INSTAGRAM_USERNAME,
        )

    def _format_story_datetime(self, taken_at: int) -> str:
        """Format Unix timestamp to human-readable datetime in GMT+7 timezone."""
        utc_plus_7 = timezone(timedelta(hours=7))
        dt = datetime.fromtimestamp(taken_at, tz=utc_plus_7)
        return dt.strftime("%A, %d %B %Y %H:%M")

    def _ensure_anchor_tweet(self, instagram_username: str) -> Optional[str]:
        """Ensure the anchor tweet exists for a given Instagram account."""
        username = instagram_username.strip().lstrip('@')
        anchor_id = self.archive_manager.get_anchor_tweet_id(username)

        if anchor_id:
            logger.info(f"Using existing anchor tweet for {username}: {anchor_id}")
            return anchor_id

        logger.info(f"Creating anchor tweet for {username}...")
        anchor_text = self.config.get_anchor_text(username)
        anchor_id = self.twitter_api.post_tweet(anchor_text, username=username)

        if not anchor_id:
            logger.error(f"Failed to create anchor tweet for {username}")
            return None

        self.archive_manager.set_anchor_tweet_id(username, anchor_id)
        self.archive_manager.set_last_tweet_id(username, anchor_id)
        logger.info(f"Anchor tweet created for {username}: {anchor_id}")
        return anchor_id

    def archive_story(self, username: str, story_id: str, story_payload: Optional[Dict] = None) -> bool:
        """Download media and save story to archive without posting to Twitter."""
        username = username.strip().lstrip('@')
        try:
            story_id = str(story_id)
            logger.info(f"=== Starting archive_story for {story_id} from {username} ===")

            # Check if already archived
            archived_ids = self.archive_manager.get_archived_story_ids(username)
            if story_id in archived_ids:
                logger.info(f"Story {story_id} already archived for {username}, skipping")
                return False

            # Fetch story data if not provided
            story_data = (
                story_payload
                if story_payload is not None
                else self.instagram_api.get_story_by_id(username, story_id)
            )
            if not story_data:
                logger.error(f"Failed to fetch story {story_id} from {username}")
                return False

            taken_at = int(story_data.get('taken_at', 0) or 0)
            media_list = self.instagram_api.extract_media_urls(story_data)
            if not media_list:
                logger.warning(f"No media found in story {story_id}")
                return False

            # Download and prepare ALL media items (reuse cache if present)
            local_media_paths = []
            media_types = []

            for idx, media in enumerate(media_list):
                media_type = media.get('type') or 'image'
                media_url = media.get('url')
                media_id = f"{username}_{story_id}_{idx}"

                media_path = self.media_manager.get_cached_media_path(media_id, media_type)
                if media_path:
                    logger.info(f"Using cached {media_type} for story {story_id} ({idx + 1}/{len(media_list)}): {media_path}")
                else:
                    if not media_url:
                        logger.warning(f"Missing media URL for story {story_id} item {idx}, skipping")
                        continue
                    media_path = self.media_manager.download_media(media_url, media_id, media_type)

                if not media_path:
                    logger.warning(f"Failed to prepare media {idx} for story {story_id}, continuing with others")
                    continue

                if media_type == 'image' and not media_path.endswith('_compressed.jpg'):
                    media_path = self.media_manager.compress_image(media_path)

                local_media_paths.append(media_path)
                media_types.append(media_type)

            if not local_media_paths:
                logger.warning(f"No media could be downloaded for story {story_id} at this time, but archiving metadata.")

            logger.info(f"Prepared {len(local_media_paths)} media items for story {story_id}")

            # Save to archive with all media paths
            archive_data = {
                'media_count': len(media_list),
                'media_urls': [m['url'] for m in media_list],
                'tweet_ids': [],  # Not posted yet
                'taken_at': taken_at,
                'local_media_paths': local_media_paths,
                'media_types': media_types,
                # Keep legacy fields for backward compatibility
                'local_media_path': local_media_paths[0] if local_media_paths else None,
                'media_type': media_types[0] if media_types else 'image',
            }
            self.archive_manager.add_story(username, story_id, archive_data)
            
            logger.info(f"Successfully archived story {story_id} for {username} with {len(local_media_paths)} media items")
            return True
        except Exception as e:
            logger.error(f"Error archiving story {story_id}: {e}", exc_info=True)
            return False

    def post_story(self, username: str, story_id: str) -> bool:
        """Post an archived story to Twitter."""
        username = username.strip().lstrip('@')
        try:
            story_id = str(story_id)
            logger.info(f"=== Starting post_story for {story_id} from {username} ===")

            # Get story from archive
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])
            story_entry = next((s for s in stories if str(s.get('story_id')) == story_id), None)

            if not story_entry:
                logger.error(f"Story {story_id} not found in archive for {username}")
                return False

            if story_entry.get('tweet_ids'):
                logger.info(f"Story {story_id} already posted for {username}")
                return True

            # Ensure local media exists; reuse cache if present, otherwise (re)download.
            stored_media_paths = story_entry.get('local_media_paths')
            stored_media_types = story_entry.get('media_types')

            if not isinstance(stored_media_paths, list):
                stored_media_paths = []
            if not isinstance(stored_media_types, list):
                stored_media_types = []

            # Backward compatibility: legacy single media format
            if not stored_media_paths:
                legacy_path = story_entry.get('local_media_path')
                legacy_type = story_entry.get('media_type', 'image')
                if legacy_path:
                    stored_media_paths = [legacy_path]
                    stored_media_types = [legacy_type]

            media_urls = story_entry.get('media_urls') or []

            # If we have URLs, prefer them as the source of truth for expected media count.
            if media_urls:
                expected_count = len(media_urls)
                media_paths = []
                media_types = []

                for idx, url in enumerate(media_urls):
                    media_type = (
                        stored_media_types[idx]
                        if idx < len(stored_media_types) and stored_media_types[idx]
                        else ('video' if 'video' in str(url).lower() else 'image')
                    )

                    existing_path = stored_media_paths[idx] if idx < len(stored_media_paths) else None
                    if existing_path and os.path.exists(existing_path):
                        media_path = existing_path
                    else:
                        media_id = f"{username}_{story_id}_{idx}"
                        media_path = self.media_manager.get_cached_media_path(media_id, media_type)
                        if not media_path:
                            media_path = self.media_manager.download_media(url, media_id, media_type)

                    if not media_path:
                        logger.error(f"Failed to prepare media {idx + 1}/{expected_count} for story {story_id}")
                        continue

                    if media_type == 'image' and not media_path.endswith('_compressed.jpg'):
                        media_path = self.media_manager.compress_image(media_path)

                    media_paths.append(media_path)
                    media_types.append(media_type)

                if not media_paths:
                    logger.error(f"Failed to prepare any media for story {story_id}")
                    return False

                if expected_count > 1 and len(media_paths) != expected_count:
                    logger.error(
                        f"Story {story_id} expects {expected_count} media items but only {len(media_paths)} were available. "
                        "Will retry on next run."
                    )
                    return False

                self.archive_manager.update_story_local_paths(username, story_id, media_paths)
            else:
                # No URLs recorded (very old archive entries). Use whatever local paths exist.
                valid_paths = [p for p in stored_media_paths if p and os.path.exists(p)]
                if not valid_paths:
                    logger.error(f"No local media paths available for story {story_id}")
                    return False
                media_paths = valid_paths
                media_types = stored_media_types

            # Ensure anchor tweet
            anchor_id = self._ensure_anchor_tweet(username)
            if not anchor_id:
                logger.error("Cannot proceed without anchor tweet")
                return False

            # Prepare caption
            taken_at = story_entry.get('taken_at')
            caption = self.config.get_story_caption(username, taken_at)
            
            last_tweet_id = self.archive_manager.get_last_tweet_id(username) or anchor_id
            
            # Post all media as a thread
            # Twitter allows up to 4 media items (images/videos) per tweet
            tweet_ids = []
            
            # Prepare batches of media (up to 4 items per tweet)
            media_batches = [media_paths[i:i + 4] for i in range(0, len(media_paths), 4)]
            
            # Post each batch as a tweet
            for idx, batch_paths in enumerate(media_batches):
                # Upload all media in batch
                media_ids = []
                for path in batch_paths:
                    media_id = self.twitter_api.upload_media(path, username=username)
                    if media_id:
                        media_ids.append(media_id)
                
                if not media_ids:
                    logger.error(f"Failed to upload media batch {idx + 1} for story {story_id}")
                    continue
                
                # Add batch info to caption if there are multiple batches
                if len(media_batches) > 1:
                    tweet_text = f"{caption}\n({idx + 1}/{len(media_batches)})"
                else:
                    tweet_text = caption
                
                tweet_id = self.twitter_api.post_tweet(
                    text=tweet_text,
                    media_ids=media_ids,
                    reply_to_id=last_tweet_id,
                    username=username,
                )
                
                if not tweet_id:
                    logger.error(f"Failed to post tweet for batch {idx + 1} of story {story_id}")
                    # Save orphan media IDs so an engineer can manually run the command
                    self.archive_manager.add_orphan_media_ids(username, story_id, media_ids)
                    break
                
                tweet_ids.append(tweet_id)
                last_tweet_id = tweet_id
                logger.info(f"Posted tweet {idx + 1}/{len(media_batches)} for story {story_id}")
            
            if not tweet_ids:
                logger.error(f"Failed to post any tweets for story {story_id}")
                return False

            # Update archive
            self.archive_manager.update_story_tweets(username, story_id, tweet_ids)
            self.archive_manager.set_last_tweet_id(username, tweet_ids[-1])
            
            # Cleanup media files after successful posting
            for media_path in media_paths:
                if media_path and os.path.exists(media_path):
                    self.media_manager.cleanup_media(media_path)
            
            # Clear local paths in archive
            self.archive_manager.update_story_local_paths(username, story_id, [])

            logger.info(f"Successfully posted story {story_id} for {username} with {len(tweet_ids)} tweet(s)")
            
            # Notify Discord about successful Twitter post (avoid spamming GitHub Actions runs)
            if self.discord and not os.getenv('GITHUB_ACTIONS'):
                self.discord.notify_twitter_post_success(
                    username=username,
                    story_count=1,
                    tweet_ids=tweet_ids,
                )
            
            return True
        except Exception as e:
            logger.error(f"Error posting story {story_id}: {e}", exc_info=True)
            return False

    def process_story(self, username: str, story_id: str, story_payload: Optional[Dict] = None) -> bool:
        """Process a single story immediately: archive and post."""
        if self.archive_story(username, story_id, story_payload):
            return self.post_story(username, story_id)
        return False

    def _sync_cache_only_stories(self, username: str, ignore_story_ids: Set[str]) -> int:
        """Backfill archive entries for media already present in media_cache and cleanup posted media.

        1. Backfills missing stories from cache (safety net for crashes).
        2. Deletes media from cache if the corresponding story has already been posted.
        """
        username = username.strip().lstrip('@')
        cache_dir = self.media_manager.cache_dir

        try:
            filenames = os.listdir(cache_dir)
        except FileNotFoundError:
            return 0

        archived_ids = self.archive_manager.get_archived_story_ids(username)
        stats = self.archive_manager.get_statistics(username)
        stories = stats.get('stories', [])
        posted_ids = {str(s.get('story_id')) for s in stories if s.get('tweet_ids')}
        
        grouped = {}
        cleaned_count = 0

        for filename in filenames:
            if not filename.startswith(f"{username}_"):
                continue

            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext not in ('.jpg', '.mp4'):
                continue

            stem = filename.rsplit('.', 1)[0]
            is_compressed = False
            if stem.endswith('_compressed'):
                stem = stem[: -len('_compressed')]
                is_compressed = True

            parts = stem.split('_')
            if len(parts) < 3:
                continue

            story_id = parts[-2]
            idx_str = parts[-1]
            if not idx_str.isdigit():
                continue

            story_id_str = str(story_id)
            
            # If already posted, delete the file
            if story_id_str in posted_ids:
                file_path = os.path.join(cache_dir, filename)
                if self.media_manager.cleanup_media(file_path):
                    cleaned_count += 1
                continue

            # If already archived but not posted, skip backfilling
            if story_id_str in archived_ids or story_id_str in ignore_story_ids:
                continue

            media_type = 'video' if ext == '.mp4' else 'image'
            grouped.setdefault(story_id_str, {})[int(idx_str)] = media_type

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} already-posted media files for {username}")

        added = 0
        for story_id_str, by_idx in grouped.items():
            indices = sorted(by_idx.keys())

            local_media_paths = []
            media_types = []
            for idx in indices:
                media_type = by_idx[idx]
                media_id = f"{username}_{story_id_str}_{idx}"
                media_path = self.media_manager.get_cached_media_path(media_id, media_type)
                if not media_path:
                    continue
                local_media_paths.append(media_path)
                media_types.append(media_type)

            if not local_media_paths:
                continue

            taken_at = int(min(os.path.getmtime(p) for p in local_media_paths))

            archive_data = {
                'media_count': len(local_media_paths),
                'media_urls': [],
                'tweet_ids': [],
                'taken_at': taken_at,
                'local_media_paths': local_media_paths,
                'media_types': media_types,
                'local_media_path': local_media_paths[0] if local_media_paths else None,
                'media_type': media_types[0] if media_types else 'image',
            }

            if self.archive_manager.add_story(username, story_id_str, archive_data):
                added += 1

        return added

    def archive_all_stories_for_user_with_summary(self, username: str) -> Tuple[int, Dict[str, int]]:
        """Fetch + archive stories for a user and return a summary for Discord notifications."""
        username = username.strip().lstrip('@')

        summary: Dict[str, int] = {
            'fetched': 0,
            'new_archived': 0,
            'already_archived': 0,
            'already_posted': 0,
            'fetch_failed': 0,
        }

        try:
            self.archive_manager.set_last_check(username)
            logger.info(f"Starting story check for {username}")

            stories = self.instagram_api.get_user_stories(username)
            if stories is None:
                summary['fetch_failed'] = 1
                logger.error(f"Failed to fetch stories from Instagram API for {username}")
                return 0, summary

            if not isinstance(stories, list):
                summary['fetch_failed'] = 1
                logger.error(f"Expected list from Instagram API, got {type(stories)}: {stories}")
                return 0, summary

            story_items = [story for story in stories if isinstance(story, dict)]

            def _story_timestamp(item: Dict) -> int:
                value = item.get('taken_at') or 0
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0

            story_items.sort(key=_story_timestamp)
            summary['fetched'] = len(story_items)

            story_ids_in_api = {
                str(story.get('pk') or story.get('id'))
                for story in story_items
                if (story.get('pk') or story.get('id'))
            }

            archived_ids = self.archive_manager.get_archived_story_ids(username)
            stats = self.archive_manager.get_statistics(username)
            archived_stories = stats.get('stories', [])
            posted_ids = {
                str(s.get('story_id'))
                for s in archived_stories
                if isinstance(s, dict) and s.get('tweet_ids')
            }

            summary['already_archived'] = len(story_ids_in_api & archived_ids)
            summary['already_posted'] = len(story_ids_in_api & posted_ids)

            processed_count = 0

            if not story_items:
                logger.info(f"No active stories available for {username} at this time")

            for i, story in enumerate(story_items):
                story_id = story.get('pk') or story.get('id')
                if not story_id:
                    logger.debug(f"Skipping story {i} without an ID")
                    continue

                story_id_str = str(story_id)
                logger.info(f"Processing story {i + 1}/{len(story_items)} for {username}: {story_id_str}")

                if story_id_str in archived_ids:
                    logger.info(f"Story {story_id_str} already archived for {username}, skipping")
                    continue

                success = self.archive_story(username, story_id_str, story_payload=story)
                logger.info(f"Story {story_id_str} archiving result for {username}: {success}")

                if success:
                    processed_count += 1
                    archived_ids.add(story_id_str)

            cache_only_added = self._sync_cache_only_stories(username, story_ids_in_api)
            if cache_only_added:
                processed_count += cache_only_added
                logger.info(
                    f"Backfilled {cache_only_added} story(ies) already present in media_cache but missing from archive.json for {username}"
                )

            logger.info(f"Story check completed for {username}")
            logger.info(f"New stories archived for {username}: {processed_count}")

            summary['new_archived'] = processed_count
            return processed_count, summary

        except Exception as e:
            summary['fetch_failed'] = 1
            logger.error(f"Error archiving stories for {username}: {e}", exc_info=True)
            return 0, summary

    def archive_all_stories_for_user(self, username: str) -> int:
        """Fetch and archive all available stories for the given username."""
        username = username.strip().lstrip('@')

        try:
            # Update last check timestamp immediately
            self.archive_manager.set_last_check(username)
            logger.info(f"Starting story check for {username}")

            stories = self.instagram_api.get_user_stories(username)
            if stories is None:
                logger.error(f"Failed to fetch stories from Instagram API for {username}")
                return 0

            if not isinstance(stories, list):
                logger.error(f"Expected list from Instagram API, got {type(stories)}: {stories}")
                return 0

            story_items = [story for story in stories if isinstance(story, dict)]
            if len(story_items) != len(stories):
                logger.warning(f"Some stories are not dictionaries: {len(story_items)}/{len(stories)} are valid")

            def _story_timestamp(item: Dict) -> int:
                value = item.get('taken_at') or 0
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0

            story_items.sort(key=_story_timestamp)
            logger.info(f"Found {len(story_items)} stories to evaluate for {username}")

            story_ids_in_api = {
                str(story.get('pk') or story.get('id'))
                for story in story_items
                if (story.get('pk') or story.get('id'))
            }

            archived_ids = self.archive_manager.get_archived_story_ids(username)
            processed_count = 0

            if not story_items:
                logger.info(f"No active stories available for {username} at this time")

            for i, story in enumerate(story_items):
                story_id = story.get('pk') or story.get('id')
                if not story_id:
                    logger.debug(f"Skipping story {i} without an ID")
                    continue

                story_id_str = str(story_id)
                logger.info(f"Processing story {i + 1}/{len(story_items)} for {username}: {story_id_str}")

                if story_id_str in archived_ids:
                    logger.info(f"Story {story_id_str} already archived for {username}, skipping")
                    continue

                success = self.archive_story(username, story_id_str, story_payload=story)
                logger.info(f"Story {story_id_str} archiving result for {username}: {success}")

                if success:
                    processed_count += 1
                    archived_ids.add(story_id_str)

            cache_only_added = self._sync_cache_only_stories(username, story_ids_in_api)
            if cache_only_added:
                processed_count += cache_only_added
                logger.info(
                    f"Backfilled {cache_only_added} story(ies) already present in media_cache but missing from archive.json for {username}"
                )

            logger.info(f"Story check completed for {username}")
            logger.info(f"New stories archived for {username}: {processed_count}")
            return processed_count

        except Exception as e:
            logger.error(f"Error archiving stories for {username}: {e}", exc_info=True)
            return 0

    def archive_all_stories(self) -> int:
        """Fetch and archive all available stories for all configured usernames."""
        total_processed = 0
        for username in self.config.INSTAGRAM_USERNAMES:
            total_processed += self.archive_all_stories_for_user(username)
        return total_processed

    def archive_all_stories_with_summary(self) -> Tuple[int, Dict[str, Dict[str, int]]]:
        """Fetch and archive stories and return a per-user summary for notifications."""
        total_processed = 0
        per_user: Dict[str, Dict[str, int]] = {}

        for username in self.config.INSTAGRAM_USERNAMES:
            processed, summary = self.archive_all_stories_for_user_with_summary(username)
            total_processed += processed
            per_user[username.strip().lstrip('@')] = summary

        return total_processed, per_user

    def archive_only(self) -> int:
        """Archive all available stories but DO NOT post them (for testing/debugging)."""
        total_processed = 0
        logger.info("Starting archive-only mode (no posting)")
        for username in self.config.INSTAGRAM_USERNAMES:
            total_processed += self.archive_all_stories_for_user(username)
        logger.info(f"Archive-only completed: {total_processed} stories archived")
        return total_processed

    def post_pending_stories(self) -> int:
        """Post all pending stories that have been archived but not yet posted to Twitter.

        Logic:
        1. Get current date in GMT+7 timezone
        2. Find stories with empty tweet_ids AND taken_at < today (before today)
        3. Post those stories to Twitter (one tweet per story, multi-media batching within story)
        4. After posting, update metadata and delete media files
        5. Log stories uploaded on the same day as planned for next day
        """
        total_posted = 0

        now = datetime.now(timezone(timedelta(hours=7)))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Checking for pending stories to post (current time: {now}, today start: {today_start})")

        for username in self.config.INSTAGRAM_USERNAMES:
            username = username.strip().lstrip('@')
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])

            # Separate stories into two groups:
            # - Stories to post: uploaded before today (taken_at < today_start)
            # - Stories planned for tomorrow: uploaded today (taken_at >= today_start)
            stories_to_post = []
            stories_planned = []

            for story in stories:
                # Only consider unposted stories (no tweet_ids)
                if not story.get('tweet_ids'):
                    taken_at_val = story.get('taken_at')
                    if taken_at_val is None:
                        logger.warning(f"Story {story.get('story_id')} has no taken_at, skipping")
                        continue

                    try:
                        taken_at_int = int(taken_at_val)
                        upload_datetime = datetime.fromtimestamp(taken_at_int, tz=timezone(timedelta(hours=7)))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid taken_at for story {story.get('story_id')}: {e}, skipping")
                        continue

                    # Check if story was uploaded before today or today
                    if upload_datetime < today_start:
                        stories_to_post.append(story)
                    else:
                        stories_planned.append(story)

            if not stories_to_post and not stories_planned:
                logger.info(f"No pending stories for {username}")
                continue

            # Log stories planned for next day
            if stories_planned:
                planned_count = len(stories_planned)
                logger.info(f"Stories uploaded today for {username}: {planned_count} (planned for next day)")
                for story in sorted(stories_planned, key=lambda x: int(x.get('taken_at', 0) or 0)):
                    story_id = story.get('story_id')
                    taken_at_val = story.get('taken_at')
                    upload_datetime = datetime.fromtimestamp(int(taken_at_val), tz=timezone(timedelta(hours=7)))
                    logger.info(f"  - Story {story_id} uploaded at {upload_datetime} (planned for next day)")

            if not stories_to_post:
                logger.info(f"No stories to post for {username} (all uploaded today)")
                continue

            # Sort stories to post by taken_at (oldest first)
            stories_to_post.sort(key=lambda x: int(x.get('taken_at', 0) or 0))

            logger.info(f"Found {len(stories_to_post)} stories to post for {username}")

            # Post each qualifying story
            for story in stories_to_post:
                story_id = story.get('story_id')
                logger.info(f"Processing pending story {story_id} for {username}")
                if self.post_story(username, story_id):
                    total_posted += 1
                else:
                    logger.error(f"Failed to post story {story_id} for {username}")

        logger.info(f"Total stories posted: {total_posted}")
        return total_posted

    def post_pending_stories_daily(self) -> int:
        """Post pending stories grouped by day to avoid spamming.

        Logic:
        1. Get current date in GMT+7 timezone
        2. Find stories with empty tweet_ids AND taken_at before today
        3. Group stories by their upload date
        4. For each day's stories, combine all media into batches of 4
        5. Post each batch as a tweet in a thread (one thread per day)
        6. Mark all stories as posted
        """
        total_posted = 0

        now = datetime.now(timezone(timedelta(hours=7)))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Checking for pending stories to post (current time: {now}, today start: {today_start})")

        for username in self.config.INSTAGRAM_USERNAMES:
            username = username.strip().lstrip('@')
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])

            # Find unposted stories uploaded before today
            stories_to_post = []
            for story in stories:
                if not story.get('tweet_ids'):
                    taken_at_val = story.get('taken_at')
                    if taken_at_val is None:
                        logger.warning(f"Story {story.get('story_id')} has no taken_at, skipping")
                        continue

                    try:
                        taken_at_int = int(taken_at_val)
                        upload_datetime = datetime.fromtimestamp(taken_at_int, tz=timezone(timedelta(hours=7)))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid taken_at for story {story.get('story_id')}: {e}, skipping")
                        continue

                    # Check if story was uploaded before today
                    if upload_datetime < today_start:
                        stories_to_post.append(story)

            if not stories_to_post:
                logger.info(f"No stories to post for {username}")
                continue

            # Group stories by upload date
            stories_by_date = {}
            for story in stories_to_post:
                taken_at_val = int(story.get('taken_at', 0))
                upload_datetime = datetime.fromtimestamp(taken_at_val, tz=timezone(timedelta(hours=7)))
                date_key = upload_datetime.strftime('%Y-%m-%d')
                stories_by_date.setdefault(date_key, []).append(story)

            logger.info(f"Found {len(stories_to_post)} stories to post for {username}, grouped into {len(stories_by_date)} day(s)")

            # Process each day's stories
            for date_key, day_stories in sorted(stories_by_date.items()):
                logger.info(f"Processing stories for {username} from {date_key}: {len(day_stories)} stories")

                # Sort stories by taken_at (oldest first)
                day_stories.sort(key=lambda x: int(x.get('taken_at', 0) or 0))

                # Ensure anchor tweet
                anchor_id = self._ensure_anchor_tweet(username)
                if not anchor_id:
                    logger.error(f"Cannot process day {date_key} for {username} without anchor tweet")
                    continue

                # Collect all media paths from all stories
                all_media_paths = []
                all_media_types = []
                all_story_ids = []

                for story in day_stories:
                    story_id = str(story.get('story_id'))
                    all_story_ids.append(story_id)

                    # Get or prepare media for this story
                    stored_media_paths = story.get('local_media_paths')
                    stored_media_types = story.get('media_types')

                    if not isinstance(stored_media_paths, list):
                        stored_media_paths = []
                    if not isinstance(stored_media_types, list):
                        stored_media_types = []

                    # Backward compatibility
                    if not stored_media_paths:
                        legacy_path = story.get('local_media_path')
                        legacy_type = story.get('media_type', 'image')
                        if legacy_path:
                            stored_media_paths = [legacy_path]
                            stored_media_types = [legacy_type]

                    media_urls = story.get('media_urls') or []

                    if media_urls:
                        # Use URLs as source of truth
                        for idx, url in enumerate(media_urls):
                            media_type = (
                                stored_media_types[idx]
                                if idx < len(stored_media_types) and stored_media_types[idx]
                                else ('video' if 'video' in str(url).lower() else 'image')
                            )

                            existing_path = stored_media_paths[idx] if idx < len(stored_media_paths) else None
                            if existing_path and os.path.exists(existing_path):
                                media_path = existing_path
                            else:
                                media_id = f"{username}_{story_id}_{idx}"
                                media_path = self.media_manager.get_cached_media_path(media_id, media_type)
                                if not media_path:
                                    media_path = self.media_manager.download_media(url, media_id, media_type)

                            if media_path:
                                if media_type == 'image' and not media_path.endswith('_compressed.jpg'):
                                    media_path = self.media_manager.compress_image(media_path)
                                all_media_paths.append(media_path)
                                all_media_types.append(media_type)
                    else:
                        # Use existing paths
                        for path in stored_media_paths:
                            if path and os.path.exists(path):
                                all_media_paths.append(path)
                            if stored_media_types:
                                all_media_types.append(stored_media_types[0])
                            else:
                                all_media_types.append('image')

                if not all_media_paths:
                    logger.warning(f"No media available for day {date_key} for {username}")
                    continue

                logger.info(f"Collected {len(all_media_paths)} media items for day {date_key}")

                # Get caption for the first story (they're all from the same day)
                first_story = day_stories[0]
                taken_at = int(first_story.get('taken_at', 0))
                caption = self.config.get_story_caption(username, taken_at)

                # Post media in batches of 4
                media_batches = [all_media_paths[i:i + 4] for i in range(0, len(all_media_paths), 4)]
                tweet_ids = []
                last_tweet_id = self.archive_manager.get_last_tweet_id(username) or anchor_id

                for idx, batch_paths in enumerate(media_batches):
                    # Upload all media in batch
                    media_ids = []
                    for path in batch_paths:
                        media_id = self.twitter_api.upload_media(path, username=username)
                        if media_id:
                            media_ids.append(media_id)

                    if not media_ids:
                        logger.error(f"Failed to upload media batch {idx + 1} for day {date_key}")
                        continue

                    # Add batch info to caption if there are multiple batches
                    if len(media_batches) > 1:
                        tweet_text = f"{caption}\n({idx + 1}/{len(media_batches)})"
                    else:
                        tweet_text = caption

                    tweet_id = self.twitter_api.post_tweet(
                        text=tweet_text,
                        media_ids=media_ids,
                        reply_to_id=last_tweet_id,
                        username=username,
                    )

                    if not tweet_id:
                        logger.error(f"Failed to post tweet for batch {idx + 1} of day {date_key}")
                        break

                    tweet_ids.append(tweet_id)
                    last_tweet_id = tweet_id
                    logger.info(f"Posted tweet {idx + 1}/{len(media_batches)} for day {date_key}")

                if not tweet_ids:
                    logger.error(f"Failed to post any tweets for day {date_key} for {username}")
                    continue

                # Mark all stories as posted
                for story_id in all_story_ids:
                    self.archive_manager.update_story_tweets(username, story_id, tweet_ids)

                # Update last tweet ID
                self.archive_manager.set_last_tweet_id(username, tweet_ids[-1])

                # Cleanup media files after successful posting
                for media_path in all_media_paths:
                    if media_path and os.path.exists(media_path):
                        self.media_manager.cleanup_media(media_path)

                # Clear local paths in archive
                for story_id in all_story_ids:
                    self.archive_manager.update_story_local_paths(username, story_id, [])

                logger.info(f"Successfully posted day {date_key} for {username} with {len(tweet_ids)} tweet(s) containing {len(all_media_paths)} media items from {len(all_story_ids)} stories")
                total_posted += len(all_story_ids)

        logger.info(f"Total stories posted: {total_posted}")
        return total_posted

    def log_pending_story_count(self) -> int:
        """Log how many pending stories are currently in the archive."""

        total_pending = 0

        for username in self.config.INSTAGRAM_USERNAMES:
            username = username.strip().lstrip('@')
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])

            pending = [s for s in stories if isinstance(s, dict) and not s.get('tweet_ids')]
            count = len(pending)
            logger.info(f"Pending queue for {username}: {count} story(ies)")
            total_pending += count

        logger.info(f"Total stories currently pending: {total_pending}")
        return total_pending

    def print_status(self) -> None:
        stats = self.archive_manager.get_statistics()

        logger.info("=" * 50)
        logger.info("ARCHIVE STATUS")
        logger.info(f"Total Stories (all accounts): {stats.get('total_stories')}")
        logger.info(f"Total Media Items (all accounts): {stats.get('total_media')}")

        accounts = stats.get('accounts') or {}
        for username, account_stats in accounts.items():
            logger.info("-" * 50)
            logger.info(f"Instagram: {username}")
            logger.info(f"  Stories: {account_stats.get('total_stories')}")
            logger.info(f"  Media:   {account_stats.get('total_media')}")
            logger.info(f"  Last check: {account_stats.get('last_check')}")
            logger.info(f"  Anchor tweet: {account_stats.get('anchor_tweet_id')}")
            logger.info(f"  Last tweet:   {account_stats.get('last_tweet_id')}")

        logger.info("=" * 50)
