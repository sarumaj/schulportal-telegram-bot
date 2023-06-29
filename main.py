import logging
import os
from telegram.ext import ApplicationBuilder
from portalbot import PortalBot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)

TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
    application.add_handler(PortalBot("", "").getHandler())
    application.run_polling()
