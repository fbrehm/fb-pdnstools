#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@license: LGPL3
@summary: test script (and module) for unit tests on PDNS server class
'''

import os
import sys
import logging
import logging.handlers
import json

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import requests
import requests_mock

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

from fb_tools.common import pp

from general import FbPdnsToolsTestcase, get_arg_verbose, init_root_logger

LOG = logging.getLogger('test_server')


# =============================================================================
class TestPdnsServer(FbPdnsToolsTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    def test_import_modules(self):

        if self.verbose:
            print()
        LOG.info("Test importing server module ...")

        LOG.debug("Importing fb_pdnstools.server ...")
        import fb_pdnstools.server

        LOG.debug("Version of fb_pdnstools.server: {!r}.".format(fb_pdnstools.zone.__version__))

        LOG.info("Testing import of PowerDNSServer from fb_pdnstools.server ...")
        from fb_pdnstools.server import PowerDNSServer

        server = PowerDNSServer(appname=self.appname, verbose=self.verbose)
        LOG.debug("Empty PowerDNSServer:\n{}".format(server))

    # -------------------------------------------------------------------------
    def set_mocking(self, obj):

        from fb_pdnstools import BasePowerDNSHandler

        if not isinstance(obj, BasePowerDNSHandler):
            msg = "Given object is not a BasePowerDNSHandler object, but a {} instead.".format(
                obj.__class__.__name__)
            raise TypeError(msg)

        obj.mocked = True

        slist = self.get_js_serverlist()
        obj.mocking_paths.append({
            'method': 'GET', 'url': '/api/v1/servers', 'text': slist})

        s_localhost = self.get_js_serverlist(0)
        obj.mocking_paths.append({
            'method': 'GET', 'url': '/api/v1/servers/localhost', 'text': s_localhost})

        js_zones = self.get_js_zones()
        obj.mocking_paths.append({
            'method': 'GET', 'url': '/api/v1/servers/localhost/zones',
            'text': json.dumps(js_zones)})

        js_zone = self.get_js_zone()
        obj.mocking_paths.append({
            'method': 'GET', 'url': '/api/v1/servers/localhost/zones/testing.com.',
            'text': json.dumps(js_zone)})

        js_zone_rev = self.get_js_zone_rev()
        obj.mocking_paths.append({
            'method': 'GET', 'url': '/api/v1/servers/localhost/zones/222.40.10.in-addr.arpa.',
            'text': json.dumps(js_zone_rev)})

    # -------------------------------------------------------------------------
    def test_get_zone(self):

        LOG.info("Testing getting a zone from a mocked PDNS API ...")

        adapter = requests_mock.Adapter()
        session = requests.Session()
        session.mount('mock', adapter)

        from fb_pdnstools.server import PowerDNSServer
        from fb_pdnstools.zone import PowerDNSZone, PowerDNSZoneDict

        pdns = PowerDNSServer(
            appname=self.appname, verbose=self.verbose, master_server=self.server_name,
            key=self.api_key, use_https=False)
        self.set_mocking(pdns)

        LOG.debug("PowerDNSServer  %%r: {!r}".format(pdns))
        if self.verbose > 1:
            LOG.debug("PowerDNSServer: %%s: {}".format(pdns))
        if self.verbose > 2:
            LOG.debug("pdns.as_dict():\n{}".format(pp(pdns.as_dict())))

        api_version = pdns.get_api_server_version()
        self.assertEqual(api_version, self.server_version)

        LOG.debug("Retreiving all zones ...")
        zones = pdns.get_api_zones()
        self.assertIsInstance(zones, PowerDNSZoneDict)
        self.assertIn("testing.com.", zones)

        LOG.debug("Retreiving zone {!r} ...".format("testing.com."))
        zone = zones["testing.com."]
        self.assertIsInstance(zone, PowerDNSZone)
        self.set_mocking(zone)
        LOG.debug("Updating zone {!r} ...".format("testing.com."))
        zone.update()
        LOG.debug("Zone: %%r: {!r}".format(zone))
        if self.verbose > 1:
            LOG.debug("Zone: %%s: {}".format(zone))
        if self.verbose > 2:
            LOG.debug("zone.as_dict: {}".format(pp(zone.as_dict())))


# =============================================================================
if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsServer('test_import_modules', verbose))
    suite.addTest(TestPdnsServer('test_get_zone', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
