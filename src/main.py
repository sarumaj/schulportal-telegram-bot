import asyncio
import logging
import os
from typing import Any, cast

from telegram.ext import Application, ApplicationBuilder, ConversationHandler

from config import APP_RUN_MODE, HEROKU_WEB_URL, TELEGRAM_API_TOKEN, TELEGRAM_BOT_URL
from portalbot import PortalBot
from webhook import run_webhook

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)


def main():
    portal = PortalBot("", "")

    async def _post_init(application: Application[Any, Any, Any, Any, Any, Any]) -> None:
        # Populate school_list inside a running event loop via the official
        # post_init hook, avoiding RuntimeError: no running event loop.
        await portal.post_init()
        handler = cast(
            ConversationHandler[Any],
            portal.getHandler(),  # type: ignore[reportUnknownArgumentType]
        )
        application.add_handler(handler)

    async def _post_shutdown(application: Application[Any, Any, Any, Any, Any, Any]) -> None:
        # Close the aiohttp session cleanly on shutdown.
        await portal.logout()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_API_TOKEN)
        .post_init(_post_init)  # type: ignore[reportUnknownMemberType]
        .post_shutdown(_post_shutdown)
        .build()
    )

    if APP_RUN_MODE != "PROD":
        portal.logger.log(logging.WARN, "running locally")
        application.run_polling()

    else:
        portal.logger.log(logging.INFO, "running remotely")
        # Updates at the webhook's path; a browser opening the address is sent to
        # the bot in Telegram.
        asyncio.run(run_webhook(
            application,
            webhook_url=HEROKU_WEB_URL,
            port=int(os.environ.get("PORT", "8443")),
            bot_url=TELEGRAM_BOT_URL,
        ))


if __name__ == "__main__":
    main()
