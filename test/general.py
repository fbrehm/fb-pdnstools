#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@license: GPL3
@summary: general used functions an objects used for unit tests on
          the pdnstools python modules
"""

import os
import sys
import logging
import argparse
import json

from pathlib import Path

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

# Own modules
from fb_logging.colored import ColoredFormatter

# =============================================================================

LOG = logging.getLogger(__name__)


# =============================================================================
def get_arg_verbose():

    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-v", "--verbose", action="count",
        dest='verbose', help='Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose


# =============================================================================
def init_root_logger(verbose=0):

    root_log = logging.getLogger()
    root_log.setLevel(logging.WARNING)
    if verbose:
        root_log.setLevel(logging.INFO)
        if verbose > 1:
            root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if verbose:
        if verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)


# =============================================================================
class FbPdnsToolsTestcase(unittest.TestCase):

    # -------------------------------------------------------------------------
    def __init__(self, methodName='runTest', verbose=0):

        self._verbose = int(verbose)

        appname = os.path.basename(sys.argv[0]).replace('.py', '')
        self._appname = appname

        super(FbPdnsToolsTestcase, self).__init__(methodName)

        self.curdir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.zone_file = self.curdir / 'zone.js'
        self.zone_rev_file = self.curdir / 'zone-rev.js'
        self.zones_file = self.curdir / 'zones.js'
        self.a_rrset_file = self.curdir / 'rrset-a.js'
        self.a_rrset_file_comment = self.curdir / 'rrset-a-with-comment.js'
        self.mx_rrset_file = self.curdir / 'rrset-mx.js'
        self.soa_rrset_file = self.curdir / 'rrset-soa.js'

        self.server_name = 'pdns-master.testing.net'
        self.api_key = 'test123'

        self.open_args = {}
        if six.PY3:
            self.open_args['encoding'] = 'utf-8'
            self.open_args['errors'] = 'surrogateescape'

        self.server_version = '4.1.10-mocked'

        self.server_list_data = [
            {
                "config_url": "/api/v1/servers/localhost/config{/config_setting}",
                "daemon_type": "authoritative",
                "id": "localhost",
                "type": "Server",
                "url": "/api/v1/servers/localhost",
                "version": "{}".format(self.server_version),
                "zones_url": "/api/v1/servers/localhost/zones{/zone}"
            }
        ]

    # -------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    # -------------------------------------------------------------------------
    @property
    def appname(self):
        """The name of the current running application."""
        return self._appname

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    def get_js_a_rrset(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.a_rrset_file)))
        with self.a_rrset_file.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_a_rrset_comment(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.a_rrset_file_comment)))
        with self.a_rrset_file_comment.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_mx_rrset(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.mx_rrset_file)))
        with self.mx_rrset_file.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_soa_rrset(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.soa_rrset_file)))
        with self.soa_rrset_file.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_zone(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.zone_file)))
        with self.zone_file.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_zone_rev(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.zone_rev_file)))
        with self.zone_rev_file.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_zones(self):

        ret = None
        LOG.debug("Loading file {!r} ...".format(str(self.zones_file)))
        with self.zones_file.open('r', **self.open_args) as fh:
            ret = json.load(fh)
        return ret

    # -------------------------------------------------------------------------
    def get_js_serverlist(self, index=None):

        import json

        if index is None:
            data = self.server_list_data
        else:
            data = self.server_list_data[index]

        return json.dumps(data)


# =============================================================================
if __name__ == '__main__':

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
