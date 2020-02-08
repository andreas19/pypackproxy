import hashlib
import os
import re
import shutil
from datetime import datetime
from posixpath import join as path_join

import cherrypy
from packaging.version import parse as parse_version
from salmagundi.files import write_all
from salmagundi.strings import format_bin_prefix

from . import PROG_NAME, ROOT_PATH, __version__
from .utils import validate_password, get_favicon_path

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
            config['/admin'] = {
                'tools.auth_basic.on': True,
                'tools.auth_basic.realm': PROG_NAME,
                'tools.auth_basic.checkpassword': validate_password(
                    cfg['admin-user'], cfg['admin-pass']),
                'tools.auth_basic.accept_charset': 'UTF-8',
            }
        self._admin_enabled = bool(cfg['admin-pass'])
        self._storage = cfg['storage-path']
        self._project_url = cfg['project-url']

    @cherrypy.expose
    def index(self):
        projects, cnt = self._list_projects(project_path, self._project_url)
        if self._admin_enabled:
            content = '<a href="/admin/">Administration</a>\n'
        else:
            content = ''
        content += f'<h2>Locally stored projects: {cnt}</h2>\n'
        content += projects
        return _html(title='Start', content=content)

    @cherrypy.expose
    def project(self, project):
        if self._project_url:
            raise cherrypy.HTTPRedirect(self._project_url.format(project))
        else:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def admin(self, project=None, newdir=None, delproj=None,
              delfiles=None, upfiles=None):
        if not self._admin_enabled:
            raise cherrypy.HTTPError(404)
        content = '''<a href="/">Startpage</a>
        <h2>Administration</h2>
        '''
        if project:
            if delproj:
                content += self._deldir(delproj)
            elif delfiles:
                content += self._delfiles(project, delfiles)
            elif upfiles:
                content += self._upload(project, upfiles)
            content += self._project(project)
        else:
            if newdir:
                content += self._newdir(newdir)
            content += self._overview()
        return _html(title='Administration', content=content)

    def _overview(self):
        projects, cnt = self._list_projects('?project=')
        content = f'''<form method="post">
        New project directory
        <input type="text" name="newdir" autofocus required>
        <button>Create</button>
        </form><br>
        <h3>Locally stored projects: {cnt}</h3>
        '''
        content += projects
        return content

    def _project(self, project):
        proj_path = os.path.join(self._storage, project)
        content = '<a href="/admin">Overview</a>\n'
        if os.path.exists(proj_path):
            content += f'''<h3>Project: {project}</h3>
            <form method="post">
            <button id="delproj" name="delproj" value="{project}">Delete project</button>
            </form>
            {_confirm('delproj', f'Delete project "{project}" and all files?')}
            <h4>Files</h4>
            <form method="post" enctype="multipart/form-data">
            <button>Upload</button> files
            <input type="file" name="upfiles" multiple required>
            </form><br>

            <form method="post" id="delfilesform">
            <button id="delfiles">Delete files</button>
            <table style="border: 1px solid;border-collapse:collapse;margin-top:5px">
            '''  # noqa: E501
            lst = []
            with os.scandir(proj_path) as it:
                for entry in sorted(it, key=lambda e: parse_version(e.name)):
                    if entry.name.endswith(hash_ext):
                        continue
                    lst.append(_row(entry, project))
            content += '\n'.join(lst)
            content += f'''\n</table></form>
            {_CHKBXS_SCRIPT}
            {_confirm('delfiles', 'Delete files?')}
            '''
        return content

    def _list_projects(self, base, create_url=True):
        projects = sorted(os.listdir(self._storage))
        if create_url:
            return '<ul>' + '\n'.join(
                f'<li><a href="{base}{project}">{project}</a></li>'
                for project in projects) + '</ul>\n', len(projects)
        return '<ul>' + '\n'.join(
            f'<li>{project}</li>' for project in projects
            ) + '</ul>\n', len(projects)

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
                return _ERR_DIV % str(ex)
        return _SUC_DIV % f'{len(delfiles)} file(s) deleted.'

    def _deldir(self, deldir):
        try:
            shutil.rmtree(os.path.join(self._storage, deldir))
            return _SUC_DIV % f'Project "{deldir}" deleted.'
        except OSError as ex:
            return _ERR_DIV % str(ex)

    def _newdir(self, newdir):
        if not proj_nam_re.match(newdir):
            return _ERR_DIV % (_INVALID_NAME_MSG % newdir)
        else:
            try:
                os.mkdir(os.path.join(self._storage, newdir))
                return _SUC_DIV % f'Directory "{newdir}" created.'
            except OSError as ex:
                return _ERR_DIV % str(ex)

    def _upload(self, project, files):
        if not isinstance(files, list):
            files = [files]
        if not all(file.filename.startswith(project + '-') for file in files):
            for file in files:
                file.file.close()
            return _ERR_DIV % ('One or more files do not belong to this'
                               ' project. Upload cancelled!')
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
            return _ERR_DIV % str(ex)
        return _SUC_DIV % f'{len(files)} file(s) uploaded.'


def _confirm(id_, msg):
    return '''<script>
    document.getElementById("%(id)s").addEventListener("click", function(e) {
        if (!confirm('%(msg)s')) {
            e.preventDefault()
        }
    })
    </script>
    ''' % {'id': id_, 'msg': msg}


def _row(entry, project):
    stat = entry.stat()
    size = format_bin_prefix('.1f', stat.st_size)
    dt = datetime.fromtimestamp(stat.st_mtime).isoformat(' ', 'seconds')
    chkbx = f'<input type="checkbox" name="delfiles" value="{entry.name}">'
    url = path_join(path, storage, project, entry.name)
    name = f'<a href="{url}">{entry.name}</a>'
    lst = []
    for value in (chkbx, name, size, dt):
        lst.append(f'<td style="border:1px solid;padding:0px 2px">{value}</td>')
    return '<tr>' + ''.join(lst) + '</tr>'


def _html(**kwargs):
    return _HTML % kwargs


_HTML = f'''<!DOCTYPE html>
<html>
<head>
<title>{PROG_NAME} {__version__} - %(title)s</title>
</head>
<body>
<h1>{PROG_NAME}</h1>
%(content)s
</body>
</html>
'''

_MSG_DIV = ('<div style="color:%(color)s;border:solid 1px %(color)s;'
            'padding:2px;margin:0px 30px 20px 0px">%%s</div>')
_ERR_DIV = _MSG_DIV % dict(color='red')
_SUC_DIV = _MSG_DIV % dict(color='green')

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

_CHKBXS_SCRIPT = '''<script>
document.getElementById("delfiles").addEventListener("click", function(e) {
    var elems = document.forms.delfilesform.elements
    var cnt = 0
    for (let i = 0; i < elems.length; i++) {
        if (elems[i].type == 'checkbox' && elems[i].checked) {
            cnt += 1
        }
    }
    if (cnt == 0) {
        e.stopImmediatePropagation()
        e.preventDefault()
    }
})
</script>
'''
