"""
config.py
---------
Configuracion centralizada y mutable en tiempo de ejecucion.
Thread-safe: la API y el loop principal pueden leer/escribir sin race conditions.
"""

import threading

_lock = threading.Lock()

_cfg: dict = {
    "min_confidence":    0.5,
    "min_confirmations": 2,
    "min_contour_area":  3000,
    "cooldown":          5.0,
    "capture_interval":  0.5,
    "total_photos":      4,
    "debug":             False,
}


def get(key: str):
    with _lock:
        return _cfg[key]


def update(values: dict) -> dict:
    with _lock:
        for k, v in values.items():
            if k in _cfg:
                _cfg[k] = v
    return snapshot()


def snapshot() -> dict:
    with _lock:
        return dict(_cfg)