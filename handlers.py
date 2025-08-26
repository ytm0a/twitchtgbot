import re
import asyncio
from aiohttp import ClientSession

from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from twitchstalk import (
    run_stalker_for_user,
    remove_stalker_for_user,
    get_user_data,
)

from config import (
    twitch_client_id,
    twitch_access_token
)


def normalize_stream(name):
    name = name.strip().lower().replace(' ', '')
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return name

def normalize_game(name):
    name = name.strip().lower().replace(' ', '').replace('-', '').replace(':','')
    name = re.sub(r'[^A-Za-z0-9]+', '', name)
    return name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await run_stalker_for_user(context, user_id)
    start_message = """Hello, I am bot! I'll send you a notification when your favourite streamer is playing your favourite game!
❗Please enable notifications after you set up your list!
Type /help for more info"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=start_message) # type: ignore


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = """/start - starting message
/stream <streamer> - add streamer you want to follow
/game <category> - add category you want to watch
/list, /ls - list of streamers and categories you want to watch
/check - check status for all streamers
/streamdel <streamer> - remove streamer from your list
/gamedel <category> - remove category from your list
/streamclr - remove all streamers
/gameclr - remove all categories

Don't forget to enable notifications after you set up your list!"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_message)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Type /help for commands list")


async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /stream gorgc
    user_id = update.effective_user.id
    value = normalize_stream(update.message.text.partition(' ')[2])
    if not value:
        response_message = 'nothing to add'
    else:
        streamers, games = get_user_data(context, user_id)
        streamers.add(value)
        context.user_data[user_id] = {'streamers': streamers, 'games': games}
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
        streamers, games = get_user_data(context, user_id)
        games.add(value)
        context.user_data[user_id] = {'streamers': streamers, 'games': games}
        await run_stalker_for_user(context, user_id)
        response_message = f'category \"{value}\" added'
    await update.message.reply_text(response_message)


async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /list
    user_id = update.effective_user.id
    if user_id in context.user_data:
        data = context.user_data.setdefault(user_id, {'streamers': set(), 'games': set()})
        streamers, games = data['streamers'], data['games']
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
    await update.message.reply_text(response_message)


async def streamdel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #streamdel gorgc
    user_id = update.effective_user.id
    value = normalize_stream(update.message.text.partition(' ')[2])
    streamers, games = get_user_data(context, user_id)
    if not value:
        response_message = 'nothing to delete'
    elif value in streamers:
        streamers.remove(value)
        response_message = value + ' deleted'
        if not streamers:
            remove_stalker_for_user(context, user_id)
    else:
        response_message = value + ' was not in your streamer list'
    context.user_data[user_id] = {'streamers': streamers, 'games': games}
    await update.message.reply_text(response_message)


async def gamedel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #gamedel dota2
    user_id = update.effective_user.id
    value = normalize_game(update.message.text.partition(' ')[2])
    streamers, games = get_user_data(context, user_id)
    if not value:
        response_message = 'nothing to delete'
    elif value in games:
        games.remove(value)
        response_message = value + ' deleted'
        if not games:
            remove_stalker_for_user(context, user_id)
    else:
        response_message = value + ' was not in your category list'
    context.user_data[user_id] = {'streamers': streamers, 'games': games}
    await update.message.reply_text(response_message)

async def streamclr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _, games = get_user_data(context, user_id)
    context.user_data[user_id] = {'streamers': set(), 'games': games}
    remove_stalker_for_user(context, user_id)
    await update.message.reply_text("cleared")

async def gameclr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    streams, _ = get_user_data(context, user_id)
    context.user_data[user_id] = {'streamers': streams, 'games': set()}
    remove_stalker_for_user(context, user_id)
    await update.message.reply_text("cleared")


async def get_stream_status(session, streamer_name):
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }
    response_message = ''
    url = 'https://api.twitch.tv/helix/streams?user_login=' + streamer_name
    async with session.get(url=url, headers=headers) as response:
        stream_data = await response.json()
        print(stream_data)
        print(streamer_name)
        if len(stream_data['data']) == 1:
            print(stream_data['data'])
            category = stream_data['data'][0]['game_name']
            response_message = f'{streamer_name} is now streaming in \"{category}\" category'
        else:
            print('not live')
            response_message = f'{streamer_name} is not live'
    return response_message

async def gather_stream_info(streams):
    response_list = []
    async with ClientSession() as session:
        tasks = []
        for streamer_name in streams:
            task = asyncio.create_task(get_stream_status(
                session,
                streamer_name,
            ))
            tasks.append(task)
        response_list = await asyncio.gather(*tasks)
    return response_list


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #/check
    user_id = update.effective_user.id
    streams, _ = get_user_data(context, user_id)
    print(context.user_data)
    print(context.application.user_data)

    if not streams:
        response_message = 'nothing to check'
    else:
        response_list = await gather_stream_info(streams)
        response_message = "\n".join(response_list)

    await update.message.reply_text(response_message)