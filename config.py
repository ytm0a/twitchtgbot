import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, '.env'))

twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not (twitch_client_secret and twitch_client_id and TOKEN):
    raise ValueError("Failed to load configuration")