#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on fb-pdnstools base handler class.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
@license: LGPL3
"""

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

# Own modules
from general import FbPdnsToolsTestcase, get_arg_verbose, init_root_logger

LOG = logging.getLogger("test_fb_pdnstools")


# =============================================================================
class TestPdnsBaseHandler(FbPdnsToolsTestcase):
    """Testcase for tests on fb_pdnstools.base_handler."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

        self.master_server = "dnsmaster01.uhu-banane.de"

    # -------------------------------------------------------------------------
    def test_import_modules(self):
        """Test import of modules fb_pdnstools.requestable."""
        LOG.info(self.get_method_doc())

        LOG.debug("Importing fb_pdnstools.requestable ...")
        import fb_pdnstools.requestable

        LOG.debug(
            "Version of fb_pdnstools.requestable: {!r}.".format(
                fb_pdnstools.requestable.__version__
            )
        )

    # -------------------------------------------------------------------------
    def test_base_handler_class(self):
        """Test instantiating of a BasePdnsRequestableObject with valid parameters."""
        LOG.info(self.get_method_doc())

        from fb_pdnstools.requestable import BasePdnsRequestableObject

        LOG.debug("Creating dummy PDNS handler on base of BasePdnsRequestableObject ...")

        # Creating dummy class
        class DummyPowerDNSHandler(BasePdnsRequestableObject):

            def __repr__(self):
                """Typecast into a string for reproduction."""
                return "<{}()>".format(self.__class__.__name__)

            def import_data(self, data):
                """Import the given data from PowerDNS API."""
                super(DummyPowerDNSHandler, self).import_data(data)

            def export_data(self):
                """Typecast PDNS relevant data into a dict for reproduction."""
                return {}

        test_handler = DummyPowerDNSHandler(
            master_server=self.master_server, appname=self.appname, verbose=self.verbose)

        LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))
        self.assertEqual(self.master_server, test_handler.master_server)

    # -------------------------------------------------------------------------
    def test_base_handler_wrong_params(self):
        """Test instantiating of a BasePowerDNSHandler with invalid parameters."""
        LOG.info(self.get_method_doc())

        from fb_pdnstools.requestable import BasePdnsRequestableObject

        LOG.debug("Creating dummy PDNS handler on base of BasePdnsRequestableObject ...")

        # Creating dummy class
        class DummyPowerDNSHandler(BasePdnsRequestableObject):

            def __repr__(self):
                """Typecast into a string for reproduction."""
                return "<{}()>".format(self.__class__.__name__)

            def import_data(self, data):
                """Import the given data from PowerDNS API."""
                super(DummyPowerDNSHandler, self).import_data(data)

            def export_data(self):
                """Typecast PDNS relevant data into a dict for reproduction."""
                return {}

        wrong_ports = ("uhu", 0, -10, 123456)

        for wrong_port in wrong_ports:
            LOG.debug("Testing with port {!r} ...".format(wrong_port))
            with self.assertRaises(ValueError) as cm:
                test_handler = DummyPowerDNSHandler(
                    appname=self.appname, verbose=self.verbose, port=wrong_port
                )
                LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))
            e = cm.exception
            LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        wrong_path_prefix = "uhu/banane"
        LOG.debug(f"Testing with wrong path_grefix {wrong_path_prefix!r} ...")
        with self.assertRaises(ValueError) as cm:
            test_handler = DummyPowerDNSHandler(
                appname=self.appname, verbose=self.verbose, path_prefix=wrong_path_prefix
            )
            LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsBaseHandler("test_import_modules", verbose))
    suite.addTest(TestPdnsBaseHandler("test_base_handler_class", verbose))
    suite.addTest(TestPdnsBaseHandler("test_base_handler_wrong_params", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
