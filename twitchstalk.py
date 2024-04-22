import os, sys, requests
from collections import defaultdict

from telegram import Update
from telegram.ext import filters, Application, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, PicklePersistence, StringRegexHandler

import logging

stalk_running = False

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

previous_category = defaultdict(str)

def run_stalker(context: ContextTypes.DEFAULT_TYPE):
    global stalk_running
    if not stalk_running:
        context.job_queue.run_repeating(stalk, interval=180, first=10, data = context.user_data)
        stalk_running = True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    text_too_long = """Hello, I am bot! I'll send you a notification when your favourite streamer is playing your favourite game!
Plese enable notifications after you set up your list!
Type /help for more info"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_too_long) # type: ignore

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    text_too_long = """/start - starting message
/stream <streamer> - add streamer you want to follow
/game <category> - add category you want to watch
/list, /ls - list of streamers and categories you want to watch
/check - check status for all streamers
/streamdel <streamer> - remove streamer from your list
/gamedel <category> - remove category from your list

Don't forget to enable notifications after you set up your list!"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_too_long)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Type /help for commands list")

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    # /stream gorgc
    user = update.message.from_user
    value = update.message.text.partition(' ')[2].strip().lower()
    if not value:
        response_message = 'nothing to add'
    else:
        streamers, games = context.user_data.get(user['id'], [set(), set()])
        streamers.add(value)
        context.user_data[user['id']] = (streamers, games)
        response_message = f'streamer \"{value}\" added'
    await update.message.reply_text(response_message)

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    # /game dota2
    user = update.message.from_user
    value = update.message.text.partition(' ')[2].strip().lower()
    if not value:
        response_message = 'nothing to add'
    else:
        streamers, games = context.user_data.get(user['id'], [set(), set()])
        games.add(value)
        context.user_data[user['id']] = (streamers, games)
        response_message = f'category \"{value}\" added'
    await update.message.reply_text(response_message)

async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    # /list
    user = update.message.from_user
    if user['id'] in context.user_data:
        streamers, games = context.user_data[user['id']]
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
    run_stalker(context)
    #streamdel gorgc
    user = update.message.from_user
    value = update.message.text.partition(' ')[2].lower()
    #print(user, user['id'], value)
    streamers, games = context.user_data.get(user['id'], [set(), set()])
    if not value:
        response_message = 'nothing to delete'
    elif value in streamers:
        streamers.remove(value)
        response_message = value + ' deleted'
    else:
        response_message = value + ' was not in your streamer list'
    context.user_data[user['id']] = (streamers, games)
    await update.message.reply_text(response_message)

async def gamedel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    #gamedel dota2
    user = update.message.from_user
    value = update.message.text.partition(' ')[2].lower()
    #print(user, user['id'], value)
    streamers, games = context.user_data.get(user['id'], [set(), set()])
    if not value:
        response_message = 'nothing to add'
    elif value in games:
        games.remove(value)
        response_message = value + ' deleted'
    else:
        response_message = value + ' was not in your category list'
    context.user_data[user['id']] = (streamers, games)
    await update.message.reply_text(response_message)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
    #/check
    global twitch_client_id, twitch_access_token
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }

    user = update.message.from_user
    stream_set, _ = context.user_data[user['id']]
    if not stream_set:
        response_message = 'nothing to check'
    else:
        response_list = []
        for streamer_name in stream_set:
            stream = requests.get('https://api.twitch.tv/helix/streams?user_login=' + streamer_name, headers=headers)
            stream_data = stream.json()
            print(streamer_name)
            
            if len(stream_data['data']) == 1:
                category = stream_data['data'][0]['game_name'].lower()
                response_list.append(f'{streamer_name} is now streaming in \"{category}\" category')
            else:
                response_list.append(f'{streamer_name} is not live')
        response_message = "\n".join(response_list)
    await update.message.reply_text(response_message)

#async def stalk_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
#    global stalk_running
#    if not stalk_running:
#        context.job_queue.run_repeating(stalk, interval=60, first=3, data = context.user_data)
#        stalk_running = True

async def stalk(context: ContextTypes.DEFAULT_TYPE):
    global twitch_client_id, twitch_access_token
    global previous_category
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }
    print('************')
    print('JOB DONE')

    user_data = context.job.data
    for user_id in user_data:
        stream_set, game_set = user_data[user_id]
        for streamer_name in stream_set:
            stream = requests.get('https://api.twitch.tv/helix/streams?user_login=' + streamer_name, headers=headers)
            stream_data = stream.json()
            print(streamer_name)
            if len(stream_data['data']) == 1:
                print(stream_data['data'])
            else:
                print('not live')
            if len(stream_data['data']) == 1:
                category = stream_data['data'][0]['game_name'].lower()
                if category in game_set:
                    if previous_category[streamer_name] == category:
                        continue
                    else:
                        previous_category[streamer_name] = category
                        response_message = f'{streamer_name} is now streaming in \"{category}\" category!'
                        print(response_message)
                        response_message += f'twitch.tv/{streamer_name}'
                        await context.bot.send_message(chat_id=user_id, text=response_message)

'''
async def streamclr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)

async def gameclr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)

async def clearall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_stalker(context)
'''


if __name__ == '__main__':
    my_persistence = PicklePersistence(filepath=os.path.join(os.path.dirname(sys.argv[0]), 'data'))
    application = ApplicationBuilder().token(TOKEN).persistence(persistence=my_persistence).build()

    job_queue = application.job_queue

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)

    stream_handler = CommandHandler('stream', stream)
    application.add_handler(stream_handler)

    game_handler = CommandHandler('game', game)
    application.add_handler(game_handler)

    delstream_handler = CommandHandler('streamdel', streamdel)
    application.add_handler(delstream_handler)

    delgame_handler = CommandHandler('gamedel', gamedel)
    application.add_handler(delgame_handler)

    list_handler = CommandHandler('list', list)
    application.add_handler(list_handler)

    ls_handler = CommandHandler('ls', list)
    application.add_handler(ls_handler)

    check_handler = CommandHandler('check', check)
    application.add_handler(check_handler)

    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    application.add_handler(echo_handler)

    application.run_polling()
 
    '''streamclr_handler = CommandHandler('streamclr', streamclr)
    application.add_handler(streamclr_handler)

    gameclr_handler = CommandHandler('gameclr', gameclr)
    application.add_handler(gameclr_handler)

    clearall_handler = CommandHandler('clearall', clearall)
    application.add_handler(clearall_handler)'''
    

