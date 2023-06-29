import logging
import re
import json
import hashlib
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import filters, ContextTypes, ConversationHandler, CommandHandler, MessageHandler
from typing import Any, Optional
from aiohttp import ClientSession
from enum import Enum
import asyncio
from expiringdict import ExpiringDict

from portal import Portal
from errors import LoginFailed


class ConversationStates(Enum):
    CHOOSING_LOCATION = 1
    CHOOSING_SCHOOL = 3
    TYPING_USERNAME = 5
    TYPING_PASSWORD = 6
    LOOP = 7


def to2d(x: list[Any], row_size: int):
    """
    Slices a list into smaller sublists of the specified row size.

    Args:
        x: The list to be sliced.
        row_size: The size of each sublist.

    Returns:
        A list of sublists.
    """
    return [x[i:i + row_size] for i in range(0, len(x), row_size)]


class PortalBot(Portal):
    """
    A bot that interacts with the Schulportal.

    This class extends the `Portal` class and implements the Telegram bot functionality for interacting with users.

    Args:
        username (str): The username for the Schulportal.
        password (str): The password for the Schulportal.
        session (Optional[ClientSession]): The `httpx` ClientSession to use for making HTTP requests. Defaults to None.

    Attributes:
        logger: The logger object for logging bot-related information.
        cache: Internal in-memory expiring cache.
    """

    def __init__(self, username: str, password: str, *, session: Optional[ClientSession] = None):
        super().__init__(username, password, session=session)
        self.logger = logging.getLogger(PortalBot.__class__.__name__)
        self.cache = ExpiringDict(max_len=100, max_age_seconds=3600)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.post_init())

    async def post_init(self):
        self.school_list = await self.list()

    def getHandler(self) -> ConversationHandler:
        """
        Returns the ConversationHandler for handling the bot's conversation flow.

        Returns:
            ConversationHandler: The ConversationHandler object.
        """
        doneFilter = filters.Regex("^(Done)$")
        doneOrCommand = doneFilter | filters.COMMAND
        textAndNotdoneOrCommand = filters.TEXT & ~doneOrCommand
        return ConversationHandler(
            entry_points=[CommandHandler("start", self.ask_location)],
            states={
                ConversationStates.CHOOSING_LOCATION.value: [
                    MessageHandler(textAndNotdoneOrCommand,
                                   self.verify_location),
                ],
                ConversationStates.CHOOSING_SCHOOL.value: [
                    MessageHandler(textAndNotdoneOrCommand,
                                   self.verify_school),
                ],
                ConversationStates.TYPING_USERNAME.value: [
                    MessageHandler(textAndNotdoneOrCommand,
                                   self.ask_password),
                ],
                ConversationStates.TYPING_PASSWORD.value: [
                    MessageHandler(textAndNotdoneOrCommand,
                                   self.verify_username_and_password),
                ],
                ConversationStates.LOOP.value: [],
            },
            fallbacks=[
                MessageHandler(doneFilter, self.done),
                CommandHandler("end", self.done)
            ]
        )

    async def ask_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: Optional[str] = None) -> int:
        """
        Asks the user to choose the location of their school.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.
            message: Optional message to send to the user.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "ask location")
        if message is None:
            message = (
                "Hi! My name is <b>Schulportal Bot</b>. What school are you attending to? "
                "May I visit you there? Please, choose the <b>location</b> of your school first:"
            )
        await update.message.reply_html(
            message,
            reply_markup=ReplyKeyboardMarkup(
                to2d(
                    sorted(
                        list(
                            {
                                school["city"] for school in self.school_list
                            }
                        )
                    ), 3
                ),
                one_time_keyboard=True
            ),
        )

        return ConversationStates.CHOOSING_LOCATION.value

    async def verify_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Verifies the chosen location of the school.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "verify_location")
        text = update.message.text
        regex = re.compile("^(%s)$" % "|".join({
            re.escape(school["city"]) for school in self.school_list
        }))
        if regex.match(text) is not None:
            self.logger.log(logging.INFO, "location verified")
            context.user_data["location"] = text
            return await self.ask_school(update, context)

        else:
            return await self.ask_location(
                update,
                context,
                f"Opsala! I did not find a matching location for <i>{text}</i>! Please, try again!"
            )

    async def ask_school(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: Optional[str] = None) -> int:
        """
        Asks the user to choose their school.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.
            message: Optional message to send to the user.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "ask_school")
        location = context.user_data["location"]
        if message is None:
            message = (
                f"Cool! I love <b>{location}</b>! Now, you made me curious about your school! "
                "Please, tell me what school are you attending to:"
            )
        await update.message.reply_html(
            message,
            reply_markup=ReplyKeyboardMarkup(
                to2d(
                    sorted(
                        list(
                            {
                                school["school"] for school in self.school_list
                                if location.casefold() in str(school["city"]).casefold()
                                or str(school["city"]).casefold() in location.casefold()
                            }
                        )
                    ), 3
                ),
                one_time_keyboard=True
            ),
        )

        return ConversationStates.CHOOSING_SCHOOL.value

    async def verify_school(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Verifies the chosen school.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "verify_school")
        location = context.user_data["location"]
        text = update.message.text
        regex = re.compile("^(%s)$" % "|".join({
            re.escape(school["school"]) for school in self.school_list
            if location.casefold() in str(school["city"]).casefold()
            or str(school["city"]).casefold() in location.casefold()
        }))
        if regex.match(text) is not None:
            self.logger.log(logging.INFO, "school verified")
            context.user_data["school"] = text
            return await self.ask_username(update, context)

        else:
            return await self.ask_school(
                update,
                context,
                f"Oh no! I did not find any school like <i>{text}</i>! Please, try again!"
            )

    async def ask_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: Optional[str] = None) -> int:
        """
        Asks the user to enter their username.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.
            message: Optional message to send to the user.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "ask_username")
        school = context.user_data["school"]
        if message is None:
            message = (
                f"Your go to <b>{school}</b>? How cool! I am sure, we have common buddies there! "
                "If you like, I can check the Schulportal on your behalf! "
                "I would like to ask you to enter your <b>username</b>:"
            )
        await update.message.reply_html(message, reply_markup=ReplyKeyboardRemove())

        return ConversationStates.TYPING_USERNAME.value

    async def ask_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Asks the user to enter their password.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "ask_password")
        context.user_data["username"] = update.message.text.strip()
        await update.message.delete()
        await update.message.reply_html(
            "Thank you! Then, I would like to ask you to enter your <b>password</b>:"
        )

        return ConversationStates.TYPING_PASSWORD.value

    async def verify_username_and_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Verifies the entered username and password.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "verify_username_and_password")

        context.user_data["password"] = update.message.text.strip()
        await update.message.delete()

        location = str(context.user_data["location"]).casefold()
        school = str(context.user_data["school"]).casefold()
        context.user_data["data-id"] = next(filter(
            lambda x: any([
                str(x["city"]).casefold() in location,
                location in str(x["city"]).casefold()
            ]) and any([
                str(x["school"]).casefold() in school,
                school in str(x["school"]).casefold()
            ]),
            self.school_list
        ), {"data-id", ""})["data-id"]
        context.user_data["user-id"] = update.effective_user.id

        async with Portal(context.user_data["username"], context.user_data["password"]) as portal:
            try:
                await portal.login(context.user_data["data-id"])
            except LoginFailed as ex:
                self.logger.log(logging.WARNING, *ex.args)
                return await self.ask_username(
                    update,
                    context,
                    "Bad news! Your credentials were invalid! Please try again! Enter your username, please:"
                )
            else:
                return await self.monitor(update, context)

    async def monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Monitors the Schulportal for updates.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.

        Returns:
            The next conversation state.
        """
        self.logger.log(logging.INFO, "monitor")
        await update.message.reply_html(
            "Thank you! Now, you are set and ready! "
            "I will keep track of your Schulportal on your behalf every minute!"
        )

        if not context.job_queue.scheduler.running:
            context.job_queue.scheduler.start()
        context.job_queue.run_once(
            self.loop,
            0,
            user_id=context.user_data["user-id"],
            data=update,
            name=("loopback_of_%s" % context.user_data["user-id"])
        )
        context.job_queue.run_repeating(
            self.loop,
            60,
            user_id=context.user_data["user-id"],
            data=update,
            name=("loopback_of_%s" % context.user_data["user-id"])
        )

        return ConversationStates.LOOP.value

    async def loop(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Performs the loop operation to check for updates.

        Args:
            context: The context object from Telegram.
        """

        user_id = context.user_data["user-id"]
        update = context.job.data
        async with Portal(context.user_data["username"], context.user_data["password"]) as portal:
            await portal.login(context.user_data["data-id"])
            todo = await portal.get_undone_homework()
            if len(todo) == 0:
                await update.message.reply_html(
                    "Hurray! There is no pending homework left!"
                )
            else:
                for task in todo:
                    md5_hash = hashlib.md5(
                        json.dumps(
                            task,
                            sort_keys=True
                        ).encode('utf-8')
                    ).hexdigest()
                    if f"{user_id}.{md5_hash}" in self.cache:
                        continue
                    self.cache[f"{user_id}.{md5_hash}"] = task
                    await update.message.reply_html(
                        (
                            f"#{md5_hash}\n"
                            "You have open homework on following topic <b>{topic}</b>, "
                            "assigned by your teacher <b>{teacher}</b> in <b>{subject}</b>. "
                            "The due date is <b>{date}</b>, and that is what you are supposed to do:\n\n<strong>{content}</strong>"
                        ).format(**task)
                    )

    async def done(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Ends conversation.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.

        Returns:
            The next terminating conversation state.
        """
        context.user_data.clear()

        [
            job.schedule_removal() for job in context.job_queue.get_jobs_by_name(
                f"loopback_of_{update.effective_user.id}"
            )
        ]

        await update.message.reply_html(
            "I am sad to see you going, but I am looking forward to seeing you again! "
            "Take care!",
            reply_markup=ReplyKeyboardRemove(),
        )

        return ConversationHandler.END
