import traceback

from packaging.version import parse as parse_version

from src.config import SETTINGS_FILE, TIME, DOA_TIME_THRESHOLD_MS, DOA_FILE, ARRAY_ARRANGEMENT, DOA_ANGLE, FREQUENCY_HZ, \
    CONFIDENCE, RSSI
from src.dataclasses import CacheRecord
from src.utils import get_kraken_version, get_config_value, now, kraken_doa_file_exists, doa_last_updated_at_ms, \
    normalize_angle


class AppData:
    def __init__(self):
        self.kraken_version = get_kraken_version()
        self.cache: set[CacheRecord] = set()
        self.cache_last_updated_at = 0
        self.array_angle: float = get_config_value(SETTINGS_FILE, 'array_angle')

    def version_specific_time(self, ll: list, logger) -> int:
        if self.kraken_version is not None and parse_version(self.kraken_version) == parse_version('1.6'):
            logger.debug(f'Kraken version: {self.kraken_version}. Use _now function.')
            return now()
        else:
            logger.debug(f'Kraken version: {self.kraken_version}. Use TIME.')
            return int(ll[TIME])
        
    def update_cache(self, logger):
        logger.debug('Updating app cache...')
        try:
            logger.debug(f'Current app cache size: {len(self.cache)}')
            time_threshold = now() - DOA_TIME_THRESHOLD_MS
            logger.debug(f'now = {now()}, time_threshold = {time_threshold}')
            self.cache = set([item for item in self.cache if item.timestamp >= time_threshold])
            logger.debug(f'Reduced by time threshold {time_threshold}, app cache size: {len(self.cache)}')
    
            if not kraken_doa_file_exists():
                logger.debug(f'File {DOA_FILE} does not exist. Skipping...')
                return
    
            if self.cache_last_updated_at >= doa_last_updated_at_ms():
                logger.debug(f'File {DOA_FILE} has not changed. Skipping...')
                return
    
            logger.debug(f'Parsing {DOA_FILE}...')
            with open(DOA_FILE) as f:
                read = f.read()
                logger.debug(f'Data read: {read[0:200]} ...')
                lines = read.split('\n')
                logger.debug(f'{len(lines)} lines read')
    
            for line in lines:
                logger.debug(f'Processing a line str={line[0:100]}...')
                if not line:
                    logger.debug('Line is too short. Skipping...')
                    continue
    
                ll = line.split(', ')
                if len(ll) < 9:
                    logger.debug(f'DOA is of the wrong format: {ll}')
                    continue
    
                ant_arrangement = ll[ARRAY_ARRANGEMENT]
                logger.debug(f'Antenna array type: {ant_arrangement}')
                # A hack for DOA heading for UCA array. Because KrakenSDR counts the angle counterclockwise
                if ant_arrangement == 'UCA':
                    logger.debug('Set doa_angle=360-DOA_ANGLE')
                    doa_angle = 360-float(ll[DOA_ANGLE])
                else:
                    logger.debug('Set doa_angle=DOA_ANGLE')
                    doa_angle = float(ll[DOA_ANGLE])
    
                if self.array_angle is not None:
                    logger.debug(f'Applying offset array_angle={self.array_angle} degrees...')
                    doa_angle = normalize_angle(doa_angle + self.array_angle)
                frequency_hz = int(ll[FREQUENCY_HZ])
                data = CacheRecord(timestamp=self.version_specific_time(ll, logger),
                                   doa=round(doa_angle, 3),
                                   confidence=round(float(ll[CONFIDENCE]), 2),
                                   rssi=round(float(ll[RSSI]), 2),
                                   frequency_hz=frequency_hz,
                                   ant_arrangement=ll[ARRAY_ARRANGEMENT])
    
                if data.timestamp > time_threshold:
                    logger.debug(f'Adding a line {data} to cache')
                    self.cache.add(data)
                    self.cache_last_updated_at = now()
                else:
                    logger.debug(f'Line {line[0:30]} is outdated (time_threshold = {time_threshold}, line ts = {data.timestamp}, delta = {time_threshold - data.timestamp}). Skipping...')
        except:
            logger.error(traceback.format_exc())


app_data = AppData()
