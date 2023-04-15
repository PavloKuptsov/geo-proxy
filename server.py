import json
import os
import shutil
from datetime import datetime

from flask import Flask, request, Response
from flask_cors import CORS

SETTINGS_FILENAME = 'settings.json'
SETTINGS_FILE = f'/home/krakenrf/krakensdr_doa/krakensdr_doa/{SETTINGS_FILENAME}'
BACKUP_DIR_NAME = '/home/krakenrf/krakensdr_doa/krakensdr_doa/settings_backups'


def _is_valid_frequency(frequency_hz: int) -> bool:
    min_supported_freq_hz = 24 * 1000 * 1000
    max_supported_freq_hz = 1766 * 1000 * 1000
    return min_supported_freq_hz < frequency_hz < max_supported_freq_hz


app = Flask(__name__)
CORS(app)


@app.post('/frequency')
def frequency():
    payload = request.json
    try:
        frequency_hz = int(payload.get('frequency_hz'))
    except (ValueError, TypeError):
        return Response(None, status=400)

    if not _is_valid_frequency(frequency_hz):
        return Response(None, status=400)

    with open(SETTINGS_FILE) as file:
        settings = json.loads(file.read())

    frequency_mhz = frequency_hz / 1000000.0
    settings['center_freq'] = frequency_mhz
    for i in range(0, 16):
        settings['vfo_freq_' + str(i)] = frequency_hz

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
