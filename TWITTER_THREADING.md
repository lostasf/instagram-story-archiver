# Twitter Threading Structure

## Overview

The archiver now uses a **threaded anchor post** structure on Twitter. This creates a continuous thread where all Instagram stories are posted as replies to previous posts.

## Structure

### 1. Anchor Post (Created Once)
- **Text**: "Gendis JKT48 Instagram Story"
- **Created**: Automatically on first story archive
- **Purpose**: Acts as the permanent starting point for all future story posts
- **Stored in**: `archive.json` as `anchor_tweet_id`

### 2. Story Posts (Threaded Replies)
- **Format**: Each story is posted as a reply to the previous post
- **Text**: Formatted datetime from the story's `taken_at` field
  - Example: "Thursday, 02 November 2025 14:48"
- **Media**: Single image or video from the Instagram story
- **Threading**: Each post replies to the last posted story

### Example Thread Structure

```
Tweet 1 (Anchor): "Gendis JKT48 Instagram Story"
  ↓ (reply)
Tweet 2: "Monday, 15 January 2024 10:30" + [media]
  ↓ (reply)
Tweet 3: "Monday, 15 January 2024 18:45" + [media]
  ↓ (reply)
Tweet 4: "Tuesday, 16 January 2024 09:15" + [media]
  ↓ (reply)
... and so on
```

## Archive Data Structure

The `archive.json` file now tracks:

```json
{
  "anchor_tweet_id": "1234567890123456789",
  "last_tweet_id": "9876543210987654321",
  "archived_stories": [
    {
      "story_id": "...",
      "archived_at": "...",
      "taken_at": 1662479754,
      "media_count": 1,
      "tweet_ids": ["..."],
      "media_urls": ["..."]
    }
  ]
}
```

### Key Fields
- `anchor_tweet_id`: ID of the first "Gendis JKT48 Instagram Story" tweet
- `last_tweet_id`: ID of the most recent story tweet (used for next reply)
- `taken_at`: Unix timestamp when the story was posted on Instagram

## Benefits

1. **Single Continuous Thread**: All stories are in one long thread, easy to browse
2. **Chronological Order**: Stories are processed in order of posting time
3. **No Thread Spam**: Only one anchor post ever created
4. **Clean Format**: Simple datetime + media format for each story
5. **Thread Continuity**: Each new check continues the existing thread

## Technical Details

### Process Flow

1. Check if anchor tweet exists in `archive.json`
2. If not, create anchor tweet and store its ID
3. For each new Instagram story:
   - Download media
   - Format the `taken_at` timestamp to readable datetime
   - Upload media to Twitter
   - Post as reply to `last_tweet_id`
   - Update `last_tweet_id` with the new tweet ID
4. Save archive state

### Datetime Formatting

Unix timestamp → Human-readable format:
- Input: `1662479754` (Unix timestamp)
- Output: `"Thursday, 06 September 2022 14:29"`
- Format: `"%A, %d %B %Y %H:%M"`

## Migration from Old Format

If you have an existing archive that used the old format (threads per story), the new system will:
1. Create a new anchor tweet on the next run
2. Start a fresh threaded structure
3. Continue archiving new stories in the new format
4. Old tweet threads remain intact but separate

## Considerations

- Twitter has a limit on thread depth, but this is very high (hundreds of replies)
- The anchor tweet should not be deleted or the thread will break
- If `last_tweet_id` is lost, the system will fall back to replying to the anchor tweet
