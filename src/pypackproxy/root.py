import hashlib
import os
import re
import shutil
from collections import namedtuple
from datetime import datetime
from posixpath import join as path_join

import cherrypy
from packaging.version import parse as parse_version
from salmagundi.files import write_all
from salmagundi.strings import format_bin_prefix

from . import ROOT_PATH
from .utils import get_favicon_path
from .renderer import render

ProjectFile = namedtuple('ProjectFile', 'name url size mtime')

path = ROOT_PATH
storage = '/storage'
config = {
    '/': {},
    storage: {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': '.',
    },
    '/favicon.ico': {
        'tools.staticfile.on': True,
        'tools.staticfile.filename': get_favicon_path(),
    }
}
proj_nam_re = re.compile('^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$',
                         re.IGNORECASE)
hash_ext = '.sha256'
chunk_size = 8192
project_path = path_join(path, '/project/')


class Root:
    def __init__(self, cfg):
        if cfg['admin-pass']:
            self._password = cfg['admin-pass']
            config['/admin'] = {'tools.sessions.on': True,
                                'tools.sessions.name': 'admin_session_id',
                                'tools.sessions.timeout': cfg['admin-expire']}
        self._admin_enabled = bool(cfg['admin-pass'])
        self._storage = cfg['storage-path']
        self._project_url = cfg['project-url']

    @cherrypy.expose
    def index(self):
        return render(
            'index.html', admin_enabled=self._admin_enabled,
            project_base_url=project_path if self._project_url else None,
            projects=sorted(os.listdir(self._storage)))

    @cherrypy.expose
    def project(self, project):
        if self._project_url:
            raise cherrypy.HTTPRedirect(self._project_url.format(project))
        else:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def admin(self, project=None, newdir=None, delproj=None,
              delfiles=None, upfiles=None, passwd=None, logout=None):
        if not self._admin_enabled:
            raise cherrypy.HTTPError(404)
        message = None
        if logout:
            cherrypy.lib.sessions.expire()
            raise cherrypy.HTTPRedirect('/')
        if passwd == self._password:
            cherrypy.session['logged-in'] = True
        elif passwd:
            message = 'Login failed', True
        if not cherrypy.session.get('logged-in'):
            return render('login.html', message=message, logged_in=False)
        if project:
            if delproj:
                message = self._deldir(delproj)
            elif delfiles:
                message = self._delfiles(project, delfiles)
            elif upfiles:
                message = self._upload(project, upfiles)
            return render('project.html', project=project,
                          message=message, files=self._files(project),
                          logged_in=True)
        else:
            if newdir:
                message = self._newdir(newdir)
            return render(
                'overview.html', project_base_url='?project=',
                message=message, logged_in=True,
                projects=sorted(os.listdir(self._storage)))

    def _files(self, project):
        proj_path = os.path.join(self._storage, project)
        files = None
        if os.path.exists(proj_path):
            files = []
            with os.scandir(proj_path) as it:
                for entry in sorted(it, key=lambda e: parse_version(e.name)):
                    if entry.name.endswith(hash_ext):
                        continue
                    stat = entry.stat()
                    files.append(ProjectFile(
                        entry.name,
                        path_join(path, storage, project, entry.name),
                        format_bin_prefix('.1f', stat.st_size),
                        datetime.fromtimestamp(
                            stat.st_mtime).isoformat(' ', 'seconds')))
        return files

    def _delfiles(self, project, delfiles):
        if not isinstance(delfiles, list):
            delfiles = [delfiles]
        for file in delfiles:
            try:
                path = os.path.join(self._storage, project, file)
                os.remove(path)
                hash_path = path + hash_ext
                if os.path.exists(hash_path):
                    os.remove(hash_path)
            except OSError as ex:
                return str(ex), True
        return f'{len(delfiles)} file(s) deleted.', False

    def _deldir(self, deldir):
        try:
            shutil.rmtree(os.path.join(self._storage, deldir))
            return f'Project "{deldir}" deleted.', False
        except OSError as ex:
            return str(ex), True

    def _newdir(self, newdir):
        if not proj_nam_re.match(newdir):
            return _INVALID_NAME_MSG % newdir, True
        else:
            try:
                os.mkdir(os.path.join(self._storage, newdir))
                return f'Directory "{newdir}" created.', False
            except OSError as ex:
                return str(ex), True

    def _upload(self, project, files):
        if not isinstance(files, list):
            files = [files]
        if not all(file.filename.startswith(project + '-') for file in files):
            for file in files:
                file.file.close()
            return ('One or more files do not belong to this'
                    ' project. Upload cancelled!'), True
        try:
            for file in files:
                file_path = os.path.join(self._storage, project, file.filename)
                hash_data = hashlib.sha256()
                with file.file, open(file_path, 'wb') as fh:
                    while True:
                        chunk = file.file.read(chunk_size)
                        if not chunk:
                            break
                        fh.write(chunk)
                        hash_data.update(chunk)
                write_all(file_path + hash_ext, hash_data.hexdigest())
        except OSError as ex:
            return str(ex), True
        return f'{len(files)} file(s) uploaded.', False


_INVALID_NAME_MSG = '''Invalid project directory name: "%s"<br>
Permitted characters:
<ul style="margin:0px">
    <li>ASCII letters ([a-zA-Z])</li>
    <li>ASCII digits ([0-9])</li>
    <li>underscores (_)</li>
    <li>hyphens (-)</li>
    <li>periods (.)</li>
</ul>
Names must start and end with an ASCII letter or digit.
'''
