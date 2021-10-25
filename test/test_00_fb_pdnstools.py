#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@license: LGPL3
@summary: test script (and module) for unit tests on fb-pdnstools base classes
'''

import os
import sys
import logging
import logging.handlers
import syslog

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
class TestPdnsToolsBase(FbPdnsToolsTestcase):

    # -------------------------------------------------------------------------
    def test_import_modules(self):

        LOG.info("Test importing main module ...")

        LOG.debug("Importing fb_logging ...")
        import fb_pdnstools

        LOG.debug("Version of fb_pdnstools: {!r}.".format(fb_pdnstools.__version__))

    # -------------------------------------------------------------------------
    def test_base_class(self):

        LOG.info("Testing base class BasePowerDNSHandler ...")

        from fb_pdnstools import BasePowerDNSHandler

        LOG.debug("Creating dummy PDNS handler on base of BasePowerDNSHandler ...")
        # Creating dummy class
        class DummyPowerDNSHandler(BasePowerDNSHandler):
            pass

        test_handler = DummyPowerDNSHandler(
            appname=self.appname, verbose=self.verbose)

        LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))


# =============================================================================
if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsToolsBase('test_import_modules', verbose))
    suite.addTest(TestPdnsToolsBase('test_base_class', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
