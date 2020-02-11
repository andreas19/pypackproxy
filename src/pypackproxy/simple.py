import os
import re
from posixpath import join as path_join
from urllib.parse import quote as urlquote, urljoin

import cherrypy
import requests
from packaging.version import parse as parse_version
from salmagundi.files import read_all

from . import root, SIMPLE_PATH
from .packs import path as packs_path

path = SIMPLE_PATH
config = {'/': {}}
replace_re = re.compile(
    '<a href=(?P<quote>[\'"])(?P<url>.+?)(?:#(?P<hash>.+?))?(?P=quote)')
search_re = re.compile('>(.+?)</a>')
root_storage = path_join(root.path, root.storage)
hash_ext = root.hash_ext


class Simple:
    def __init__(self, cfg):
        self._index_url = cfg['index-url']
        if self._index_url and not self._index_url.endswith('/'):
            self._index_url += '/'
        self._storage = cfg['storage-path']
        self._proxies = cfg['proxies']
        self._timeout = cfg['timeout']
        self._retries = cfg['retries']
        self._headers = {'User-Agent': cfg['user-agent']}

    @cherrypy.expose
    def default(self, project):
        response = None
        if self._index_url:
            for i in range(self._retries + 1):
                try:
                    response = requests.get(f'{self._index_url}{project}/',
                                            headers=self._headers,
                                            proxies=self._proxies,
                                            timeout=self._timeout)
                    break
                except requests.ConnectionError as ex:
                    if i == self._retries:
                        cherrypy.log(str(ex) + ' (quit)')
                        break
                    else:
                        cherrypy.log(str(ex) + ' (retry)')
                except Exception as ex:
                    msg = str(ex)
                    cherrypy.log(msg)
                    raise cherrypy.HTTPError(message=msg)
        project_path = os.path.join(self._storage, project)
        if not response or response.status_code == requests.codes.NOT_FOUND:
            return self._local(project, project_path)
        elif response and response.status_code == requests.codes.OK:
            return self._remote(project, project_path, response)
        else:
            raise cherrypy.HTTPError(response.status_code)

    def _local(self, project, project_path):
        if os.path.exists(project_path):
            lines = []
            for file in sorted(os.listdir(project_path), key=parse_version):
                if file.endswith(hash_ext):
                    continue
                url = path_join(root_storage, project, file)
                hash_file = os.path.join(project_path, file + hash_ext)
                if os.path.exists(hash_file):
                    url += '#' + read_all(hash_file).strip()
                lines.append(f'<a href="{url}">{file}</a><br>')
            if lines:
                return _HTML % dict(project=project, content='\n'.join(lines))
        raise cherrypy.HTTPError(requests.codes.NOT_FOUND)

    def _remote(self, project, project_path, response):
        def replace(m):
            return self._replace(m, project)
        if os.path.exists(project_path):
            def replace_local(m):
                return self._replace(m, project, True)
            local_files = self._local_files(project_path)
            lines = []
            for line in response.text.splitlines():
                if '<a ' in line:
                    file = search_re.search(line)[1]
                    if file in local_files:
                        item = (file, replace_re.sub(replace_local, line))
                        del local_files[file]
                    else:
                        item = (file, replace_re.sub(replace, line))
                    lines.append(item)
            for file in local_files:
                url = path_join(root_storage, project, file)
                hash_data = local_files[file]
                if hash_data:
                    url += '#' + hash_data
                lines.append((file, f'<a href="{url}">{file}</a><br>'))
            lines.sort(key=lambda x: parse_version(x[0]))
            content = '\n'.join(line[1] for line in lines)
            return _HTML % dict(project=project, content=content)
        return replace_re.sub(replace, response.text)

    def _local_files(self, project_path):
        rv = {}
        for file in os.listdir(project_path):
            if file.endswith(hash_ext):
                continue
            hash_file = os.path.join(project_path, file + hash_ext)
            if os.path.exists(hash_file):
                hash_data = read_all(hash_file).strip()
            else:
                hash_data = None
            rv[file] = hash_data
        return rv

    def _replace(self, m, project, local=False):
        if local:
            url = path_join(root_storage, project, m['url'].rsplit('/', 1)[-1])
            if m['hash']:
                return f'<a href="{url}#{m["hash"]}"'
            else:
                return f'<a href="{url}"'
        else:
            url = urljoin(self._index_url, m['url'])
            if m['hash']:
                return (f'<a href="{packs_path}/{project}/'
                        f'{urlquote(url)}#{m["hash"]}"')
            else:
                return f'<a href="{packs_path}/{project}/{urlquote(url)}"'


_HTML = '''<!DOCTYPE html>
<html><head><title>Links for %(project)s</title></head><body>
<h1>Links for %(project)s</h1>
%(content)s
</body></html>
'''
