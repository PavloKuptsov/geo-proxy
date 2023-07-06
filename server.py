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
TIME = 0
DOA_ANGLE = 1
CONFIDENCE = 2
RSSI = 3
FREQUENCY_HZ = 4
ARRAY_ARRANGEMENT = 5
STATION_ID = 7
LATITUDE = 8
LONGITUDE = 9
GPS_HEADING = 10
COMPASS_HEADING = 11
HEADING_SENSOR = 12


class CacheRecord:
    def __init__(self, time: int, doa: float, confidence: float, rssi: float, frequency_hz: int):
        self.time = time
        self.doa = doa
        self.confidence = confidence
        self.rssi = rssi
        self.frequency_hz = frequency_hz


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


def _get_kraken_config_value(key: str) -> str:
    with open(SETTINGS_FILE) as file:
        settings = json.loads(file.read())
    return settings[key]


def _set_kraken_config_value(key: str, value: str):
    _update_kraken_config({key: value})


def _doa_last_updated_at() -> int:
    try:
        return int(os.path.getmtime(DOA_FILE) * 1000)
    except OSError:
        return 0


def _kraken_doa_file_exists() -> bool:
    return os.path.exists(DOA_FILE)


def _kraken_settings_file_exists() -> bool:
    return os.path.exists(SETTINGS_FILE)


app = Flask(__name__)
app.debug = True

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.info')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

app.cache: set[CacheRecord] = set()
app.cache_last_updated_at = 0
app.latitude = 0
app.longitude = 0
app.arrangement = ''
app.alias = None
app.heading = 0.0
CORS(app)


def update_cache():
    app.logger.debug(f'Updating app cache...')
    try:
        app.logger.debug(f'Current app cache size: {len(app.cache)}')
        now = int(time.time() * 1000)
        time_threshold = now - DOA_TIME_THRESHOLD_MS
        app.logger.debug(f'now = {now}, time_threshold = {time_threshold}')
        app.cache = set([item for item in app.cache if item.time >= time_threshold])
        app.logger.debug(f'Reduced by time threshold {time_threshold}, app cache size: {len(app.cache)}')

        if not _kraken_doa_file_exists():
            app.logger.debug(f'File {DOA_FILE} does not exist. Skipping...')
            return

        app.logger.debug(f'Parsing {DOA_FILE}...')
        with open(DOA_FILE) as f:
            read = f.read()
            app.logger.debug(f'Data read: {read[0:200]} ...')
            lines = read.split('\n')
            app.logger.debug(f'{len(lines)} lines read')

        for line in lines:
            app.logger.debug(f'Processing a line str={line[0:100]}...')
            if not line:
                app.logger.debug(f'Line is too short. Skipping...')
                continue

            ll = line.split(', ')
            if len(ll) < 9:
                app.logger.debug(f'DOA is of the wrong format: {ll}')
                continue

            gps_heading = ll[GPS_HEADING]
            compass_heading = ll[COMPASS_HEADING]
            is_gps_heading = ll[HEADING_SENSOR] == 'GPS'
            app.heading = gps_heading if is_gps_heading else compass_heading
            data = CacheRecord(time=now,
                               doa=float(ll[DOA_ANGLE]),
                               confidence=float(ll[CONFIDENCE]),
                               rssi=float(ll[RSSI]),
                               frequency_hz=int(ll[FREQUENCY_HZ]))
            app.arrangement = ll[ARRAY_ARRANGEMENT]
            app.latitude = float(ll[LATITUDE])
            app.longitude = float(ll[LONGITUDE])
            if ll[STATION_ID] != 'NOCALL':
                app.alias = ll[STATION_ID]

            if data.time > time_threshold:
                app.logger.debug(f'Adding a line {line[0:30]} to cache')
                app.cache.add(data)
                app.cache_last_updated_at = int(time.time() * 1000)
            else:
                app.logger.debug(f'Line {line[0:30]} is outdated (time_threshold = {time_threshold}, line ts = {data.time}, delta = {time_threshold-data.time}). Skipping...')
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
        settings = {'latitude': lat, 'longitude': lon, 'location_source': 'Static'}
        _update_kraken_config(settings)
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=400)


@app.get('/')
def ping():
    return {"message": "ping"}


@app.get('/healthcheck')
def healthcheck():
    now = int(time.time() * 1000)
    doa_last_updated_at = _doa_last_updated_at()
    doa_updated_ms_ago = now - doa_last_updated_at if doa_last_updated_at > 0 else None
    cache_updated_ms_ago = now - app.cache_last_updated_at if app.cache_last_updated_at > 0 else None
    settings_file_exists = _kraken_settings_file_exists()
    doa_file_exists = _kraken_doa_file_exists()
    status_ok = doa_file_exists and doa_updated_ms_ago < 1000 and settings_file_exists
    return {
        "status_ok": status_ok,
        "doa_updated_ms_ago": doa_updated_ms_ago,
        "cache_updated_ms_ago": cache_updated_ms_ago,
        "doa_file_exists": doa_file_exists,
        "settings_file_exists": settings_file_exists
    }


@app.get('/cache')
def cache():
    app.logger.debug(f'Responding with cache (args={request.args}). Current size: {len(app.cache)}')
    confidence = request.args.get('confidence')
    rssi = request.args.get('rssi')
    newer_than = request.args.get('newer_than')
    result = sorted(list(app.cache), key=lambda x: x.time, reverse=True)
    latest = result[0] if result else None

    if confidence:
        result = [record for record in result if record.confidence >= float(confidence)]

    if rssi:
        result = [record for record in result if record.rssi >= float(rssi)]

    if newer_than:
        result = [record for record in result if record.time >= int(newer_than)]

    app.logger.debug(f'Filtered cache size: {len(app.cache)}')

    data = [[record.time, record.doa, record.confidence, record.rssi, record.frequency_hz] for record in result]
    return jsonify({
        'lat': app.latitude,
        'lon': app.longitude,
        'arr': app.arrangement,
        'alias': app.alias,
        'freq': latest.frequency_hz if latest else None,
        'heading': app.heading,
        'data': data
    })


def create_app():
    app.logger.info(f'Kraken settings file: {SETTINGS_FILE}, exists: {_kraken_settings_file_exists()}')
    app.logger.info(f'Kraken DOA file: {DOA_FILE}, exists: {_kraken_doa_file_exists()}')

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
