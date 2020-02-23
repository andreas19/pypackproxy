from importlib.resources import contents, read_text

from mako.lookup import TemplateLookup

from . import DATA_PACKAGE, PROG_NAME, __version__


class Renderer:
    def __init__(self):
        self._lookup = TemplateLookup()
        for tmpl in contents(DATA_PACKAGE):
            if tmpl.endswith('.mako'):
                self._lookup.put_string(tmpl, read_text(DATA_PACKAGE, tmpl))

    def __call__(self, name, **data):
        return self._lookup.get_template(name).render(
            progname=PROG_NAME, progversion=__version__, **data)
