import requests, os, sys

client_id = ''
client_secret = ''

#get a new access token
if __name__ == '__main__':
    with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitchoath.txt'), 'r') as f:
        client_id = f.readline().strip()
        client_secret = f.readline().strip()
    
    body = {
        'client_id': client_id,
        'client_secret': client_secret,
        "grant_type": 'client_credentials'
    }

    r = requests.post('https://id.twitch.tv/oauth2/token', body)
    keys = r.json();
    access_token = keys['access_token']
    with open(os.path.join(os.path.dirname(sys.argv[0]), 'twitch_access_token.txt'), 'w') as f:
        f.write(access_token)