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
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
    portal = PortalBot("", "")
    application.add_handler(portal.getHandler())

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
