import os
import sys
import re
import asyncio
from aiohttp import ClientSession
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    filters,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
)

import logging

STALK_JOB_INTERVAL = 300

in_memory_jobs = {}
previous_category_dict = defaultdict(str)

twitch_client_id = ''
twitch_access_token = ''

with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitchoath.txt'), 'r') as f:
    twitch_client_id = f.readline().strip()
with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitch_access_token.txt'), 'r') as f:
    twitch_access_token = f.readline().strip()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = None
with open(os.path.join(os.path.dirname(sys.argv[0]), 'token.txt'), 'r') as f:
    TOKEN = f.read().strip()


async def run_stalker_for_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):

    if user_id in in_memory_jobs:
        return
    
    user_data = context.application.user_data.get(user_id)
    if not user_data:
        return

    streamers, games = user_data.get(user_id, (set(), set()))
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


async def startup(application):
    user_data = application.persistence.user_data

    for user_id in user_data:
        context = ContextTypes.DEFAULT_TYPE(application=application)
        await run_stalker_for_user(context, user_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await run_stalker_for_user(context, user_id)
    text_too_long = """Hello, I am bot! I'll send you a notification when your favourite streamer is playing your favourite game!
❗Please enable notifications after you set up your list!
Type /help for more info"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_too_long) # type: ignore

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_too_long = """/start - starting message
/stream <streamer> - add streamer you want to follow
/game <category> - add category you want to watch
/list, /ls - list of streamers and categories you want to watch
/check - check status for all streamers
/streamdel <streamer> - remove streamer from your list
/gamedel <category> - remove category from your list
/streamclr - remove all streamers
/gameclr - remove all categories

Don't forget to enable notifications after you set up your list!"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_too_long)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Type /help for commands list")


def normalize_stream(name):
    name = name.strip().lower().replace(' ', '')
    name = re.sub('[^A-Za-z0-9]+', '', name)
    return name

def normalize_game(name):
    name = name.strip().lower().replace(' ', '').replace('-', '').replace(':','')
    name = re.sub('[^A-Za-z0-9]+', '', name)
    return name

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /stream gorgc
    user_id = update.effective_user.id
    value = normalize_stream(update.message.text.partition(' ')[2])
    if not value:
        response_message = 'nothing to add'
    else:
        streamers, games = context.user_data.get(user_id, [set(), set()])
        streamers.add(value)
        context.user_data[user_id] = (streamers, games)
        await run_stalker_for_user(context, user_id)
        response_message = f'streamer \"{value}\" added'
    await update.message.reply_text(response_message)


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /game dota2
    user_id = update.effective_user.id
    value = normalize_game(update.message.text.partition(' ')[2])
    if not value:
        response_message = 'nothing to add'
    else:
        streamers, games = context.user_data.get(user_id, [set(), set()])
        games.add(value)
        context.user_data[user_id] = (streamers, games)
        await run_stalker_for_user(context, user_id)
        response_message = f'category \"{value}\" added'
    await update.message.reply_text(response_message)


async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /list
    user_id = update.effective_user.id
    if user_id in context.user_data:
        streamers, games = context.user_data[user_id]
        if not streamers:
            response_message1 = 'Streamers: no streamers added'
        else:
            response_message1 = f"Streamers: {', '.join(streamers)}"
        if not games:
            response_message2 = 'Categories: no categories added'
        else:
            response_message2 = f"Categories: {', '.join(games)}"
        response_message = response_message1 + '\n' + response_message2
    else:
        response_message = 'Your list is empty! Try adding streamers with /stream <streamer> command'
    #print(user, user['id'], value)
    await update.message.reply_text(response_message)


async def streamdel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #streamdel gorgc
    user_id = update.effective_user.id
    value = normalize_stream(update.message.text.partition(' ')[2])
    #print(user, user_id, value)
    streamers, games = context.user_data.get(user_id, [set(), set()])
    if not value:
        response_message = 'nothing to delete'
    elif value in streamers:
        streamers.remove(value)
        response_message = value + ' deleted'
        if not streamers:
            remove_stalker_for_user(context, user_id)
    else:
        response_message = value + ' was not in your streamer list'
    context.user_data[user_id] = (streamers, games)
    await update.message.reply_text(response_message)


async def gamedel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #gamedel dota2
    user_id = update.effective_user.id
    value = normalize_game(update.message.text.partition(' ')[2])
    streamers, games = context.user_data.get(user_id, [set(), set()])
    if not value:
        response_message = 'nothing to add'
    elif value in games:
        games.remove(value)
        response_message = value + ' deleted'
        if not games:
            remove_stalker_for_user(context, user_id)
    else:
        response_message = value + ' was not in your category list'
    context.user_data[user_id] = (streamers, games)
    await update.message.reply_text(response_message)

async def streamclr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _, games = context.user_data.get(user_id, [set(), set()])
    context.user_data[user_id] = (set(), games)
    remove_stalker_for_user(context, user_id)
    await update.message.reply_text("cleared")

async def gameclr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    streams, _ = context.user_data.get(user_id, [set(), set()])
    context.user_data[user_id] = (streams, set())
    remove_stalker_for_user(context, user_id)
    await update.message.reply_text("cleared")


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #/check
    global twitch_client_id, twitch_access_token
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }

    user_id = update.effective_user.id
    stream_set, _ = context.user_data[user_id]

    if not stream_set:
        response_message = 'nothing to check'
    else:
        response_list = []

        async def get_stream_info(streamer_name, headers, response_list):
            async with ClientSession() as session:
                url = 'https://api.twitch.tv/helix/streams?user_login=' + streamer_name
                async with session.get(url=url, headers=headers) as response:
                    stream_data = await response.json()
                    print(stream_data)
                    print(streamer_name)
                    if len(stream_data['data']) == 1:
                        print(stream_data['data'])
                    else:
                        print('not live')
                    if len(stream_data['data']) == 1:
                        category = stream_data['data'][0]['game_name']
                        response_list.append(f'{streamer_name} is now streaming in \"{category}\" category')
                    else:
                        response_list.append(f'{streamer_name} is not live')
        
        tasks = []
        for streamer_name in stream_set:
            tasks.append(asyncio.create_task(get_stream_info(streamer_name, headers, response_list)))
        for task in tasks:
            await task
        response_message = "\n".join(response_list)

    await update.message.reply_text(response_message)


async def stalk(context: ContextTypes.DEFAULT_TYPE):
    global twitch_client_id, twitch_access_token
    global previous_category_dict
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }

    user_id = context.job.data
    print("USER_ID", user_id)

    async def send_stream_notifications(streamer_name, headers, user_id):
        global previous_category_dict
        async with ClientSession() as session:
            url = 'https://api.twitch.tv/helix/streams?user_login=' + streamer_name
            async with session.get(url=url, headers=headers) as response:
                stream_data = await response.json()
                print(streamer_name)
                if len(stream_data['data']) == 1:
                    print(stream_data['data'])
                else:
                    previous_category_dict[streamer_name] = ''
                    print('not live')
                if len(stream_data['data']) == 1:
                    orig_category = stream_data['data'][0]['game_name']
                    category = normalize_game(orig_category)

                    if category in game_set:
                        if previous_category_dict[streamer_name] != category:
                            previous_category_dict[streamer_name] = category
                            response_message = f'{streamer_name} is now streaming in \"{orig_category}\" category!'
                            print(response_message)
                            response_message += f' twitch.tv/{streamer_name}'
                            await context.bot.send_message(chat_id=user_id, text=response_message)
    print('************')
    tasks = []
    print(context.application.user_data)

    stream_set, game_set = context.application.user_data[user_id][user_id]
    for streamer_name in stream_set:
        tasks.append(asyncio.create_task(send_stream_notifications(streamer_name, headers, user_id)))
    for task in tasks:
        await task
 
'''

async def clearall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
'''


if __name__ == '__main__':
    my_persistence = PicklePersistence(filepath=os.path.join(os.path.dirname(sys.argv[0]), 'data'))
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence=my_persistence)
        .post_init(startup)
        .build()
    )

    job_queue = application.job_queue

    application.add_handler(CommandHandler('start', start))

    application.add_handler(CommandHandler('help', help))

    application.add_handler(CommandHandler('stream', stream))

    application.add_handler(CommandHandler('game', game))

    application.add_handler(CommandHandler('streamdel', streamdel))

    application.add_handler(CommandHandler('gamedel', gamedel))

    application.add_handler(CommandHandler('list', list))

    application.add_handler(CommandHandler('ls', list))

    application.add_handler(CommandHandler('check', check))

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    application.add_handler(CommandHandler('streamclr', streamclr))

    application.add_handler(CommandHandler('gameclr', gameclr))

    application.run_polling()
    
    '''

    clearall_handler = CommandHandler('clearall', clearall)
    application.add_handler(clearall_handler)'''