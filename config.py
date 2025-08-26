import os, sys

twitch_client_id = ''
twitch_access_token = ''

with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitchoath.txt'), 'r') as f:
    twitch_client_id = f.readline().strip()
with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitch_access_token.txt'), 'r') as f:
    twitch_access_token = f.readline().strip()

TOKEN = None
with open(os.path.join(os.path.dirname(sys.argv[0]), 'token.txt'), 'r') as f:
    TOKEN = f.read().strip()