#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 Frank Brehm, Berlin
@license: LGPL3
@summary: test script (and module) for unit tests on fb-pdnstools base handller class
'''

import os
import sys
import logging
import logging.handlers

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

from fb_tools.common import pp

from general import FbPdnsToolsTestcase, get_arg_verbose, init_root_logger

LOG = logging.getLogger('test_fb_pdnstools')


# =============================================================================
class TestPdnsBaseHandler(FbPdnsToolsTestcase):

    # -------------------------------------------------------------------------
    def test_import_modules(self):

        LOG.info("Test importing base handler module ...")

        LOG.debug("Importing fb_pdnstools.base_handler ...")
        import fb_pdnstools.base_handler

        LOG.debug("Version of fb_pdnstools.base_handler: {!r}.".format(
            fb_pdnstools.base_handler.__version__))

    # -------------------------------------------------------------------------
    def test_base_handler_class(self):

        LOG.info("Testing base class BasePowerDNSHandler ...")

        from fb_pdnstools.base_handler import BasePowerDNSHandler

        LOG.debug("Creating dummy PDNS handler on base of BasePowerDNSHandler ...")

        # Creating dummy class
        class DummyPowerDNSHandler(BasePowerDNSHandler):
            pass

        test_handler = DummyPowerDNSHandler(
            appname=self.appname, verbose=self.verbose)

        LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))

    # -------------------------------------------------------------------------
    def test_base_handler_wrong_params(self):

        LOG.info("Testing base class BasePowerDNSHandler with wrong parameters ...")

        from fb_pdnstools.base_handler import BasePowerDNSHandler

        LOG.debug("Creating dummy PDNS handler on base of BasePowerDNSHandler ...")

        # Creating dummy class
        class DummyPowerDNSHandler(BasePowerDNSHandler):
            pass

        wrong_ports = ('uhu', 0, -10, 123456)

        for wrong_port in wrong_ports:
            LOG.debug("Testing with port {!r} ...".format(wrong_port))
            with self.assertRaises(ValueError) as cm:
                test_handler = DummyPowerDNSHandler(
                    appname=self.appname, verbose=self.verbose, port=wrong_port)
                LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))
            e = cm.exception
            LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))


# =============================================================================
if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsBaseHandler('test_import_modules', verbose))
    suite.addTest(TestPdnsBaseHandler('test_base_handler_class', verbose))
    suite.addTest(TestPdnsBaseHandler('test_base_handler_wrong_params', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
