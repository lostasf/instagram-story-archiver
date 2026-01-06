import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord webhook notifier for sending notifications about various events.

    Supports split webhooks:
    - success/info channel
    - failure/error channel

    Falls back to the legacy DISCORD_WEBHOOK_URL if split webhooks are not set.
    """

    def __init__(
        self,
        success_webhook_url: Optional[str] = None,
        failure_webhook_url: Optional[str] = None,
    ):
        legacy = os.getenv("DISCORD_WEBHOOK_URL")

        self.success_webhook_url = (
            success_webhook_url
            or os.getenv("DISCORD_WEBHOOK_SUCCESS_URL")
            or legacy
        )
        self.failure_webhook_url = (
            failure_webhook_url
            or os.getenv("DISCORD_WEBHOOK_FAILURE_URL")
            or legacy
        )

        self.success_enabled = bool(self.success_webhook_url)
        self.failure_enabled = bool(self.failure_webhook_url)

    def _send_embed(
        self,
        *,
        webhook_url: Optional[str],
        title: str,
        description: str,
        color: int,
        fields: Optional[List[Dict]] = None,
        footer: Optional[str] = None,
    ) -> bool:
        if not webhook_url:
            return False

        embed: Dict[str, object] = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if fields:
            embed["fields"] = fields

        if footer:
            embed["footer"] = {"text": footer}

        payload = {"embeds": [embed]}

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            return True
        except RequestException as e:
            logger.error(f"Failed to send Discord notification: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Discord API Response: {e.response.text}")
            return False

    def _send_success_embed(
        self,
        *,
        title: str,
        description: str,
        color: int,
        fields: Optional[List[Dict]] = None,
        footer: Optional[str] = None,
    ) -> bool:
        return self._send_embed(
            webhook_url=self.success_webhook_url,
            title=title,
            description=description,
            color=color,
            fields=fields,
            footer=footer,
        )

    def _send_failure_embed(
        self,
        *,
        title: str,
        description: str,
        color: int,
        fields: Optional[List[Dict]] = None,
        footer: Optional[str] = None,
    ) -> bool:
        return self._send_embed(
            webhook_url=self.failure_webhook_url,
            title=title,
            description=description,
            color=color,
            fields=fields,
            footer=footer,
        )

    def notify_github_action_start(self, workflow_name: str, actor: str, repository: str, branch: str) -> bool:
        fields = [
            {"name": "Workflow", "value": workflow_name, "inline": True},
            {"name": "Actor", "value": actor, "inline": True},
            {"name": "Repository", "value": repository, "inline": True},
            {"name": "Branch", "value": branch, "inline": True},
        ]

        return self._send_success_embed(
            title="🚀 GitHub Action Started",
            description=f"Workflow `{workflow_name}` has started execution.",
            color=0x3498DB,
            fields=fields,
            footer="GitHub Actions",
        )

    def notify_github_action_success(
        self,
        workflow_name: str,
        actor: str,
        repository: str,
        branch: str,
        run_url: str,
        logs: Optional[str] = None,
    ) -> bool:
        description = f"Workflow `{workflow_name}` completed successfully."
        if logs:
            description += f"\n```\n{logs[-1000:]}\n```"

        fields = [
            {"name": "Workflow", "value": workflow_name, "inline": True},
            {"name": "Actor", "value": actor, "inline": True},
            {"name": "Repository", "value": repository, "inline": True},
            {"name": "Branch", "value": branch, "inline": True},
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False},
        ]

        if logs and len(logs) > 1000:
            fields.append(
                {
                    "name": "Note",
                    "value": "Logs truncated. Full logs available in GitHub.",
                    "inline": False,
                }
            )

        return self._send_success_embed(
            title="✅ GitHub Action Success",
            description=description,
            color=0x00FF00,
            fields=fields,
            footer="GitHub Actions",
        )

    def notify_github_action_failure(
        self,
        workflow_name: str,
        actor: str,
        repository: str,
        branch: str,
        error: str,
        run_url: str,
        logs: Optional[str] = None,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ) -> bool:
        description = f"Workflow `{workflow_name}` failed with error:\n```\n{error[:500]}\n```"
        if logs:
            description += f"\n**Recent logs:**\n```\n{logs[-1000:]}\n```"

        fields = [
            {"name": "Workflow", "value": workflow_name, "inline": True},
            {"name": "Actor", "value": actor, "inline": True},
            {"name": "Repository", "value": repository, "inline": True},
            {"name": "Branch", "value": branch, "inline": True},
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False},
        ]

        if status_code is not None:
            fields.append({"name": "HTTP Status", "value": str(status_code), "inline": True})

        if response_text:
            fields.append(
                {
                    "name": "Response",
                    "value": f"```json\n{response_text[:1000]}\n```",
                    "inline": False,
                }
            )

        if len(error) > 500:
            fields.append(
                {
                    "name": "Note",
                    "value": "Error message truncated. Full error in GitHub logs.",
                    "inline": False,
                }
            )

        return self._send_failure_embed(
            title="❌ GitHub Action Failed",
            description=description,
            color=0xFF0000,
            fields=fields,
            footer="GitHub Actions",
        )

    def notify_fetch_only_summary(
        self,
        *,
        workflow_name: str,
        actor: str,
        repository: str,
        branch: str,
        run_url: str,
        per_user: Dict[str, Dict[str, int]],
    ) -> bool:
        fields: List[Dict] = [
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False}
        ]

        for username, summary in per_user.items():
            fetched = summary.get("fetched", 0)
            new_archived = summary.get("new_archived", 0)
            already_archived = summary.get("already_archived", 0)
            already_posted = summary.get("already_posted", 0)
            fetch_failed = summary.get("fetch_failed", 0)

            value_parts = [
                f"Active stories fetched: **{fetched}**",
                f"New archived: **{new_archived}**",
            ]

            if fetch_failed:
                value_parts.append("⚠️ Fetch failed for this account (see failure channel for details)")

            if already_archived:
                suffix = f" (already posted: {already_posted})" if already_posted else ""
                value_parts.append(f"Skipped (already in archive): **{already_archived}**{suffix}")
            elif already_posted:
                value_parts.append(f"Already posted (still active on IG): **{already_posted}**")

            fields.append(
                {
                    "name": f"@{username}",
                    "value": "\n".join(value_parts),
                    "inline": False,
                }
            )

        return self._send_success_embed(
            title="✅ Fetch-only run summary",
            description=(
                f"Workflow `{workflow_name}` finished.\n"
                f"Repo: `{repository}` • Branch: `{branch}` • Actor: `{actor}`"
            ),
            color=0x00FF00,
            fields=fields,
            footer="GitHub Actions",
        )

    def notify_post_daily_summary(
        self,
        *,
        workflow_name: str,
        actor: str,
        repository: str,
        branch: str,
        run_url: str,
        per_user: Dict[str, Dict[str, int]],
    ) -> bool:
        fields: List[Dict] = [
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False}
        ]

        for username, summary in per_user.items():
            posted_now = summary.get("posted_now", 0)
            archived_total = summary.get("archived_total", 0)
            already_posted = summary.get("already_posted", 0)

            value_parts = [
                f"New stories posted: **{posted_now}**",
                f"Stories archived (total): **{archived_total}**",
            ]

            if already_posted:
                value_parts.append(f"Already posted before this run: **{already_posted}**")

            fields.append(
                {
                    "name": f"@{username}",
                    "value": "\n".join(value_parts),
                    "inline": False,
                }
            )

        return self._send_success_embed(
            title="✅ Post-daily run summary",
            description=(
                f"Workflow `{workflow_name}` finished.\n"
                f"Repo: `{repository}` • Branch: `{branch}` • Actor: `{actor}`"
            ),
            color=0x00FF00,
            fields=fields,
            footer="GitHub Actions",
        )

    def notify_cleanup_summary(
        self,
        *,
        workflow_name: str,
        actor: str,
        repository: str,
        branch: str,
        run_url: str,
        cleaned_count: int,
    ) -> bool:
        fields: List[Dict] = [
            {"name": "Run URL", "value": f"[View Run]({run_url})", "inline": False},
            {"name": "Files Cleaned", "value": str(cleaned_count), "inline": True},
        ]

        return self._send_success_embed(
            title="✅ Media Cache Cleanup Summary",
            description=(
                f"Workflow `{workflow_name}` finished.\n"
                f"Repo: `{repository}` • Branch: `{branch}` • Actor: `{actor}`"
            ),
            color=0x00FF00,
            fields=fields,
            footer="GitHub Actions",
        )

    def notify_instagram_fetch_error(
        self,
        username: str,
        error: str,
        status_code: Optional[int] = None,
        response_data: Optional[str] = None,
    ) -> bool:
        description = f"Failed to fetch stories from @{username}\n```\n{error[:800]}\n```"

        fields: List[Dict] = [{"name": "Username", "value": f"@{username}", "inline": True}]

        if status_code is not None:
            fields.append({"name": "HTTP Status", "value": str(status_code), "inline": True})

        if response_data:
            fields.append(
                {
                    "name": "Response",
                    "value": f"```json\n{response_data[:1000]}\n```",
                    "inline": False,
                }
            )

        return self._send_failure_embed(
            title="⚠️ Instagram Stories Fetch Failed",
            description=description,
            color=0xFFA500,
            fields=fields,
            footer="Instagram API",
        )

    def notify_twitter_post_success(self, username: str, story_count: int, tweet_ids: List[str]) -> bool:
        tweet_links = [f"https://twitter.com/user/status/{tid}" for tid in tweet_ids]
        fields: List[Dict] = [
            {"name": "Instagram User", "value": f"@{username}", "inline": True},
            {"name": "Stories Posted", "value": str(story_count), "inline": True},
            {"name": "Tweet Count", "value": str(len(tweet_ids)), "inline": True},
        ]

        if tweet_links:
            fields.append(
                {
                    "name": "Tweet Links",
                    "value": "\n".join([f"[Tweet {i + 1}]({link})" for i, link in enumerate(tweet_links[:5])]),
                    "inline": False,
                }
            )

        return self._send_success_embed(
            title="🐦 Twitter Post Success",
            description=f"Successfully posted {story_count} stories to Twitter",
            color=0x00FF00,
            fields=fields,
            footer="Twitter API",
        )

    def notify_twitter_post_error(
        self,
        username: str,
        error: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        tweet_attempts: Optional[int] = None,
    ) -> bool:
        description = f"Failed to post stories from @{username} to Twitter"

        fields: List[Dict] = [{"name": "Username", "value": f"@{username}", "inline": True}]

        if status_code is not None:
            fields.append({"name": "HTTP Status", "value": str(status_code), "inline": True})
            if status_code == 403:
                description += "\n**⚠️ Authorization Error (403)** - Check Twitter API permissions!"

        if error:
            fields.append({"name": "Error", "value": f"```\n{error[:800]}\n```", "inline": False})

        if response_text:
            fields.append({"name": "Response", "value": f"```json\n{response_text[:1000]}\n```", "inline": False})

        if tweet_attempts is not None:
            fields.append({"name": "Tweet Attempts", "value": str(tweet_attempts), "inline": True})

        color = 0xFF0000 if status_code == 403 else 0xFFA500

        return self._send_failure_embed(
            title="❌ Twitter Post Failed",
            description=description,
            color=color,
            fields=fields,
            footer="Twitter API",
        )

    def notify_error(self, component: str, error: str, context: Optional[str] = None) -> bool:
        description = f"Error in {component}: ```\n{error[:1000]}\n```"

        fields: List[Dict] = [{"name": "Component", "value": component, "inline": True}]
        if context:
            fields.append({"name": "Context", "value": context, "inline": False})

        return self._send_failure_embed(
            title="🔥 Application Error",
            description=description,
            color=0x8B0000,
            fields=fields,
            footer="Application",
        )

    def notify_info(self, title: str, message: str, fields: Optional[List[Dict]] = None) -> bool:
        return self._send_success_embed(
            title=f"ℹ️ {title}",
            description=message,
            color=0x808080,
            fields=fields,
        )
