import cherrypy

from . import root, packages, simple


def main():
    cherrypy.tree.mount(root.Root(), '/', root.config)
    cherrypy.tree.mount(packages.Packages(), '/packages', packages.config)
    cherrypy.tree.mount(simple.Simple(), '/simple', simple.config)
    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == '__main__':
    main()
