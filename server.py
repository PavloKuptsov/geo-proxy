import json
import logging
import os
import shutil
import time
import traceback
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


def _to_int(value: str):
    try:
        return int(value)
    except ValueError:
        return int(float(value))


def _is_valid_frequency(frequency_hz: int) -> bool:
    min_supported_freq_hz = 24 * 1000 * 1000
    max_supported_freq_hz = 1766 * 1000 * 1000
    return min_supported_freq_hz <= frequency_hz <= max_supported_freq_hz


def _update_kraken_config(data: dict):
    with open(SETTINGS_FILE) as file:
        settings = json.loads(file.read())

    for key in data:
        settings[key] = data[key]

    with open(SETTINGS_FILE, 'w') as file:
        file.write(json.dumps(settings, indent=2))


app = Flask(__name__)
app.debug = True

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.info')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

app.cache = set()
app.latitude = 0
app.longitude = 0
app.arrangement = ''
CORS(app)


def update_cache():
    app.logger.info(f'Updating app cache...')
    try:
        app.logger.info(f'Current app cache size: {len(app.cache)}')
        now = int(time.time() * 1000)
        time_threshold = now - DOA_TIME_THRESHOLD_MS
        app.logger.info(f'now = {now}, time_threshold = {time_threshold}')
        app.cache = set([item for item in app.cache if item[0] >= time_threshold])
        app.logger.info(f'Reduced by time threshold {time_threshold}, app cache size: {len(app.cache)}')

        app.logger.info(f'Parsing {DOA_FILE}...')
        with open(DOA_FILE) as f:
            read = f.read()
            app.logger.info(f'Data read: {read[0:200]} ...')
            lines = read.split('\n')
            app.logger.info(f'{len(lines)} lines read')

        for line in lines:
            app.logger.info(f'Processing a line str={line[0:100]}...')
            if not line:
                app.logger.info(f'Line is too short. Skipping...')
                continue

            ll = line.split(', ')
            if len(ll) < 9:
                app.logger.info(f'DOA is of the wrong format: {ll}')
                continue

            data = (now, _to_int(ll[1]), float(ll[2]), float(ll[3]), _to_int(ll[4]))
            app.arrangement = ll[5]
            app.latitude = float(ll[8])
            app.longitude = float(ll[9])
            if data[0] > time_threshold:
                app.logger.info(f'Adding a line {line[0:30]} to cache')
                app.cache.add(data)
            else:
                app.logger.info(f'Line {line[0:30]} is outdated (time_threshold = {time_threshold}, line ts = {data[0]}, delta = {time_threshold-data[0]}). Skipping...')
    except:
        app.logger.error(traceback.format_exc())


@app.post('/frequency')
def frequency():
    try:
        payload = request.json
        try:
            frequency_hz = int(payload.get('frequency_hz'))
        except (ValueError, TypeError):
            return Response(None, status=400)

        if not _is_valid_frequency(frequency_hz):
            return Response(None, status=400)

        frequency_mhz = frequency_hz / 1000000.0
        settings = dict()
        settings['center_freq'] = frequency_mhz
        for i in range(0, 16):
            settings['vfo_freq_' + str(i)] = frequency_hz
        _update_kraken_config(settings)
        return Response(None, status=200)
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=400)


@app.post('/coordinates')
def coordinates():
    try:
        payload = request.json
        lat = float(payload.get('lat'))
        lon = float(payload.get('lon'))
        settings = {'latitude': lat, 'longitude': lon}
        _update_kraken_config(settings)
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=400)


@app.get('/')
def ping():
    return {"message": "ping"}


@app.get('/cache')
def cache():
    app.logger.info(f'Responding with cache (args={request.args}). Current size: {len(app.cache)}')
    confidence = request.args.get('confidence')
    rssi = request.args.get('rssi')
    newer_than = request.args.get('newer_than')
    result = sorted(list(app.cache), key=lambda x: x[0], reverse=True)
    latest = result[0] if result else None

    if confidence:
        result = [item for item in result if item[2] >= float(confidence)]

    if rssi:
        result = [item for item in result if item[3] >= float(rssi)]

    if newer_than:
        result = [item for item in result if item[0] >= int(newer_than)]

    app.logger.info(f'Filtered cache size: {len(app.cache)}')

    return jsonify({
        'lat': app.latitude,
        'lon': app.longitude,
        'arr': app.arrangement,
        'freq': latest[4] if latest else None,
        'data': result
    })


def create_app():
    now = datetime.now()
    if not os.path.exists(BACKUP_DIR_NAME):
        os.makedirs(BACKUP_DIR_NAME)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_cache, trigger='interval', seconds=DOA_READ_REGULARITY_MS / 1000.0)
    scheduler.start()
    app.logger.info(f'Cache updater started {now.isoformat()}, running')

    destination = f'{BACKUP_DIR_NAME}/{now.strftime("%Y%m%d-%H%M%S")}-{SETTINGS_FILENAME}.bak'
    shutil.copyfile(SETTINGS_FILE, destination)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8082)
