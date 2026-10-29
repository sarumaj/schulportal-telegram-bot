"""The bot's web server in production: Telegram's updates arrive as POST requests at
the webhook's path, and everything else (a person opening the address in a browser)
is redirected to the bot in Telegram.

python-telegram-bot's own webhook server answers only the POST requests (405 for the
rest), so this one takes its place, with the Application driven by hand as its
documentation shows for a custom server."""

import asyncio
import logging
import signal
from typing import Any
from urllib.parse import urlparse

from aiohttp import web
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

# The key under which the web application keeps the bot's Application.
APPLICATION_KEY: web.AppKey["Application[Any, Any, Any, Any, Any, Any]"] = web.AppKey("application")


def webhook_path(webhook_url: str) -> str:
    """The path Telegram posts to: that of the webhook's address, / when it has none."""
    return urlparse(webhook_url).path or "/"


def make_web_app(
    application: "Application[Any, Any, Any, Any, Any, Any]",
    path: str,
    bot_url: str,
) -> web.Application:
    """The web application: updates at path (POST), a redirect to bot_url otherwise."""

    async def receive(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except ValueError:
            return web.Response(status=400, text="not an update")
        bot_application = request.app[APPLICATION_KEY]
        await bot_application.update_queue.put(Update.de_json(data=data, bot=bot_application.bot))
        return web.Response()

    async def redirect(_request: web.Request) -> web.Response:
        raise web.HTTPFound(bot_url)

    app = web.Application()
    app[APPLICATION_KEY] = application
    app.router.add_post(path, receive)
    # GET also answers HEAD.
    app.router.add_get("/{tail:.*}", redirect)
    return app


async def run_webhook(
    application: "Application[Any, Any, Any, Any, Any, Any]",
    webhook_url: str,
    port: int,
    bot_url: str,
) -> None:
    """Run the bot behind the web server until SIGTERM or SIGINT: what
    Application.run_webhook does, with post_init and post_shutdown called as it
    would."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    runner = web.AppRunner(make_web_app(application, webhook_path(webhook_url), bot_url))
    async with application:
        if application.post_init:
            await application.post_init(application)
        await application.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
        await application.start()
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", port).start()
        logger.info("listening on port %d, webhook at %s", port, webhook_path(webhook_url))
        try:
            await stop.wait()
        finally:
            await runner.cleanup()
            await application.stop()
            if application.post_shutdown:
                await application.post_shutdown(application)
