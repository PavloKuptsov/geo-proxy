import shutil
from dataclasses import dataclass
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from flask_compress import Compress
from src.system import *
from src.utils import *
from packaging.version import parse as parse_version

from src.ws_client import ClientSocket

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
WEB_UI_WS_URL = 'ws://127.0.0.1:8080/_push'
BACKUP_DIR_NAME = os.path.join(DOA_PATH, 'settings_backups')
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


@dataclass(eq=True, frozen=True)
class CacheRecord:
    timestamp: int
    doa: float
    confidence: float
    rssi: float
    frequency_hz: int


def _doa_last_updated_at_ms() -> int:
    try:
        return int(os.path.getmtime(DOA_FILE) * 1000)
    except OSError:
        return 0


def _kraken_doa_file_exists() -> bool:
    return os.path.exists(DOA_FILE)


def _kraken_settings_file_exists() -> bool:
    return os.path.exists(KRAKEN_SETTINGS_FILE)


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
app.latitude = 0
app.longitude = 0
app.arrangement = ''
app.alias = None
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

        if not _kraken_doa_file_exists():
            app.logger.debug(f'File {DOA_FILE} does not exist. Skipping...')
            return

        if app.cache_last_updated_at >= _doa_last_updated_at_ms():
            app.logger.debug(f'File {DOA_FILE} has not changed. Skipping...')
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

            app.arrangement = ll[ARRAY_ARRANGEMENT]
            app.logger.debug(f'Array type: {app.arrangement}')
            # A hack for DOA heading for UCA array. Because KrakenSDR counts the angle counterclockwise
            if app.arrangement == 'UCA':
                app.logger.debug(f'Set doa_angle=360-DOA_ANGLE')
                doa_angle = 360-float(ll[DOA_ANGLE])
            else:
                app.logger.debug(f'Set doa_angle=DOA_ANGLE')
                doa_angle = float(ll[DOA_ANGLE])

            if app.array_angle is not None:
                app.logger.debug(f'Applying offset array_angle={app.array_angle} degrees...')
                doa_angle = normalize_angle(doa_angle + app.array_angle)
            data = CacheRecord(timestamp=version_specific_time(ll),
                               doa=round(doa_angle, 3),
                               confidence=round(float(ll[CONFIDENCE]), 2),
                               rssi=round(float(ll[RSSI]), 2),
                               frequency_hz=int(ll[FREQUENCY_HZ]))
            app.latitude = float(ll[LATITUDE])
            app.longitude = float(ll[LONGITUDE])
            if ll[STATION_ID] != 'NOCALL':
                app.alias = ll[STATION_ID]

            if data.timestamp > time_threshold:
                app.logger.debug(f'Adding a line {data} to cache')
                app.cache.add(data)
                app.cache_last_updated_at = _now()
            else:
                app.logger.debug(f'Line {line[0:30]} is outdated (time_threshold = {time_threshold}, line ts = {data.timestamp}, delta = {time_threshold - data.timestamp}). Skipping...')
    except:
        app.logger.error(traceback.format_exc())


@app.post('/frequency')
def set_frequency():
    try:
        payload = request.json
        try:
            frequency_hz = int(payload.get('frequency_hz'))
        except (ValueError, TypeError):
            return Response(None, status=400)

        if not is_valid_frequency(frequency_hz):
            return Response(None, status=400)

        frequency_mhz = frequency_hz / (1.0 * 1000 * 1000)
        settings = dict()
        settings['center_freq'] = frequency_mhz
        for i in range(0, 16):
            settings['vfo_freq_' + str(i)] = frequency_hz
        update_config(KRAKEN_SETTINGS_FILE, settings)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=400)


@app.post('/coordinates')
def set_coordinates():
    try:
        payload = request.json
        lat = float(payload.get('lat'))
        lon = float(payload.get('lon'))
        settings = {'latitude': lat, 'longitude': lon, 'location_source': 'Static'}
        update_config(KRAKEN_SETTINGS_FILE, settings)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=400)


@app.post('/array_angle')
def set_array_angle():
    try:
        payload = request.json
        array_angle = payload.get('array_angle', None)
        if array_angle is not None and not is_valid_angle(float(array_angle)):
            return Response(None, status=400)
        app.array_angle = round(float(array_angle), 3) if array_angle is not None else None
        set_config_value(SETTINGS_FILE, 'array_angle', app.array_angle)
        return get_settings()
    except:
        app.logger.error(traceback.format_exc())
        return Response(None, status=500)


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
        return Response(None, status=400)


@app.get('/settings')
def get_settings():
    kraken_config = read_config(KRAKEN_SETTINGS_FILE)
    lat = kraken_config['latitude']
    lon = kraken_config['longitude']
    frequency_hz = int(kraken_config['center_freq'] * (1000 * 1000))
    alias = kraken_config['station_id']
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
    doa_last_updated_at = _doa_last_updated_at_ms()
    doa_updated_ms_ago = now - doa_last_updated_at if doa_last_updated_at > 0 else None
    cache_updated_ms_ago = now - app.cache_last_updated_at if app.cache_last_updated_at > 0 else None
    settings_file_exists = _kraken_settings_file_exists()
    doa_file_exists = _kraken_doa_file_exists()
    doa_ok = doa_updated_ms_ago < 1000 and doa_file_exists if doa_updated_ms_ago else False
    kraken_service_running = is_kraken_service_running()
    kraken_sdr_connected = is_kraken_sdr_connected()
    cpu_temperature = get_cpu_temperature()
    status_ok = doa_file_exists and doa_ok and settings_file_exists and kraken_service_running and kraken_sdr_connected
    return jsonify({
        "status_ok": status_ok,
        "doa_ok": doa_ok,
        "doa_updated_ms_ago": doa_updated_ms_ago,
        "cache_updated_ms_ago": cache_updated_ms_ago,
        "doa_file_exists": doa_file_exists,
        "settings_file_exists": settings_file_exists,
        "kraken_service_version": app.kraken_version,
        "kraken_service_running": kraken_service_running,
        "kraken_sdr_connected": kraken_sdr_connected,
        "kraken_suspended": not (kraken_service_running and kraken_sdr_connected),
        "cpu_temperature": cpu_temperature,
        "array_angle": app.array_angle
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
    return jsonify({
        'lat': app.latitude,
        'lon': app.longitude,
        'arr': app.arrangement,
        'alias': app.alias,
        'freq': latest.frequency_hz if latest else None,
        'array_angle': app.array_angle,
        'data': data
    })


@app.post('/suspend')
def suspend():
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
    ws = ClientSocket(WEB_UI_WS_URL)
    app.run(host='0.0.0.0', port=8082)
