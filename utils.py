import re

def normalize_stream(name):
    name = name.strip().lower().replace(' ', '')
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return name

def normalize_game(name):
    name = name.strip().lower().replace(' ', '').replace('-', '').replace(':','')
    name = re.sub(r'[^A-Za-z0-9]+', '', name)
    return name