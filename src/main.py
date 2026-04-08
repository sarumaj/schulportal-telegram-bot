import logging
import os
from telegram.ext import ApplicationBuilder, Application
from portalbot import PortalBot
from config import (
    APP_RUN_MODE,
    HEROKU_WEB_URL,
    TELEGRAM_API_TOKEN
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)


def main():
    portal = PortalBot("", "")

    async def _post_init(application: Application) -> None:
        # Populate school_list inside a running event loop via the official
        # post_init hook, avoiding RuntimeError: no running event loop.
        await portal.post_init()
        application.add_handler(portal.getHandler())

    async def _post_shutdown(application: Application) -> None:
        # Close the aiohttp session cleanly on shutdown.
        await portal.logout()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_API_TOKEN)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    if APP_RUN_MODE != "PROD":
        portal.logger.log(logging.WARN, "running locally")
        application.run_polling()

    else:
        portal.logger.log(logging.INFO, "running remotely")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", "8443")),
            webhook_url=HEROKU_WEB_URL,
        )


if __name__ == "__main__":
    main()
