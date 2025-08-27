import asyncio
from aiohttp import ClientSession
from collections import defaultdict

from config import (
    twitch_client_id,
    twitch_access_token,
)

from utils import normalize_game

previous_category_dict = defaultdict(lambda: defaultdict(str))


async def get_fresh_category_from_stream(session, streamer_name, user_id, user_categories):
    global previous_category_dict
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