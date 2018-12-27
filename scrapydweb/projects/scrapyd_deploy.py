# coding: utf8
"""
source: https://github.com/scrapy/scrapyd-client
scrapyd-client/scrapyd_client/deploy.py
"""
import os
import sys
import glob
import tempfile
from shutil import copyfile
from subprocess import check_call
import errno
try:
    from ConfigParser import SafeConfigParser  # PY2
except ImportError:
    from configparser import ConfigParser as SafeConfigParser  # PY3

from flask import current_app as app


_SETUP_PY_TEMPLATE = """# Automatically created by: scrapydweb x scrapyd-client

from setuptools import setup, find_packages

setup(
    name         = 'project',
    version      = '1.0',
    packages     = find_packages(),
    entry_points = {'scrapy': ['settings = %(settings)s']},
)
"""


def get_config(sources):
    """Get Scrapy config file as a SafeConfigParser"""
    # sources = get_sources(use_closest)
    cfg = SafeConfigParser()
    cfg.read(sources)
    return cfg


def retry_on_eintr(func, *args, **kw):
    """Run a function and retry it while getting EINTR errors"""
    while True:
        try:
            return func(*args, **kw)
        except IOError as e:
            if e.errno != errno.EINTR:
                raise


def _build_egg(scrapy_cfg_path):
    cwd = os.getcwd()
   # If get_config() raise an error without executing os.chdir(cwd), would cause subsequent test cases
   # to raise TemplateNotFound when testing in Debian or MacOS with python 2, PY2 and MACOS_DEBIAN.
   # Debug: add print(environment.list_templates()) in flask/templating.py _get_source_fast() would show []
    try:
        os.chdir(os.path.dirname(scrapy_cfg_path))

        if os.path.exists('setup.py'):
            copyfile('setup.py', 'setup_backup.py')
        # lib/configparser.py: def get(self, section, option, *, raw=False, vars=None, fallback=_UNSET):
        # projectname/scrapy.cfg: [settings] default = demo.settings
        settings = get_config(scrapy_cfg_path).get('settings', 'default')  # demo.settings
        _create_default_setup_py(settings=settings)

        d = tempfile.mkdtemp(prefix="scrapydweb-deploy-")
        o = open(os.path.join(d, "stdout"), "wb")
        e = open(os.path.join(d, "stderr"), "wb")
        retry_on_eintr(check_call, [sys.executable, 'setup.py', 'clean', '-a', 'bdist_egg', '-d', d],
                       stdout=o, stderr=e)
        egg = glob.glob(os.path.join(d, '*.egg'))[0]
        o.close()
        e.close()
    except:
        os.chdir(cwd)
        raise
    finally:
        os.chdir(cwd)

    return egg, d


def _create_default_setup_py(**kwargs):
    with open('setup.py', 'w') as f:
        content = _SETUP_PY_TEMPLATE % kwargs
        app.logger.debug('New setup.py')
        # app.logger.debug(content)
        f.write(content)
