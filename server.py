import json
import os
import shutil
from datetime import datetime

from flask import Flask, request, Response

SETTINGS_FILE = 'settings.json'
BACKUP_DIR_NAME = 'settings_backups'


app = Flask(__name__)


@app.post('/frequency')
def frequency():
    payload = request.json
    try:
        freq = float(payload.get('frequency'))
    except (ValueError, TypeError):
        return Response(None, status=400)

    with open(SETTINGS_FILE) as file:
        settings = json.loads(file.read())

    settings['center_freq'] = freq
    with open(SETTINGS_FILE, 'w') as file:
        file.write(json.dumps(settings, indent=2))
    return Response(None, status=200)


@app.get('/')
def ping():
    return Response('{"message": "ping"}', status=200)


def create_app():
    now = datetime.now()
    if not os.path.exists(BACKUP_DIR_NAME):
        os.makedirs(BACKUP_DIR_NAME)

    destination = f'{BACKUP_DIR_NAME}/{now.strftime("%Y%m%d-%H%M%S")}-{SETTINGS_FILE}.bak'
    shutil.copyfile(SETTINGS_FILE, destination)
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
