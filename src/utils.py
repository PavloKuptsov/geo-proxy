import json


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
    with open(path, 'a') as file:
        settings = json.loads(file.read())

    for key in data:
        settings[key] = data[key]

    with open(path, 'w') as file:
        file.write(json.dumps(settings, indent=2))


def read_config(path: str):
    with open(path) as file:
        settings = json.loads(file.read())
    return settings





def set_config_value(path: str, key: str, value):
    update_config(path, {key: value})


