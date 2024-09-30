import os

PROXY_VERSION = '2024.10.01'

LOG_LEVEL = str(os.getenv('LOG_LEVEL', 'WARNING'))
SETTINGS_FILENAME = 'geo_settings.json'
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), SETTINGS_FILENAME)
KRAKEN_SETTINGS_FILENAME = 'settings.json'
DOA_FILENAME = 'DOA_value.html'
DOA_PATH = str(os.getenv('DOA_PATH', '/home/krakenrf/krakensdr_doa/krakensdr_doa'))

if os.path.exists(os.path.join(DOA_PATH, '_share')):
    KRAKEN_SETTINGS_FILE = os.path.join(DOA_PATH, '_share', KRAKEN_SETTINGS_FILENAME)
    DOA_FILE = os.path.join(DOA_PATH, '_share', DOA_FILENAME)
else:
    KRAKEN_SETTINGS_FILE = os.path.join(DOA_PATH, KRAKEN_SETTINGS_FILENAME)
    DOA_FILE = os.path.join(DOA_PATH, '_android_web', DOA_FILENAME)

WEB_UI_FILE_NEW = os.path.join(DOA_PATH, '_UI/_web_interface/kraken_web_config.py')
WEB_UI_FILE_OLD = os.path.join(DOA_PATH, '_UI/_web_interface/kraken_web_interface.py')
WEB_UI_VARIABLES_FILE = os.path.join(DOA_PATH, '_ui/_web_interface/variables.py')

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
NOCALL = 'NOCALL'
