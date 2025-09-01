import asyncio, time, os
from aiohttp import ClientSession
from collections import defaultdict

from config import (
    BASE_DIR,
    twitch_client_id,
    twitch_client_secret,
)

from utils import normalize_game

previous_category_dict = defaultdict(lambda: defaultdict(str))
twitch_access_token = ''
token_expires_at = 0.0

try:
    with open(os.path.join(BASE_DIR, 'twitch_access_token.txt'), 'r') as f:
        twitch_access_token = f.readline().strip()
        token_expires_at = float(f.readline().strip())
except Exception as e:
    print('Failed to read twitch_access_token', e)

async def get_new_token():
    global twitch_access_token, token_expires_in
    body = {
        'client_id': twitch_client_id,
        'client_secret': twitch_client_secret,
        "grant_type": 'client_credentials'
    }
    url = 'https://id.twitch.tv/oauth2/token'
    async with asyncio.Lock():
        try:
            async with ClientSession() as session:
                async with session.post(url=url, data=body) as r:
                    data = await r.json();
                    access_token = data['access_token']
                    expires_in = float(data['expires_in'])
                    twitch_access_token = access_token
                    token_expires_at = time.time() + expires_in
                    try:
                        with open(os.path.join(BASE_DIR, 'twitch_access_token.txt'), 'w') as f:
                            f.write(str(twitch_access_token)+'\n')
                            f.write(str(token_expires_at))
                    except Exception as e:
                        print('Failed to write in twitch_access_token.txt', e)
        except Exception as e:
            print('Error updating token')
            raise e

async def check_twitch_access_token():
    global twitch_access_token, token_expires_at
    if not twitch_access_token or (token_expires_at < time.time() + 300):
        await get_new_token()
    return twitch_access_token

async def get_fresh_category_from_stream(session, streamer_name, user_id, user_categories):
    global previous_category_dict, twitch_access_token
    twitch_access_token = await check_twitch_access_token()
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }
    url = 'https://api.twitch.tv/helix/streams?user_login=' + streamer_name

    try:
        async with session.get(url=url, headers=headers) as response:
            stream_data = await response.json()
            print(streamer_name)
            if len(stream_data['data']) != 1:
                previous_category_dict[user_id][streamer_name] = ''
                print('not live')
            else:
                print(stream_data['data'])
                orig_category = stream_data['data'][0]['game_name']
                category = normalize_game(orig_category)

                if category in user_categories:
                    if previous_category_dict[user_id][streamer_name] != category:
                        previous_category_dict[user_id][streamer_name] = category
                        response_message = f'{streamer_name} is now streaming in \"{orig_category}\" category!'
                        print(response_message)
                        response_message += f' twitch.tv/{streamer_name}'
                        return response_message
    except Exception as exc:
        return f'{streamer_name} - failed to get streamer info, errorcode: {str(exc)}'


async def gather_stream_notifications(streams, user_id, user_categories):
    response_list = []
    async with ClientSession() as session:
        tasks = []
        for streamer_name in streams:
            task = asyncio.create_task(get_fresh_category_from_stream(
                session,
                streamer_name,
                user_id,
                user_categories
                ))
            tasks.append(task)
        response_list = await asyncio.gather(*tasks)
    return response_list


async def get_stream_status(session, streamer_name, user_id):
    global twitch_access_token
    twitch_access_token = await check_twitch_access_token()
    headers = {
        'Client-ID': twitch_client_id,
        'Authorization': 'Bearer ' + twitch_access_token
    }
    response_message = ''
    url = 'https://api.twitch.tv/helix/streams?user_login=' + streamer_name
    try:
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
                previous_category_dict[user_id][streamer_name] = ''
                response_message = f'{streamer_name} is not live'
        return response_message
    except Exception as exc:
        return f'{streamer_name} - failed to get streamer info, errorcode: {str(exc)}'


async def gather_stream_info(streams, user_id):
    response_list = []
    async with ClientSession() as session:
        tasks = []
        for streamer_name in streams:
            task = asyncio.create_task(get_stream_status(
                session,
                streamer_name,
                user_id,
            ))
            tasks.append(task)
        response_list = await asyncio.gather(*tasks)
    return response_list