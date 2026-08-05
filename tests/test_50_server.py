#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on PDNS server class.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
@license: LGPL3
"""

import json
import logging
import logging.handlers
import os
import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, libdir)

# Third party modules
from fb_tools.common import pp

from general import FbPdnsToolsTestcase, get_arg_verbose, init_root_logger

import requests

import requests_mock

LOG = logging.getLogger("test_server")


# =============================================================================
class TestPdnsServer(FbPdnsToolsTestcase):
    """Testcase for tests on fb_pdnstools.server."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Print an empty line on each test method call."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def tearDown(self):
        """Do nothing. Hook for finishing actions on each test method call."""
        pass

    # -------------------------------------------------------------------------
    def test_import_modules(self):
        """Test import of module fb_pdnstools.server ..."""
        if self.verbose:
            print()
        LOG.info(self.get_method_doc())

        LOG.debug("Importing fb_pdnstools.api ...")
        import fb_pdnstools.api
        LOG.debug("Version of fb_pdnstools.api: {!r}.".format(fb_pdnstools.api.__version__))

        # LOG.debug("Importing fb_pdnstools.server ...")
        # import fb_pdnstools.server

        # LOG.debug("Version of fb_pdnstools.server: {!r}.".format(fb_pdnstools.zone.__version__))

        # LOG.info("Testing import of PowerDNSServer from fb_pdnstools.server ...")
        # from fb_pdnstools.server import PowerDNSServer

        # server = PowerDNSServer(appname=self.appname, verbose=self.verbose)
        # LOG.debug("Empty PowerDNSServer:\n{}".format(server))

    # -------------------------------------------------------------------------
    def set_mocking(self, obj, what=None):
        """
        Set mocking mode in the given server object.

        Also responses for some HTTP requests are prepared.
        """
        from fb_pdnstools.requestable import BasePdnsRequestableObject

        if not isinstance(obj, BasePdnsRequestableObject):
            msg = "Given object is not a BasePdnsRequestableObject object, but a {} instead.".format(
                obj.__class__.__name__
            )
            raise TypeError(msg)

        obj.mocked = True

        wtf = "all"
        if what is not None:
            wtf = what
        if self.verbose > 1:
            LOG.debug(f"Setting mock data {wtf!r}.")

        if what is None or what == "api_root":
            obj.mocking_paths.append(
                {"method": "GET", "url": "/api/v1", "text": json.dumps(self.api_root_data)}
            )

        if what is None or what == "server_list":
            slist = self.get_js_serverlist()
            obj.mocking_paths.append({"method": "GET", "url": "/api/v1/servers", "text": slist})

        if what is None or what == "server_localhost":
            s_localhost = self.get_js_serverlist(0)
            obj.mocking_paths.append(
                {"method": "GET", "url": "/api/v1/servers/localhost", "text": s_localhost}
            )

        if what is None or what == "zones":
            js_zones = self.get_js_zones()
            obj.mocking_paths.append(
                {
                    "method": "GET",
                    "url": "/api/v1/servers/localhost/zones",
                    "text": json.dumps(js_zones),
                }
            )

        if what is None or what == "zone_testing.com":
            js_zone = self.get_js_zone()
            obj.mocking_paths.append(
                {
                    "method": "GET",
                    "url": "/api/v1/servers/localhost/zones/testing.com.",
                    "text": json.dumps(js_zone),
                }
            )

        if what is None or what == "222.40.10.in-addr.arpa":
            js_zone_rev = self.get_js_zone_rev()
            obj.mocking_paths.append(
                {
                    "method": "GET",
                    "url": "/api/v1/servers/localhost/zones/222.40.10.in-addr.arpa.",
                    "text": json.dumps(js_zone_rev),
                }
            )

    # -------------------------------------------------------------------------
    def test_init_api_root(self):
        """Testing init of an API root object."""
        if self.verbose > 1:
            print()
        LOG.info(self.get_method_doc())

        from fb_pdnstools.api import PowerDnsApiRoot

        api = PowerDnsApiRoot(
            appname=self.appname,
            verbose=self.verbose,
            master_server=self.server_name,
            api_key=self.api_key,
            use_https=False,
        )

        if self.verbose > 1:
            LOG.debug("PowerDnsApiRoot: %s: {}".format(api))
            LOG.debug("PowerDnsApiRoot: %r: {!r}".format(api))
        if self.verbose > 2:
            LOG.debug("api.as_dict():\n{}".format(pp(api.as_dict())))

    # -------------------------------------------------------------------------
    def test_eeplore_api_root(self):
        """Test exploring of an API root."""
        if self.verbose > 1:
            print()
        LOG.info(self.get_method_doc())

        from fb_pdnstools.api import PowerDnsApiRoot

        api = PowerDnsApiRoot(
            appname=self.appname,
            verbose=self.verbose,
            master_server=self.server_name,
            api_key=self.api_key,
            use_https=False,
        )
        self.set_mocking(api, "api_root")
        self.set_mocking(api, "server_list")
        LOG.debug("PowerDnsApiRoot: %r: {!r}".format(api))
        if self.verbose > 1:
            LOG.debug("PowerDnsApiRoot: %s: {}".format(api))

        api.explore()

        if self.verbose > 1:
            LOG.debug("PowerDnsApiRoot: %s: {}".format(api))

    # -------------------------------------------------------------------------
    def test_get_serverlist(self):
        """Testing getting the list of servers of a mocked PDNS API."""
        if self.verbose > 1:
            print()
        LOG.info(self.get_method_doc())


    # -------------------------------------------------------------------------
    def test_get_serverversion(self):
        """Testing getting the server version of a mocked PDNS API."""
        if self.verbose > 1:
            print()
        LOG.info(self.get_method_doc())

        adapter = requests_mock.Adapter()
        session = requests.Session()
        session.mount("mock", adapter)

        from fb_pdnstools.server import PowerDNSServer

        pdns = PowerDNSServer(
            appname=self.appname,
            verbose=self.verbose,
            master_server=self.server_name,
            api_key=self.api_key,
            use_https=False,
        )
        self.set_mocking(pdns, "server_list")

        LOG.debug("PowerDNSServer  %r: {!r}".format(pdns))
        if self.verbose > 1:
            LOG.debug("PowerDNSServer: %s: {}".format(pdns))
        if self.verbose > 2:
            LOG.debug("pdns.as_dict():\n{}".format(pp(pdns.as_dict())))

    # -------------------------------------------------------------------------
    def test_get_zone(self):
        """Testing getting a zone from a mocked PDNS API."""
        if self.verbose > 1:
            print()
        LOG.info(self.get_method_doc())

        adapter = requests_mock.Adapter()
        session = requests.Session()
        session.mount("mock", adapter)

        from fb_pdnstools.server import PowerDNSServer
        from fb_pdnstools.zone import PowerDNSZone
        from fb_pdnstools.zonedict import PowerDNSZoneDict

        pdns = PowerDNSServer(
            appname=self.appname,
            verbose=self.verbose,
            master_server=self.server_name,
            api_key=self.api_key,
            use_https=False,
        )
        self.set_mocking(pdns)

        LOG.debug("PowerDNSServer  %r: {!r}".format(pdns))
        if self.verbose > 1:
            LOG.debug("PowerDNSServer: %s: {}".format(pdns))
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
        LOG.debug("Zone: %r: {!r}".format(zone))
        if self.verbose > 1:
            LOG.debug("Zone: %s: {}".format(zone))
        if self.verbose > 2:
            LOG.debug("zone.as_dict: {}".format(pp(zone.as_dict())))


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsServer("test_import_modules", verbose))
    suite.addTest(TestPdnsServer("test_init_api_root", verbose))
    suite.addTest(TestPdnsServer("test_eeplore_api_root", verbose))
    # suite.addTest(TestPdnsServer("test_get_zone", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
