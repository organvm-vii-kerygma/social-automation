"""Discord integration module for community channel automation.

Manages webhook-based publishing to Discord channels with
formatted embeds and role mentions.
"""

from __future__ import annotations
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

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url
        self._sent: list[dict[str, Any]] = []

    def send_message(self, content: str) -> dict[str, Any]:
        result = {"content": content, "webhook": self.webhook_url, "id": len(self._sent) + 1}
        self._sent.append(result)
        return result

    def send_embed(self, embed: DiscordEmbed, content: str = "") -> dict[str, Any]:
        result = {
            "content": content,
            "embeds": [embed.to_payload()],
            "webhook": self.webhook_url,
            "id": len(self._sent) + 1,
        }
        self._sent.append(result)
        return result

    @property
    def messages_sent(self) -> int:
        return len(self._sent)
