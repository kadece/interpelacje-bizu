"""Grzeczny klient HTTP dla BIP: throttling, ponawianie z backoffem."""
import time

import requests

from . import config

_session = requests.Session()
_session.headers.update({
    "User-Agent": config.HTTP_UA,
    "Accept-Language": "pl-PL,pl;q=0.9",
})
_last_request = 0.0


def _throttle() -> None:
    global _last_request
    now = time.monotonic()
    if config.REQUEST_DELAY_S > 0:
        wait = config.REQUEST_DELAY_S - (now - _last_request)
        if wait > 0:
            time.sleep(wait)
    _last_request = time.monotonic()


def _request(url: str, *, binary: bool = False):
    last_error = None
    for attempt in range(config.MAX_RETRIES):
        _throttle()
        try:
            response = _session.get(url, timeout=config.REQUEST_TIMEOUT_S)
            if response.status_code == 200:
                return response.content if binary else response.text
            if response.status_code in (429, 502, 503, 504):
                last_error = "HTTP %d" % response.status_code
            else:
                raise RuntimeError("HTTP %d dla %s" % (response.status_code, url))
        except requests.RequestException as error:
            last_error = str(error)
        time.sleep(2 ** attempt)
    raise RuntimeError("Nie udalo sie pobrac %s: %s" % (url, last_error))


def get_text(url: str) -> str:
    return _request(url, binary=False)


def get_bytes(url: str) -> bytes:
    return _request(url, binary=True)
