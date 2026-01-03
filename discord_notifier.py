import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord webhook notifier for sending notifications about various events."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)

    def _send_embed(self, title: str, description: str, color: int, 
                    fields: Optional[List[Dict]] = None, 
                    footer: Optional[str] = None) -> bool:
        """Send a Discord embed message."""
        if not self.enabled:
            return False

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if fields:
            embed["fields"] = fields

        if footer:
            embed["footer"] = {"text": footer}

        payload = {"embeds": [embed]}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            return True
        except RequestException as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def notify_github_action_start(self, workflow_name: str, actor: str, 
                                   repository: str, branch: str) -> bool:
        """Notify when a GitHub Action workflow starts."""
        fields = [
            {"name": "Workflow", "value": workflow_name, "inline": True},
            {"name": "Actor", "value": actor, "inline": True},
            {"name": "Repository", "value": repository, "inline": True},
            {"name": "Branch", "value": branch, "inline": True}
        ]
        
        return self._send_embed(
            title="🚀 GitHub Action Started",
            description=f"Workflow `{workflow_name}` has started execution.",
            color=0x3498db,  # Blue
            fields=fields,
            footer="GitHub Actions"
        )

    def notify_github_action_success(self, workflow_name: str, actor: str,
                                     repository: str, branch: str, 
                                     run_url: str, logs: Optional[str] = None) -> bool:
        """Notify when a GitHub Action workflow succeeds."""
        description = f"Workflow `{workflow_name}` completed successfully."
        if logs:
            description += f"\n```\n{logs[-1000]}\n```"  # Last 1000 chars

        fields = [
            {"name": "Workflow", "value": workflow_name, "inline": True},
            {"name": "Actor", "value": actor, "inline": True},
            {"name": "Repository", "value": repository, "inline": True},
            {"name": "Branch", "value": branch, "inline": True},
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False}
        ]

        if logs and len(logs) > 1000:
            fields.append({"name": "Note", "value": "Logs truncated. Full logs available in GitHub.", "inline": False})

        return self._send_embed(
            title="✅ GitHub Action Success",
            description=description,
            color=0x00ff00,  # Green
            fields=fields,
            footer="GitHub Actions"
        )

    def notify_github_action_failure(self, workflow_name: str, actor: str,
                                     repository: str, branch: str, error: str,
                                     run_url: str, logs: Optional[str] = None) -> bool:
        """Notify when a GitHub Action workflow fails."""
        description = f"Workflow `{workflow_name}` failed with error:\n```\n{error[:500]}\n```"
        if logs:
            description += f"\n**Recent logs:**\n```\n{logs[-1000:]}\n```"

        fields = [
            {"name": "Workflow", "value": workflow_name, "inline": True},
            {"name": "Actor", "value": actor, "inline": True},
            {"name": "Repository", "value": repository, "inline": True},
            {"name": "Branch", "value": branch, "inline": True},
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False}
        ]

        if len(error) > 500:
            fields.append({"name": "Note", "value": "Error message truncated. Full error in GitHub logs.", "inline": False})

        return self._send_embed(
            title="❌ GitHub Action Failed",
            description=description,
            color=0xff0000,  # Red
            fields=fields,
            footer="GitHub Actions"
        )

    def notify_instagram_fetch_success(self, username: str, 
                                       stories_count: int) -> bool:
        """Notify when Instagram stories are successfully fetched."""
        return self._send_embed(
            title="📸 Instagram Stories Fetched",
            description=f"Successfully fetched {stories_count} stories from @{username}",
            color=0x00ff00,  # Green
            fields=[
                {"name": "Username", "value": f"@{username}", "inline": True},
                {"name": "Stories Count", "value": str(stories_count), "inline": True}
            ],
            footer="Instagram API"
        )

    def notify_instagram_fetch_error(self, username: str, error: str,
                                     response_data: Optional[str] = None) -> bool:
        """Notify when Instagram stories fetch fails."""
        description = f"Failed to fetch stories from @{username}\n```\n{error[:800]}\n```"
        
        fields = [{"name": "Username", "value": f"@{username}", "inline": True}]
        
        if response_data:
            fields.append({
                "name": "Response Data", 
                "value": f"```json\n{response_data[:1000]}\n```", 
                "inline": False
            })

        return self._send_embed(
            title="⚠️ Instagram Stories Fetch Failed",
            description=description,
            color=0xffa500,  # Orange
            fields=fields,
            footer="Instagram API"
        )

    def notify_twitter_post_success(self, username: str, 
                                   story_count: int,
                                   tweet_ids: List[str]) -> bool:
        """Notify when Twitter posting is successful."""
        tweet_links = [f"https://twitter.com/user/status/{tid}" for tid in tweet_ids]
        fields = [
            {"name": "Instagram User", "value": f"@{username}", "inline": True},
            {"name": "Stories Posted", "value": str(story_count), "inline": True},
            {"name": "Tweet Count", "value": str(len(tweet_ids)), "inline": True}
        ]

        if tweet_links:
            fields.append({
                "name": "Tweet Links", 
                "value": "\n".join([f"[Tweet {i+1}]({link})" for i, link in enumerate(tweet_links[:5])]), 
                "inline": False
            })

        return self._send_embed(
            title="🐦 Twitter Post Success",
            description=f"Successfully posted {story_count} stories to Twitter",
            color=0x00ff00,  # Green
            fields=fields,
            footer="Twitter API"
        )

    def notify_twitter_post_error(self, username: str, error: str,
                                 status_code: Optional[int] = None,
                                 response_text: Optional[str] = None,
                                 tweet_attempts: Optional[int] = None) -> bool:
        """Notify when Twitter posting fails (especially 403 errors)."""
        description = f"Failed to post stories from @{username} to Twitter"

        fields = [
            {"name": "Username", "value": f"@{username}", "inline": True}
        ]

        if status_code:
            fields.append({"name": "Status Code", "value": str(status_code), "inline": True})
            if status_code == 403:
                description += "\n**⚠️ Authorization Error (403)** - Check Twitter API permissions!"

        if error:
            fields.append({"name": "Error", "value": f"```\n{error[:800]}\n```", "inline": False})

        if response_text:
            fields.append({"name": "Response", "value": f"```json\n{response_text[:1000]}\n```", "inline": False})

        if tweet_attempts:
            fields.append({"name": "Tweet Attempts", "value": str(tweet_attempts), "inline": True})

        color = 0xff0000 if status_code == 403 else 0xffa500  # Red for 403, Orange for others

        return self._send_embed(
            title="❌ Twitter Post Failed",
            description=description,
            color=color,
            fields=fields,
            footer="Twitter API"
        )

    def notify_error(self, component: str, error: str, 
                    context: Optional[str] = None) -> bool:
        """Generic error notification."""
        description = f"Error in {component}: ```\n{error[:1000]}\n```"

        fields = [{"name": "Component", "value": component, "inline": True}]
        
        if context:
            fields.append({"name": "Context", "value": context, "inline": False})

        return self._send_embed(
            title="🔥 Application Error",
            description=description,
            color=0x8b0000,  # Dark red
            fields=fields,
            footer="Application"
        )

    def notify_info(self, title: str, message: str, 
                   fields: Optional[List[Dict]] = None) -> bool:
        """Generic info notification."""
        return self._send_embed(
            title=f"ℹ️ {title}",
            description=message,
            color=0x808080,  # Gray
            fields=fields
        )