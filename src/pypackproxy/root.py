import cherrypy

config = {'/': {}}


class Root:
    @cherrypy.expose
    def index(self, *args, **kwargs):
        print('root', args, kwargs)
