"""PyPackProxy package."""

import os

__version__ = '0.3.1'

PROG_NAME = 'PyPackProxy'

PYPP_DEBUG = bool(os.getenv('PYPP_DEBUG'))

ROOT_PATH = '/'
PACKS_PATH = '/packs'
SIMPLE_PATH = '/simple'

DATA_PACKAGE = f'{__package__}.data'
