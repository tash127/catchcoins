import logging

from django.db.models import F
from django.db.models.signals import post_save

from bd_models.models import BallInstance, Player
from settings.models import settings

REWARD = 1
UID = "catchcoins_give_coin"

log = logging.getLogger("catchcoins")


def give_coin(sender, instance, created, **kwargs):
    try:
        if not created or instance.spawned_time is None:
            return
        if not settings.currency_name:
            return
        Player.objects.filter(pk=instance.player_id).update(money=F("money") + REWARD)
    except Exception:
        log.exception("Could not give catch reward")


async def setup(bot):
    post_save.connect(give_coin, sender=BallInstance, dispatch_uid=UID)


async def teardown(bot):
    post_save.disconnect(sender=BallInstance, dispatch_uid=UID)
