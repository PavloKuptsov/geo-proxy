from dataclasses import dataclass


@dataclass(eq=True, frozen=True)
class CacheRecord:
    timestamp: int
    doa: float
    confidence: float
    rssi: float
    frequency_hz: int
    ant_arrangement: str
