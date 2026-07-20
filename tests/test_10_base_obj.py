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

    # -------------------------------------------------------------------------
    def test_import_modules(self):
        """Test import of modules fb_pdnstools.base."""
        LOG.info(self.get_method_doc())

        LOG.debug("Importing fb_pdnstools.base ...")
        import fb_pdnstools.base

        LOG.debug(
            "Version of fb_pdnstools.base: {!r}.".format(
                fb_pdnstools.base.__version__
            )
        )

    # -------------------------------------------------------------------------
    def test_base_handler_class(self):
        """Test instantiating of a BasePdnsObject with valid parameters."""
        LOG.info(self.get_method_doc())

        from fb_pdnstools.base import BasePdnsObject

        LOG.debug("Creating dummy PDNS handler on base of BasePdnsObject ...")

        # Creating dummy class
        class DummyPowerDNSHandler(BasePdnsObject):

            def __repr__(self):
                """Typecast into a string for reproduction."""
                return "<{}()>".format(self.__class__.__name__)

        test_handler = DummyPowerDNSHandler(appname=self.appname, verbose=self.verbose)

        LOG.debug("Dummy PDNS handler:\n{}".format(pp(test_handler.as_dict())))


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

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
