import cherrypy

config = {'/': {}}


class Packages:
    @cherrypy.expose
    def index(self, *args, **kwargs):
        print('packages', args, kwargs)
