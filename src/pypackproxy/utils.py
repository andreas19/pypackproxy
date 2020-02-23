import atexit
import os
from contextlib import ExitStack
from importlib.resources import path as res_path
from urllib.parse import urlparse

from . import DATA_PACKAGE


def get_favicon_path():
    file_manager = ExitStack()
    atexit.register(file_manager.close)
    path = file_manager.enter_context(
        res_path(DATA_PACKAGE, 'favicon.ico'))
    return str(path)


def check_path(path, name):
    if not os.path.isabs(path):
        raise ValueError(f'{name} not absolute: {path}')
    if not os.path.exists(path):
        raise RuntimeError(f'{name} directory does not exist: {path}')


def check_url(url, name):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f'invalid {name} {url!r}:'
                         ' only http(s) urls allowed')
    try:
        parsed.port
    except ValueError:
        raise ValueError(f'invalid {name} {url!r}: port out of range')
    if not parsed.netloc:
        raise ValueError(f'incomplete {name}: {url}')
    return parsed


def check_passwd(s):
    if s.lower() == 'false':
        return False
    if len(s) < 8:
        raise ValueError(
            'Password must be at least 8 characters long')
    return s


def file_size(s):
    if len(s) >= 2 and s[-1].upper() in ('K', 'M'):
        num = float(s[:-1])
        if s[-1].upper() == 'K':
            return round(num * 2 ** 10)
        return round(num * 2 ** 20)
    else:
        return int(s)


def pos_float(s):
    x = float(s)
    if x < 0.0:
        raise ValueError('value must be >= 0.0')
    return x


def pos_int(s):
    x = int(s)
    if x < 0:
        raise ValueError('value must be >= 0')
    return x
