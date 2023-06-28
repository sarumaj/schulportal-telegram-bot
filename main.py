import logging
import os
import datetime
from aiohttp import ClientSession
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import filters, Application, ApplicationBuilder, ContextTypes, ConversationHandler, CommandHandler, MessageHandler
from typing import Any
from enum import Enum
from portal import Portal

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)

TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]

class Interaction(Enum):
    CHOOSING_LOCATION, CHOOSING_SCHOOL, TYPING_USERNAME, TYPING_PASSWORD, LOOP = range(5)

def slice(x: list[Any], row_size: int):
    return [x[i:i + row_size] for i in range(0, len(x), row_size)]

class PortalBot(Portal):
    def __init__(self):
        super().__init__("", "", session=None)

    async def ask_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        self.school_list = await self.list()
        await update.message.reply_text(
            "Hi! My name is Schulportal Bot. What school are you attending to? "
            "May I visit you there? Please, choose the location of your school first:",
            reply_markup=ReplyKeyboardMarkup(
                slice(
                    sorted(
                        list(
                            {
                                school["city"] for school in self.school_list
                            }
                        )
                    )
                    , 3
                ),
                one_time_keyboard=True
            ),
        )

        return Interaction.CHOOSING_LOCATION.value

    async def ask_school(self , update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        text = update.message.text
        context.user_data["location"] = text
        await update.message.reply_text(
            f"Cool! I love {text}! Now, you made me curious about your school! "
            "Please, tell me what school are you attending to:",
            reply_markup=ReplyKeyboardMarkup(
                slice(
                    sorted(
                        list(
                            {
                                school["school"] for school in self.school_list
                                if text.casefold() in str(school["city"]).casefold()
                                or str(school["city"]).casefold() in text.casefold()
                            }
                        )
                    )
                    , 3
                ),
                one_time_keyboard=True
            ),
        )

        return Interaction.CHOOSING_SCHOOL.value

    async def ask_username(self , update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        text = update.message.text
        context.user_data["school"] = text
        await update.message.reply_text(
            f"Your go to {text}? How cool! I am sure, we have common buddies there! "
            "If you like, I can check the Schulportal on your behalf, if you like! "
            "I would need to know, what is your USERNAME:"
        )

        return Interaction.TYPING_USERNAME.value

    async def ask_password(self , update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        text = update.message.text
        context.user_data["username"] = text
        await update.message.reply_text(
            "Thank you! You can trust me, I will keep your data secure! "
            "Then, I would need to know, what is your PASSWORD:"
        )

        return Interaction.TYPING_PASSWORD.value

    async def monitor(self , update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        text = update.message.text
        user_data = context.user_data
        user_data["password"] = text
        await update.message.reply_text(
            "Thank you! Now, you are set and ready! "
            "I will keep track of your Schulportal on your behalf!"
        )

        location = str(user_data["location"]).casefold()
        school = str(user_data["school"]).casefold()
        user_data["data-id"] = next(filter(
            lambda x: any(
                str(x["city"]).casefold() in location,
                location in str(x["city"]).casefold()
            ) and any(
                str(x["school"]).casefold() in school,
                school in str(x["school"]).casefold()
            ),
            self.school_list
        ), {"data-id", "5114"})["data-id"]

        job_queue = context.job_queue
        job_queue.run_repeating(self.loop, 5, user_id=update.effective_user.id, data=update)

        return Interaction.LOOP.value

    async def loop(self, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        job = context.job
        update = job.data
        async with Portal(user_data["username"], user_data["password"]) as portal:
            portal.login(user_data["data_id"])
            await update.message.reply_text(
                "Hurray, you are signed in!"
            )

    async def done(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_data = context.user_data
        user_data.clear()

        job_queue = context.job_queue
        job_queue.stop(False)

        await update.message.reply_text(
            "I am sad to see you going, but I am looking forward to seeing you again! "
            "Take care!",
            reply_markup=ReplyKeyboardRemove(),
        )

        
        return ConversationHandler.END


if __name__ == "__main__":
    application= ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
    portal = PortalBot()
    doneFilter = filters.Regex("^(Done)$")
    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("start", portal.ask_location)],
            states={
                Interaction.CHOOSING_LOCATION.value: [
                    MessageHandler(filters.TEXT & ~(doneFilter | filters.COMMAND), portal.ask_school),
                ],
                Interaction.CHOOSING_SCHOOL.value: [
                    MessageHandler(filters.TEXT & ~(doneFilter | filters.COMMAND), portal.ask_username),
                ],
                Interaction.TYPING_USERNAME.value: [
                    MessageHandler(filters.TEXT & ~(doneFilter | filters.COMMAND), portal.ask_password),
                ],
                Interaction.TYPING_PASSWORD.value: [
                    MessageHandler(filters.TEXT & ~(doneFilter | filters.COMMAND), portal.monitor),
                ],
                Interaction.LOOP.value: [],
            },
            fallbacks=[
                MessageHandler(doneFilter, portal.done),
                CommandHandler("end", portal.done)
            ]
        )
    )
    application.run_polling()
