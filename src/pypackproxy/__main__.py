import mimetypes
import sys

import cherrypy
from cherrypy._cpnative_server import CPHTTPServer

from . import renderer, root, packs, simple, __version__, PYPP_DEBUG, PROG_NAME
from .configuration import configure

mimetypes.add_type('application/octet-stream', '.whl')


def main(config: 'Configuration file'):  # noqa: F722
    try:
        cfg = configure(config)
        renderer.init()
        cherrypy.log('START', 'INFO')
        cherrypy.server.httpserver = CPHTTPServer(cherrypy.server)
        cherrypy.tree.mount(root.Root(cfg), root.path, root.config)
        cherrypy.tree.mount(packs.Packs(cfg), packs.path, packs.config)
        cherrypy.tree.mount(simple.Simple(cfg), simple.path, simple.config)
        cherrypy.engine.signals.subscribe()
        cherrypy.engine.start()
        cherrypy.engine.block()
    except Exception as ex:
        cherrypy.log(str(ex), 'ERROR', traceback=PYPP_DEBUG)
        sys.exit(ex)
    finally:
        cherrypy.log('STOP', 'INFO')


main.description = f'{PROG_NAME} {__version__}'


def entry_point():
    import plac
    plac.call(main)


if __name__ == '__main__':
    entry_point()
