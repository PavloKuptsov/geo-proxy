import json
import os
import re
import time
from typing import Optional

from src.config import DOA_FILE, KRAKEN_SETTINGS_FILE, WEB_UI_FILE_NEW, WEB_UI_FILE_OLD, WEB_UI_VARIABLES_FILE

config_cache = dict()


def normalize_angle(angle: float) -> float:
    value = angle % 360
    if value < 0:
        value += 360
    return value


def is_valid_frequency(frequency_hz: int) -> bool:
    min_supported_freq_hz = 24 * 1000 * 1000
    max_supported_freq_hz = 1766 * 1000 * 1000
    return min_supported_freq_hz <= frequency_hz <= max_supported_freq_hz


def is_valid_angle(angle: float) -> bool:
    return 0.0 <= angle <= 360.0


def update_config(path: str, data: dict):
    settings = {}
    if os.path.exists(path):
        with open(path) as file:
            settings = json.loads(file.read())
    for key in data:
        settings[key] = data[key]
    with open(path, 'w') as file:
        file.write(json.dumps(settings, indent=2))


def read_config(path: str):
    settings = {}
    if os.path.exists(path):
        with open(path) as file:
            settings = json.loads(file.read())
    return settings


def set_config_value(path: str, key: str, value):
    update_config(path, {key: value})


def get_config_value(path: str, key: str):
    settings = read_config(path)
    return settings[key] if key in settings else None


def get_cached_config_value(path: str, key: str, ttl_ms=1000):
    value, set_at = 0, 1
    now = int(time.time() * 1000)
    if (path, key) in config_cache and abs(now - config_cache[(path, key)][set_at]) < ttl_ms:
        return config_cache[(path, key)][value]

    result = get_config_value(path, key)
    config_cache[(path, key)] = [result, now]
    return result


def doa_last_updated_at_ms() -> int:
    try:
        return int(os.path.getmtime(DOA_FILE) * 1000)
    except OSError:
        return 0


def kraken_doa_file_exists() -> bool:
    return os.path.exists(DOA_FILE)


def kraken_settings_file_exists() -> bool:
    return os.path.exists(KRAKEN_SETTINGS_FILE)


def get_cached_frequency_from_kraken_config() -> int:
    frequency_mhz = get_cached_config_value(KRAKEN_SETTINGS_FILE, 'center_freq', 400)
    return int(float(frequency_mhz) * 1000 * 1000) if frequency_mhz else None


def get_kraken_version() -> Optional[str]:
    version = None
    env_version = os.getenv('KRAKEN_VERSION', None)
    if env_version is not None:
        version = str(env_version)

    # 1.7 and higher
    if not version:
        version = get_regex_match_from_file(WEB_UI_VARIABLES_FILE, re.compile(r'SOFTWARE_VERSION\s=\s\"(.*)\"'))

    # 1.6.x
    if not version:
        version = get_regex_match_from_file(WEB_UI_FILE_NEW, re.compile(r'html\.Div\(\"Version (.*)\"'))

    # pre-1.6
    if not version:
        version = get_regex_match_from_file(WEB_UI_FILE_OLD, re.compile(r'html\.Div\(\"Version (.*)\"'))

    return version


def get_regex_match_from_file(file_path: str, regex) -> Optional[str]:
    if not os.path.exists(file_path):
        return None

    with open(WEB_UI_FILE_OLD) as f:
        match = re.search(regex, f.read())
    return match.groups()[0] if match and len(match.groups()) else None


def now() -> int:
    return int(time.time() * 1000)
