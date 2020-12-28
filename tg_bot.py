from telegram.ext import Updater
import telegram
import os
import logging
from telegram.ext import CommandHandler, MessageHandler, Filters
import telegram.ext
import asyncio
import datetime
import os
from os import path as op
from functools import partial

from bot.commands import start, game, dual, leaderboard, bot_help, normal_messages, error_logger, stats, standing

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                     level=logging.INFO,
                     datefmt='%m-%d %H:%M:%S',
                     filename=op.join(op.dirname(__file__), "log.txt"),
                     filemode="a")

token = os.getenv("TG_TOKEN")

if not os.path.exists(os.path.join(os.path.dirname(__file__), "persistent_storage")):
    os.mkdir(os.path.join(os.path.dirname(__file__), "persistent_storage"))
if not os.path.exists(os.path.join(os.path.dirname(__file__), "message_history")):
    os.mkdir(os.path.join(os.path.dirname(__file__), "message_history"))

updater = Updater(token=token, workers=1)
dispatcher = updater.dispatcher

# QOL Could add a custom dispatcher, that would check the correct ranking for the message
dispatcher.add_handler(MessageHandler(~Filters.command, normal_messages, channel_post_updates=True, edited_updates=True, message_updates=True))
dispatcher.add_handler(CommandHandler('start', partial(start, log_update=True)))
dispatcher.add_handler(CommandHandler('singles', partial(game, log_update=True)))
dispatcher.add_handler(CommandHandler('duals', partial(dual, log_update=True)))
dispatcher.add_handler(CommandHandler('board', partial(leaderboard, log_update=True)))
dispatcher.add_handler(CommandHandler('standing', partial(standing, log_update=True)))
dispatcher.add_handler(CommandHandler('stats', partial(stats, log_update=True)))
dispatcher.add_handler(CommandHandler('help', partial(bot_help, log_update=True)))
# QOL The Telegram provides an API for authentication on websites. This would allow to run a webserver, through which the
# admins could manage the rankings of the chat. Alternatively, could also be used to display different rankings.

dispatcher.add_error_handler(error_logger)

updater.start_polling()
