# schulportal-telegram-bot

Telegram Bot for Maciej (best brother whom one can wish to have 😁).

Schulportal is a collaboration platform used by many schools in Hessia, Germany.
This bot should ease the access to the portal and expose features like "Vertretungsplan" or undone homework reminders.

Bot is registered as [t.me/SchulportalBot](http://t.me/SchulportalBot).

In production the bot receives Telegram's updates through a webhook (`src/webhook.py`); opening its address in a browser leads to [t.me/SchulportalBot](https://t.me/SchulportalBot) (`TELEGRAM_BOT_URL`).
