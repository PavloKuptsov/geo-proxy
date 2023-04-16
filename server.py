import json
import os
import shutil
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

SETTINGS_FILENAME = 'settings.json'
DOA_FILENAME = 'DOA_value.html'
DOA_PATH = '/home/krakenrf/krakensdr_doa/krakensdr_doa'
SETTINGS_FILE = f'/{DOA_PATH}/{SETTINGS_FILENAME}'
DOA_FILE = f'{DOA_PATH}/_android_web/{DOA_FILENAME}'
BACKUP_DIR_NAME = f'{DOA_PATH}/settings_backups'
DOA_READ_REGULARITY_MS = int(os.getenv('DOA_READ_REGULARITY_MS', 100))
DOA_TIME_THRESHOLD_MS = int(os.getenv('DOA_TIME_THRESHOLD_MS', 5000))


def _is_valid_frequency(frequency_hz: int) -> bool:
    min_supported_freq_hz = 24 * 1000 * 1000
    max_supported_freq_hz = 1766 * 1000 * 1000
    return min_supported_freq_hz < frequency_hz < max_supported_freq_hz


app = Flask(__name__)
app.cache = set()
app.latitude = 0
app.longitude = 0
app.arrangement = ''
CORS(app)


def update_cache():
    now = datetime.now()
    print(f'Cache update started {now.isoformat()}')
    time_threshold = int(now.timestamp() * 1000) - DOA_TIME_THRESHOLD_MS
    app.cache = set([item for item in app.cache if item[0] >= time_threshold])

    with open(DOA_FILE) as f:
        lines = f.read().split('\n')

    for line in lines:
        if not line:
            continue

        ll = line.split(', ')
        data = (int(ll[0]), int(ll[1]), float(ll[2]), float(ll[3]), int(ll[4]))
        app.arrangement = ll[5]
        app.latitude = float(ll[8])
        app.longitude = float(ll[9])
        if data[0] > time_threshold:
            app.cache.add(data)


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
    return {"message": "ping"}


@app.get('/cache')
def cache():
    confidence = request.args.get('confidence')
    if confidence:
        result = [item for item in app.cache if item[2] >= float(confidence)]
    else:
        result = list(app.cache)

    return jsonify({
        'lat': app.latitude,
        'lon': app.longitude,
        'arr': app.arrangement,
        'data': result
    })


def create_app():
    now = datetime.now()
    if not os.path.exists(BACKUP_DIR_NAME):
        os.makedirs(BACKUP_DIR_NAME)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_cache, trigger='interval', seconds=DOA_READ_REGULARITY_MS / 1000.0)
    scheduler.start()

    destination = f'{BACKUP_DIR_NAME}/{now.strftime("%Y%m%d-%H%M%S")}-{SETTINGS_FILENAME}.bak'
    shutil.copyfile(SETTINGS_FILE, destination)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(port=8082)
