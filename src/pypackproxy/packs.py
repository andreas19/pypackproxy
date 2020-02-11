import os
from posixpath import join as path_join
from urllib.parse import unquote as urlunquote

import cherrypy
import requests

from . import root, PACKS_PATH

path = PACKS_PATH
config = {'/': {}}
root_storage = path_join(root.path, root.storage)
chunk_size = 8192


class Packs:
    def __init__(self, cfg):
        self._storage = cfg['storage-path']
        self._proxies = cfg['proxies']
        self._timeout = cfg['timeout']
        self._headers = {'User-Agent': cfg['user-agent']}

    @cherrypy.expose
    def default(self, project, proto, *args):
        if proto not in ('http:', 'https:') and args:
            raise cherrypy.HTTPError(requests.codes.BAD_REQUEST)
        file = args[-1]
        file_path = os.path.join(self._storage, project, file)
        if not os.path.exists(file_path):
            url = f'{proto}//{urlunquote("/".join(args))}'
            try:
                r = requests.get(url, stream=True,
                                 headers=self._headers,
                                 proxies=self._proxies,
                                 timeout=self._timeout)
            except Exception as ex:
                msg = str(ex)
                cherrypy.log(msg)
                raise cherrypy.HTTPError(message=msg)
            if r.status_code == requests.codes.OK:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                resp_headers = cherrypy.response.headers
                resp_headers['Content-Type'] = r.headers['Content-Type']
                resp_headers['Content-Length'] = r.headers['Content-Length']
                return _content(r, file_path)
            else:
                raise cherrypy.HTTPError(r.status_code)
        else:
            raise cherrypy.HTTPRedirect(path_join(root_storage, project, file))


def _content(r, file_path):
    with open(file_path, 'wb') as fh:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fh.write(chunk)
            yield chunk
