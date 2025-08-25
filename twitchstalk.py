import os
import sys
import asyncio
from aiohttp import ClientSession
from collections import defaultdict

from telegram.ext import (
    filters,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
)

import handlers

import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

STALK_JOB_INTERVAL = 300

in_memory_jobs = {}
previous_category_dict = defaultdict(lambda: defaultdict(str))

twitch_client_id = ''
twitch_access_token = ''

with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitchoath.txt'), 'r') as f:
    twitch_client_id = f.readline().strip()
with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitch_access_token.txt'), 'r') as f:
    twitch_access_token = f.readline().strip()

TOKEN = None
with open(os.path.join(os.path.dirname(sys.argv[0]), 'token.txt'), 'r') as f:
    TOKEN = f.read().strip()


async def startup(application):
    user_data = application.persistence.user_data
    for user_id in user_data:
        context = ContextTypes.DEFAULT_TYPE(application=application)
        await run_stalker_for_user(context, user_id)

def get_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if context.user_data:
        data = context.user_data
        if user_id not in data:
            data[user_id] = {
                'streamers': set(),
                'games': set()
            }
        return data[user_id]['streamers'], data[user_id]['games']
    if user_id in context.application.user_data:
        data = context.application.user_data[user_id]
        if user_id not in data:
            data[user_id] = {
                'streamers': set(),
                'games': set()
                }
        return data[user_id]['streamers'], data[user_id]['games']


async def run_stalker_for_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if user_id in in_memory_jobs:
        return
    
    user_data = context.application.user_data.get(user_id)
    if not user_data:
        return
    
    streamers, games = get_user_data(context, user_id)
    if not streamers or not games:
        return
    
    job = context.job_queue.run_repeating(
        stalk,
        interval=STALK_JOB_INTERVAL,
        first=10,
        data=user_id
    )
    in_memory_jobs[user_id] = job


def remove_stalker_for_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    job = in_memory_jobs.pop(user_id, None)
    if job:
        job.schedule_removal()


async def stalk(context: ContextTypes.DEFAULT_TYPE):
    global twitch_client_id, twitch_access_token
    global previous_category_dict
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }

    user_id = context.job.data
    print("USER_ID", user_id)

    async def send_stream_notifications(streamer_name, headers, user_id, user_categories):
        global previous_category_dict
        async with ClientSession() as session:
            url = 'https://api.twitch.tv/helix/streams?user_login=' + streamer_name
            async with session.get(url=url, headers=headers) as response:
                stream_data = await response.json()
                print(streamer_name)
                if len(stream_data['data']) == 1:
                    print(stream_data['data'])
                else:
                    previous_category_dict[user_id][streamer_name] = ''
                    print('not live')
                if len(stream_data['data']) == 1:
                    orig_category = stream_data['data'][0]['game_name']
                    category = handlers.normalize_game(orig_category)

                    if category in user_categories:
                        if previous_category_dict[user_id][streamer_name] != category:
                            previous_category_dict[user_id][streamer_name] = category
                            response_message = f'{streamer_name} is now streaming in \"{orig_category}\" category!'
                            print(response_message)
                            response_message += f' twitch.tv/{streamer_name}'
                            await context.bot.send_message(chat_id=user_id, text=response_message)
    print('************')
    tasks = []
    print(context.application.user_data)

    streams, games = get_user_data(context, user_id)
    for streamer_name in streams:
        tasks.append(asyncio.create_task(send_stream_notifications(streamer_name, headers, user_id, games)))
    for task in tasks:
        await task


if __name__ == '__main__':
    my_persistence = PicklePersistence(
        filepath=os.path.join(os.path.dirname(sys.argv[0]), 'data')
    )
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence=my_persistence)
        .post_init(startup)
        .build()
    )

    job_queue = application.job_queue

    application.add_handler(CommandHandler('start', handlers.start))

    application.add_handler(CommandHandler('help', handlers.help))

    application.add_handler(CommandHandler('stream', handlers.stream))

    application.add_handler(CommandHandler('game', handlers.game))

    application.add_handler(CommandHandler('streamdel', handlers.streamdel))

    application.add_handler(CommandHandler('gamedel', handlers.gamedel))

    application.add_handler(CommandHandler('list', handlers.list))

    application.add_handler(CommandHandler('ls', handlers.list))

    application.add_handler(CommandHandler('check', handlers.check))

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.echo))

    application.add_handler(CommandHandler('streamclr', handlers.streamclr))

    application.add_handler(CommandHandler('gameclr', handlers.gameclr))

    application.run_polling()
