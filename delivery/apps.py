from django.apps import AppConfig
import signal
import logging
import threading
import os
from django.db import connections
from django.core.cache import cache

log = logging.getLogger(__name__)

shutdown_in_progress = False

def _graceful_shutdown(*args, **kwargs):
    global shutdown_in_progress
    if shutdown_in_progress:
        return
    shutdown_in_progress = True

    try:
        log.info("Graceful shutdown: closing DB connections and cache...")

        # Start force-shutdown timer
        def force_exit():
            log.error("Graceful shutdown did not finish in 10s. Forcing exit.")
            os._exit(1)  # force kill process

        timer = threading.Timer(10.0, force_exit)
        timer.start()

        # Close DB connections
        for conn in connections.all():
            conn.close_if_unusable_or_obsolete()

        # Close cache
        try:
            cache.close()  # LocMem = no-op; Redis closes connection
        except Exception as e:
            log.warning("Error closing cache: %s", e)

        log.info("Graceful shutdown completed.")
        timer.cancel()  # cancel force kill if finished in time

        os._exit(0)  # clean exit
    except Exception as e:
        log.exception("Error during graceful shutdown: %s", e)
        os._exit(1)


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "delivery"

    def ready(self):
        # Register SIGTERM/SIGINT handlers once the app is ready
        signal.signal(signal.SIGTERM, _graceful_shutdown)
        signal.signal(signal.SIGINT, _graceful_shutdown)
