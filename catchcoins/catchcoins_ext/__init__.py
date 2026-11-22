import asyncio
import logging
import random
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from django.db.models import F
from django.db.models.signals import post_save
from django.utils import timezone

from bd_models.models import BallInstance, Player
from settings.models import settings

CATCH_REWARD = 1
DAILY_MIN = 10
DAILY_MAX = 30
DAILY_COOLDOWN = timedelta(hours=24)
DAILY_KEY = "catchcoins_last_daily"
UID = "catchcoins_give_coin"

log = logging.getLogger("catchcoins")


def give_coin(sender, instance, created, **kwargs):
    try:
        if not created or instance.spawned_time is None:
            return
        if not settings.currency_name:
            return
        Player.objects.filter(pk=instance.player_id).update(money=F("money") + CATCH_REWARD)
    except Exception:
        log.exception("Could not give catch reward")


class Scudettini(commands.GroupCog, name="scudettini"):
    """Currency commands."""

    def __init__(self, bot):
        self.bot = bot
        self.locks: dict[int, asyncio.Lock] = {}

    @app_commands.command()
    async def daily(self, interaction: discord.Interaction):
        """Claim your free daily reward."""
        if not settings.currency_name:
            await interaction.response.send_message("Currency is not enabled.", ephemeral=True)
            return

        lock = self.locks.setdefault(interaction.user.id, asyncio.Lock())
        async with lock:
            player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
            data = player.extra_data or {}
            now = timezone.now()

            last = None
            if data.get(DAILY_KEY):
                try:
                    last = datetime.fromisoformat(data[DAILY_KEY])
                except ValueError:
                    last = None

            if last is not None and now - last < DAILY_COOLDOWN:
                ready = int((last + DAILY_COOLDOWN).timestamp())
                await interaction.response.send_message(
                    f"You already claimed your daily reward. Come back <t:{ready}:R>.",
                    ephemeral=True,
                )
                return

            data[DAILY_KEY] = now.isoformat()
            player.extra_data = data
            await player.asave(update_fields=["extra_data"])
            reward = random.randint(DAILY_MIN, DAILY_MAX)
            await player.add_money(reward)

        await interaction.response.send_message(f"You claimed {reward} {settings.currency_name}!")


async def setup(bot):
    post_save.connect(give_coin, sender=BallInstance, dispatch_uid=UID)
    await bot.add_cog(Scudettini(bot))


async def teardown(bot):
    post_save.disconnect(sender=BallInstance, dispatch_uid=UID)
