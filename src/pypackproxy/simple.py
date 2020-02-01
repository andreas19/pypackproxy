import cherrypy

config = {'/': {}}


class Simple:
    @cherrypy.expose
    def index(self, *args, **kwargs):
        print('simple', args, kwargs)
