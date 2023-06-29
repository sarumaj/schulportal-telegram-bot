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


def run_locally(application: Application):
    application.run_polling()


def run_on_heroku(application: Application):
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", "8443")),
        webhook_url=HEROKU_WEB_URL,
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
    portal = PortalBot("", "")
    application.add_handler(portal.getHandler())
    if APP_RUN_MODE != "PROD":
        portal.logger.log(logging.WARN, "running locally")
        run_locally(application)
    else:
        portal.logger.log(logging.INFO, "running remotely")
        run_on_heroku(application)
