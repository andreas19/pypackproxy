from jinja2 import Environment, PackageLoader

from . import PYPP_DEBUG, PROG_NAME, __version__


def init():
    global _env
    _env = Environment(auto_reload=PYPP_DEBUG,
                       loader=PackageLoader(__package__))


def render(name, **data):
    return _env.get_template(name).render(progname=PROG_NAME,
                                          progversion=__version__,
                                          **data)
