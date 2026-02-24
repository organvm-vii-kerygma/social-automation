"""Tests for the discord module."""
from kerygma_social.discord import DiscordWebhook, DiscordEmbed


def test_send_message():
    wh = DiscordWebhook("https://discord.com/api/webhooks/test")
    result = wh.send_message("Hello!")
    assert result["content"] == "Hello!"
    assert wh.messages_sent == 1


def test_send_embed():
    wh = DiscordWebhook("https://discord.com/api/webhooks/test")
    embed = DiscordEmbed(title="Test", description="Desc", url="https://example.com")
    result = wh.send_embed(embed)
    assert len(result["embeds"]) == 1
    assert result["embeds"][0]["title"] == "Test"


def test_embed_add_field():
    embed = DiscordEmbed(title="T", description="D")
    embed.add_field("key", "value", inline=True)
    assert len(embed.fields) == 1
    payload = embed.to_payload()
    assert "fields" in payload


def test_embed_field_inline_is_bool():
    """Discord API expects inline as a boolean, not a string."""
    embed = DiscordEmbed(title="T", description="D")
    embed.add_field("key", "value", inline=True)
    assert embed.fields[0]["inline"] is True
    embed.add_field("key2", "value2", inline=False)
    assert embed.fields[1]["inline"] is False
