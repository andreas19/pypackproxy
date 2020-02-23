import os
from importlib.resources import open_text
from logging.handlers import RotatingFileHandler
from urllib.parse import urlunparse

import cherrypy
import salmagundi.config
from cherrypy.process.plugins import Daemonizer, PIDFile, DropPrivileges
from salmagundi.strings import split_host_port

from . import __version__, PYPP_DEBUG, PROG_NAME, DATA_PACKAGE
from .utils import (check_path, check_url, file_size, check_passwd,
                    pos_float, pos_int)


_CONFIG_SPEC = (DATA_PACKAGE, 'config_spec.ini')
_CONVERTERS = {'hostport': split_host_port,
               'filesize': file_size,
               'passwd': check_passwd,
               'posfloat': pos_float,
               'posint': pos_int}


def configure(cfgfile):
    with open_text(*_CONFIG_SPEC) as fh:
        cfg = salmagundi.config.configure(cfgfile, fh, create_properties=False,
                                          converters=_CONVERTERS)
    _logging(cfg)
    _storage_path(cfg)
    _index_url(cfg)
    _project_url(cfg)
    _ssl(cfg)
    host, port = cfg['server', 'host']
    cherrypy.config.update({
        'response.headers.Server': f'{PROG_NAME}/{__version__}',
        'server.socket_host': host,
        'server.socket_port': port,
        'engine.autoreload.on': False,
        'request.show_tracebacks': PYPP_DEBUG,
        'request.show_mismatched_params': PYPP_DEBUG,
    })
    if PYPP_DEBUG:
        cherrypy.engine.signal_handler.handlers['SIGUSR2'] =\
            lambda: cherrypy.engine.restart()
    if cfg['server', 'daemonize']:
        Daemonizer(cherrypy.engine).subscribe()
        cherrypy.engine.signal_handler.handlers['SIGUSR1'] = None
    if os.getuid() == 0:
        uid, gid = _user_group(cfg)
        if uid:
            DropPrivileges(cherrypy.engine, uid=uid, gid=gid).subscribe()
        else:
            cherrypy.log("running as 'root'", 'WARNING')
    if cfg['server', 'pidfile']:
        PIDFile(cherrypy.engine, cfg['server', 'pidfile']).subscribe()
    rv = {opt: cfg['pypackproxy', opt] for opt in cfg.options('pypackproxy')}
    rv['proxies'] = _proxies(cfg)
    rv['user-agent'] = f'{PROG_NAME}/{__version__}'
    return rv


def _storage_path(cfg):
    path = cfg['pypackproxy', 'storage-path']
    check_path(path, 'storage-path')
    cherrypy.config.update({'tools.staticdir.root': path})


def _index_url(cfg):
    index_url = cfg['pypackproxy', 'index-url']
    if not index_url or index_url.lower() == 'false':
        cfg['pypackproxy', 'index-url'] = False
        return
    check_url(index_url, 'index-url')


def _project_url(cfg):
    project_url = cfg['pypackproxy', 'project-url']
    if not project_url or project_url.lower() == 'false':
        cfg['pypackproxy', 'project-url'] = False
        return
    check_url(project_url, 'project-url')
    if '{}' not in project_url:
        raise RuntimeError('project-url must contain a placeholder {}')


def _ssl(cfg):
    if (bool(cfg['server', 'ssl_certificate']) ^
            bool(cfg['server', 'ssl_private_key'])):
        raise RuntimeError('certificate and private key both needed for SSL')
    cherrypy.server.ssl_module = 'builtin'
    cherrypy.server.ssl_certificate = cfg['server', 'ssl_certificate']
    cherrypy.server.ssl_private_key = cfg['server', 'ssl_private_key']
    if cfg['server', 'ssl_certificate_chain']:
        cherrypy.server.ssl_certificate_chain = cfg[
            'server', 'ssl_certificate_chain']


def _user_group(cfg):
    import pwd
    import grp
    user = cfg['server', 'user']
    group = cfg['server', 'group']
    if not user:
        return None, None
    try:
        try:
            uid = int(user)
            pwd.getpwuid(uid)
        except ValueError:
            uid = pwd.getpwnam(user).pw_uid
    except KeyError:
        raise RuntimeError(f'unknown user: {user}')
    if group:
        try:
            try:
                gid = int(group)
                grp.getgrgid(gid)
            except ValueError:
                gid = grp.getgrnam(group).gr_gid
        except KeyError:
            raise RuntimeError(f'unknown group: {group}')
    else:
        gid = pwd.getpwuid(uid).pw_gid
    return uid, gid


def _proxies(cfg):
    if cfg['proxy', 'proxy-url']:
        parsed = check_url(cfg['proxy', 'proxy-url'], 'proxy-url')
        if cfg['proxy', 'proxy-user']:
            netloc = cfg["proxy", "proxy-user"]
            if cfg['proxy', 'proxy-pass']:
                netloc += ':' + cfg['proxy', 'proxy-pass']
            netloc += f'@{parsed.hostname}:{parsed.port}'
            proxy_url = urlunparse(parsed._replace(netloc=netloc))
        else:
            proxy_url = cfg['proxy', 'proxy-url']
        return {'http': proxy_url, 'https': proxy_url}


def _logging(cfg):
    cherrypy.config.update({'log.screen': PYPP_DEBUG,
                            'log.access_file': '',
                            'log.error_file': ''})
    cherrypy.engine.unsubscribe('graceful', cherrypy.log.reopen_files)
    acc_path = cfg['logging', 'access-file']
    if acc_path:
        check_path(os.path.dirname(acc_path), 'access-file path')
        handler = RotatingFileHandler(acc_path, 'a',
                                      cfg['logging', 'access-size'],
                                      cfg['logging', 'access-count'])
        cherrypy.log.access_log.addHandler(handler)
    msg_path = cfg['logging', 'message-file']
    if msg_path:
        check_path(os.path.dirname(msg_path), 'message-file path')
        handler = RotatingFileHandler(msg_path, 'a',
                                      cfg['logging', 'message-size'],
                                      cfg['logging', 'message-count'])
        handler.addFilter(
            lambda record: 0 if 'NATIVE_ADAPTER' in record.msg else 1)
        cherrypy.log.error_log.addHandler(handler)
