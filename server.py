import json
import os
import shutil
from datetime import datetime

from flask import Flask, request, Response
from flask_cors import CORS

SETTINGS_FILENAME = 'settings.json'
SETTINGS_FILE = f'/home/krakenrf/krakensdr_doa/krakensdr_doa/{SETTINGS_FILENAME}'
BACKUP_DIR_NAME = '/home/krakenrf/krakensdr_doa/krakensdr_doa/settings_backups'


app = Flask(__name__)
CORS(app)


@app.post('/frequency')
def frequency():
    payload = request.json
    try:
        freq_mhz = float(payload.get('frequency'))
    except (ValueError, TypeError):
        return Response(None, status=400)

    with open(SETTINGS_FILE) as file:
        settings = json.loads(file.read())

    settings['center_freq'] = freq_mhz
    freq_hz = int(freq_mhz * 1000000)
    for i in range(0, 16):
        settings['vfo_freq_' + str(i)] = freq_hz

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

    destination = f'{BACKUP_DIR_NAME}/{now.strftime("%Y%m%d-%H%M%S")}-{SETTINGS_FILENAME}.bak'
    shutil.copyfile(SETTINGS_FILE, destination)
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
