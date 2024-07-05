[![build_and_release](https://github.com/sarumaj/schulportal-telegram-bot/actions/workflows/deploy.yml/badge.svg)](https://github.com/sarumaj/schulportal-telegram-bot/actions/workflows/deploy.yml)
[![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/sarumaj/schulportal-telegram-bot)](https://github.com/sarumaj/schulportal-telegram-bot/blob/main/requirements.txt)

---

# schulportal-telegram-bot

Telegram Bot for Maciej (best brother whom one can wish to have 😁).

Schulportal is a collaboration platform used by many schools in Hessia, Germany.
This bot should ease the access to the portal and expose features like "Vertretungsplan" or undone homework reminders.

Bot is registered as [t.me/SchulportalBot](http://t.me/SchulportalBot).

## Deployment on Heroku

Requires Heroku CLI and docker installed.

```bash
heroku login
docker ps
heroku container:login
heroku container:push web
heroku container:release web
```
