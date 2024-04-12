import shutil
from dataclasses import dataclass
from datetime import datetime

import random

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from flask_compress import Compress

from src import ws_client
from src.system import *
from src.utils import *
from packaging.version import parse as parse_version

PROXY_VERSION = '2024.04.12'

LOG_LEVEL = str(os.getenv('LOG_LEVEL', 'WARNING'))
SETTINGS_FILENAME = 'geo_settings.json'
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), SETTINGS_FILENAME)
if not os.path.exists(SETTINGS_FILE):
    update_config(SETTINGS_FILE, {})
KRAKEN_SETTINGS_FILENAME = 'settings.json'
DOA_FILENAME = 'DOA_value.html'
DOA_PATH = str(os.getenv('DOA_PATH', '/home/krakenrf/krakensdr_doa/krakensdr_doa'))
if os.path.exists(os.path.join(DOA_PATH, '_share')):
    KRAKEN_SETTINGS_FILE = os.path.join(DOA_PATH, '_share', KRAKEN_SETTINGS_FILENAME)
    DOA_FILE = os.path.join(DOA_PATH, '_share', DOA_FILENAME)
else:
    KRAKEN_SETTINGS_FILE = os.path.join(DOA_PATH, KRAKEN_SETTINGS_FILENAME)
    DOA_FILE = os.path.join(DOA_PATH, '_android_web', DOA_FILENAME)
if not os.path.exists(KRAKEN_SETTINGS_FILE):
    raise Exception(f'File {KRAKEN_SETTINGS_FILE} does not exist')
WEB_UI_FILE_NEW = os.path.join(DOA_PATH, '_UI/_web_interface/kraken_web_config.py')
WEB_UI_FILE_OLD = os.path.join(DOA_PATH, '_UI/_web_interface/kraken_web_interface.py')
BACKUP_DIR_NAME = os.path.join(DOA_PATH, 'settings_backups')
DOA_READ_REGULARITY_MS = int(os.getenv('DOA_READ_REGULARITY_MS', 500))
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
NOCALL = 'NOCALL'


@dataclass(eq=True, frozen=True)
class CacheRecord:
    timestamp: int
    doa: float
    confidence: float
    rssi: float
    frequency_hz: int
    ant_arrangement: str


class Error:
    def __init__(self, message: str):
        self.message = message

    def to_json(self):
        return json.dumps({'message': self.message})


def _doa_last_updated_at_ms() -> int:
    try:
        return int(os.path.getmtime(DOA_FILE) * 1000)
    except OSError:
        return 0


def _kraken_doa_file_exists() -> bool:
    return os.path.exists(DOA_FILE)


def _kraken_settings_file_exists() -> bool:
    return os.path.exists(KRAKEN_SETTINGS_FILE)


def _get_cached_frequency_from_kraken_config() -> int:
    frequency_mhz = get_cached_config_value(KRAKEN_SETTINGS_FILE, 'center_freq', 400)
    return int(float(frequency_mhz) * 1000 * 1000) if frequency_mhz else None


def _get_kraken_version() -> str:
    env_version = os.getenv('KRAKEN_VERSION', None)
    if env_version is not None:
        return str(env_version)
    else:
        version_regex = re.compile(r'html\.Div\(\"Version (.*)\"')
        ui_file = WEB_UI_FILE_NEW if os.path.exists(WEB_UI_FILE_NEW) else WEB_UI_FILE_OLD
        try:
            with open(ui_file) as f:
                match = re.search(version_regex, f.read())

            return match.groups()[0] if match and len(match.groups()) else None
        except FileNotFoundError:
            return None


def _now() -> int:
    return int(time.time() * 1000)


app = Flask(__name__)
app.debug = True
app.kraken_version = _get_kraken_version()
app.logger.setLevel(LOG_LEVEL)
app.cache: set[CacheRecord] = set()
app.cache_last_updated_at = 0
app.array_angle: float = get_config_value(SETTINGS_FILE, 'array_angle')
compress = Compress()
compress.init_app(app)
CORS(app)


def version_specific_time(ll: list) -> int:
    if app.kraken_version is not None and parse_version(app.kraken_version) == parse_version('1.6'):
        app.logger.debug(f'Kraken version: {app.kraken_version}. Use _now function.')
        return _now()
    else:
        app.logger.debug(f'Kraken version: {app.kraken_version}. Use TIME.')
        return int(ll[TIME])


def update_cache():
    app.logger.debug(f'Updating app cache...')
    try:
        app.logger.debug(f'Current app cache size: {len(app.cache)}')
        time_threshold = _now() - DOA_TIME_THRESHOLD_MS
        app.logger.debug(f'now = {_now()}, time_threshold = {time_threshold}')
        app.cache = set([item for item in app.cache if item.timestamp >= time_threshold])
        app.logger.debug(f'Reduced by time threshold {time_threshold}, app cache size: {len(app.cache)}')


        signal_strength = random.uniform(0.01, 1)

        data = CacheRecord(timestamp=_now() - random.randint(100, 150),
                           doa=round(random.uniform(110, 120), 1),
                           confidence=round(0.5 + 7.5 * signal_strength, 2),  # 0.5 - 8,
                           rssi=-80 + round(60 * signal_strength),
                           frequency_hz=_get_cached_frequency_from_kraken_config(),
                           ant_arrangement=get_cached_config_value(KRAKEN_SETTINGS_FILE, 'ant_arrangement'))

        app.cache.add(data)
        app.cache_last_updated_at = _now()
    except:
        app.logger.error(traceback.format_exc())


@app.post('/frequency')
def set_frequency():
    try:
        payload = request.json
        try:
            frequency_hz = int(payload.get('frequency_hz'))
        except (ValueError, TypeError):
            return Response(Error(f'Invalid frequency').to_json(), status=400)

        if not is_valid_frequency(frequency_hz):
            return Response(Error(f'Frequency {frequency_hz} is out of range').to_json(), status=400)

        frequency_mhz = frequency_hz / (1.0 * 1000 * 1000)
        if frequency_hz != _get_cached_frequency_from_kraken_config():
            settings = dict()
            settings['center_freq'] = frequency_mhz
            for i in range(0, 16):
                settings['vfo_freq_' + str(i)] = frequency_hz
            update_config(KRAKEN_SETTINGS_FILE, settings)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(Error('Failed to set frequency').to_json(), status=400)


@app.post('/coordinates')
def set_coordinates():
    try:
        payload = request.json
        lat = float(payload.get('lat'))
        lon = float(payload.get('lon'))
    except:
        return Response(Error('Invalid coordinates').to_json(), status=400)
    try:
        settings = {'latitude': lat, 'longitude': lon, 'location_source': 'Static'}
        update_config(KRAKEN_SETTINGS_FILE, settings)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(Error('Failed to set coordinates').to_json(), status=500)


@app.post('/array_angle')
def set_array_angle():
    try:
        payload = request.json
        array_angle = payload.get('array_angle', None)
        if array_angle is not None and not is_valid_angle(float(array_angle)):
            return Response(Error(f'"{array_angle}" is not a valid angle').to_json(), status=400)
        app.array_angle = round(float(array_angle), 3) if array_angle is not None else None
        set_config_value(SETTINGS_FILE, 'array_angle', app.array_angle)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(Error('Failed to set an antenna array angle').to_json(), status=500)


@app.post('/settings')
def set_settings():
    try:
        params = {}
        payload = request.json
        station_alias = payload.get('alias', None)
        if station_alias is not None:
            params['station_id'] = str(station_alias).strip()[0:20]
        update_config(KRAKEN_SETTINGS_FILE, params)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(Error('Failed to set a station settings').to_json(), status=400)


@app.get('/settings')
def get_settings():
    kraken_config = read_config(KRAKEN_SETTINGS_FILE)
    lat = kraken_config['latitude']
    lon = kraken_config['longitude']
    frequency_hz = int(kraken_config['center_freq'] * (1000 * 1000))
    alias = kraken_config['station_id'] if kraken_config['station_id'] != NOCALL else None
    return jsonify({
        "array_angle": app.array_angle,
        "lat": lat,
        "lon": lon,
        "frequency_hz": frequency_hz,
        "alias": alias
    })


@app.get('/')
def ping():
    return {"message": "ping"}


@app.get('/healthcheck')
def healthcheck():
    now = _now()
    in_docker = is_in_docker()
    doa_last_updated_at = _doa_last_updated_at_ms()
    doa_updated_ms_ago = now - doa_last_updated_at if doa_last_updated_at > 0 else None
    cache_updated_ms_ago = now - app.cache_last_updated_at if app.cache_last_updated_at > 0 else None
    settings_file_exists = _kraken_settings_file_exists()
    doa_file_exists = _kraken_doa_file_exists()
    doa_ok = doa_updated_ms_ago < 1000 and doa_file_exists if doa_updated_ms_ago else False
    kraken_service_running = is_kraken_service_running() if not in_docker else None
    kraken_sdr_connected = is_kraken_sdr_connected() if not in_docker else None
    cpu_temperature = get_cpu_temperature() if not in_docker else None
    status_ok = doa_file_exists and settings_file_exists and (in_docker or (kraken_service_running and kraken_sdr_connected))
    return jsonify({
        "status_ok": status_ok,
        "doa_ok": doa_ok,
        "in_docker": in_docker,
        "doa_updated_ms_ago": doa_updated_ms_ago,
        "cache_updated_ms_ago": cache_updated_ms_ago,
        "doa_file_exists": doa_file_exists,
        "settings_file_exists": settings_file_exists,
        "kraken_service_version": app.kraken_version,
        "kraken_service_running": kraken_service_running,
        "kraken_sdr_connected": kraken_sdr_connected,
        "kraken_suspended": not (kraken_service_running and kraken_sdr_connected) if not in_docker else None,
        "cpu_temperature": cpu_temperature,
        "array_angle": app.array_angle,
        "proxy_version": PROXY_VERSION
    })


@app.get('/cache')
def cache():
    app.logger.debug(f'Responding with cache (args={request.args}). Current size: {len(app.cache)}')
    confidence = request.args.get('confidence')
    rssi = request.args.get('rssi')
    newer_than = request.args.get('newer_than')
    result = sorted(list(app.cache), key=lambda x: x.timestamp, reverse=True)
    latest = result[0] if result else None

    if confidence:
        result = [record for record in result if record.confidence >= float(confidence)]

    if rssi:
        result = [record for record in result if record.rssi >= float(rssi)]

    if newer_than:
        result = [record for record in result if record.timestamp >= int(newer_than)]

    app.logger.debug(f'Filtered cache size: {len(app.cache)}')

    data = [[record.timestamp, record.doa, record.confidence, record.rssi, record.frequency_hz] for record in result]

    station_alias = get_cached_config_value(KRAKEN_SETTINGS_FILE, 'station_id')
    latitude = get_cached_config_value(KRAKEN_SETTINGS_FILE, 'latitude')
    longitude = get_cached_config_value(KRAKEN_SETTINGS_FILE, 'longitude')
    curr_frequency = latest.frequency_hz if latest else None
    if not curr_frequency:
        curr_frequency = _get_cached_frequency_from_kraken_config()
    curr_ant_arrangement = latest.ant_arrangement if latest else None
    if not curr_ant_arrangement:
        curr_ant_arrangement = get_cached_config_value(KRAKEN_SETTINGS_FILE, 'ant_arrangement')

    return jsonify({
        'lat': latitude if latitude is not None else 0,
        'lon': longitude if longitude is not None else 0,
        'arr': curr_ant_arrangement,
        'alias': station_alias if station_alias != NOCALL else None,
        'freq': curr_frequency,
        'array_angle': app.array_angle,
        'data': data
    })


@app.post('/suspend')
def suspend():
    if is_in_docker():
        return Response(Error('Cant suspend in Docker').to_json(), status=400)
    try:
        payload = request.json
        turn_power_on = payload.get('power_on')
        if turn_power_on:
            kraken_sdr_power_on()
        else:
            kraken_sdr_power_off()
        return healthcheck()
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=400)


@app.post('/reboot')
def reboot():
    if is_in_docker():
        return Response(Error('Cant reboot in Docker').to_json(), status=400)
    system_reboot()
    return Response(status=200)


def create_app():
    app.logger.info(f'Kraken settings file: {KRAKEN_SETTINGS_FILE}, exists: {_kraken_settings_file_exists()}')
    app.logger.info(f'Kraken DOA file: {DOA_FILE}, exists: {_kraken_doa_file_exists()}')

    now = datetime.now()
    if not os.path.exists(BACKUP_DIR_NAME):
        os.makedirs(BACKUP_DIR_NAME)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_cache, trigger='interval', seconds=DOA_READ_REGULARITY_MS / 1000.0)
    scheduler.start()
    app.logger.info(f'Cache updater started {now.isoformat()}, running')
    destination = os.path.join(BACKUP_DIR_NAME, f'{now.strftime("%Y%m%d-%H%M%S")}-{KRAKEN_SETTINGS_FILENAME}.bak')
    shutil.copyfile(KRAKEN_SETTINGS_FILE, destination)
    return app


if __name__ == '__main__':
    app = create_app()
    ws_client.run_in_thread()
    app.run(host='0.0.0.0', port=8082)
