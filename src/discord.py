"""Discord integration module for community channel automation.

Manages webhook-based publishing to Discord channels with
formatted embeds and role mentions.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscordEmbed:
    title: str
    description: str
    url: str = ""
    color: int = 0x5865F2
    fields: list[dict[str, str]] = field(default_factory=list)

    def add_field(self, name: str, value: str, inline: bool = False) -> None:
        self.fields.append({"name": name, "value": value, "inline": str(inline).lower()})

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": self.title,
            "description": self.description,
            "color": self.color,
        }
        if self.url:
            payload["url"] = self.url
        if self.fields:
            payload["fields"] = self.fields
        return payload


class DiscordWebhook:
    """Sends formatted messages to Discord channels via webhooks."""

    def __init__(self, webhook_url: str, live: bool = False) -> None:
        self.webhook_url = webhook_url
        self._live = live
        self._sent: list[dict[str, Any]] = []

    def _send_to_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a payload to the Discord webhook via HTTP POST."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                if body:
                    return json.loads(body)
                return {"ok": True, "status": resp.status}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Discord webhook error {exc.code}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Discord connection error: {exc.reason}"
            ) from exc

    def send_message(self, content: str) -> dict[str, Any]:
        result = {"content": content, "webhook": self.webhook_url, "id": len(self._sent) + 1}

        if self._live:
            api_result = self._send_to_webhook({"content": content})
            result["api_response"] = api_result

        self._sent.append(result)
        return result

    def send_embed(self, embed: DiscordEmbed, content: str = "") -> dict[str, Any]:
        result = {
            "content": content,
            "embeds": [embed.to_payload()],
            "webhook": self.webhook_url,
            "id": len(self._sent) + 1,
        }

        if self._live:
            payload: dict[str, Any] = {"embeds": [embed.to_payload()]}
            if content:
                payload["content"] = content
            api_result = self._send_to_webhook(payload)
            result["api_response"] = api_result

        self._sent.append(result)
        return result

    @property
    def messages_sent(self) -> int:
        return len(self._sent)
