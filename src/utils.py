import json
import os
import time

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


def get_cached_config_value(path: str, key: str, ttl_ms = 1000):
    value, set_at = 0, 1
    now = int(time.time() * 1000)
    if (path, key) in config_cache and abs(now - config_cache[(path, key)][set_at]) < ttl_ms:
        return config_cache[(path, key)][value]

    result = get_config_value(path, key)
    config_cache[(path, key)] = [result, now]
    return result


