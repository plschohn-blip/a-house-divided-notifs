"""
AHD Alert Bot — main entry point.
Starts the Discord bot and the background polling loop.
"""

import asyncio
import logging
import os

import discord
from discord.ext import commands, tasks

from db import Database
from poller import Poller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ahd-bot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
db = Database("data/subscriptions.db")


@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")
    poll_loop.start()


# ── Slash commands ────────────────────────────────────────────────────────────

@bot.tree.command(name="subscribe", description="Subscribe to A House Divided alerts")
@discord.app_commands.describe(
    alert_type="What to watch: elections | legislation | market | news | characters",
    country="Country code, e.g. US, GB, DE (leave blank for all)",
    keyword="Optional keyword filter for news/legislation",
)
async def subscribe(
    interaction: discord.Interaction,
    alert_type: str,
    country: str = "",
    keyword: str = "",
):
    valid = {"elections", "legislation", "market", "news", "characters"}
    if alert_type.lower() not in valid:
        await interaction.response.send_message(
            f"❌ Unknown alert type `{alert_type}`. Choose from: {', '.join(sorted(valid))}",
            ephemeral=True,
        )
        return

    db.add_subscription(
        user_id=interaction.user.id,
        alert_type=alert_type.lower(),
        country=country.upper() if country else "",
        keyword=keyword.lower() if keyword else "",
    )

    parts = [f"**{alert_type}**"]
    if country:
        parts.append(f"country: **{country.upper()}**")
    if keyword:
        parts.append(f"keyword: **{keyword}**")

    await interaction.response.send_message(
        f"✅ Subscribed to {' | '.join(parts)}. You'll receive DMs when matching events occur.",
        ephemeral=True,
    )


@bot.tree.command(name="unsubscribe", description="Remove an A House Divided alert subscription")
@discord.app_commands.describe(
    alert_type="Alert type to remove: elections | legislation | market | news | characters | all",
)
async def unsubscribe(interaction: discord.Interaction, alert_type: str):
    if alert_type.lower() == "all":
        db.remove_all_subscriptions(interaction.user.id)
        await interaction.response.send_message("✅ Removed all your AHD subscriptions.", ephemeral=True)
    else:
        db.remove_subscription(interaction.user.id, alert_type.lower())
        await interaction.response.send_message(
            f"✅ Removed your **{alert_type}** subscription.", ephemeral=True
        )


@bot.tree.command(name="myalerts", description="List your current AHD alert subscriptions")
async def myalerts(interaction: discord.Interaction):
    subs = db.get_subscriptions(interaction.user.id)
    if not subs:
        await interaction.response.send_message(
            "You have no active subscriptions. Use `/subscribe` to add one.", ephemeral=True
        )
        return

    lines = []
    for s in subs:
        parts = [f"**{s['alert_type']}**"]
        if s["country"]:
            parts.append(f"country: {s['country']}")
        if s["keyword"]:
            parts.append(f"keyword: `{s['keyword']}`")
        lines.append("• " + " | ".join(parts))

    await interaction.response.send_message(
        "**Your AHD subscriptions:**\n" + "\n".join(lines), ephemeral=True
    )


@bot.tree.command(name="ahd", description="About this bot")
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="A House Divided Alert Bot",
        description=(
            "Get DM notifications for in-game events in A House Divided.\n\n"
            "**Commands:**\n"
            "`/subscribe` — add an alert\n"
            "`/unsubscribe` — remove an alert\n"
            "`/myalerts` — see your subscriptions\n\n"
            "**Alert types:** elections, legislation, market, news, characters\n\n"
            "**Example:**\n"
            "`/subscribe alert_type:elections country:US`\n"
            "`/subscribe alert_type:news keyword:scandal`"
        ),
        color=0x5865F2,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Background polling loop ───────────────────────────────────────────────────

@tasks.loop(minutes=1)
async def poll_loop():
    try:
        poller = Poller(db, bot)
        await poller.run()
    except Exception as e:
        log.error(f"Polling error: {e}", exc_info=True)


@poll_loop.before_loop
async def before_poll():
    await bot.wait_until_ready()


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable not set")
    bot.run(token)
