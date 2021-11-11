#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@license: LGPL3
@summary: test script (and module) for unit tests record classes
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

LOG = logging.getLogger('test_record')


# =============================================================================
class TestPdnsRecord(FbPdnsToolsTestcase):

    # -------------------------------------------------------------------------
    def test_import_modules(self):

        LOG.info("Test importing record module ...")

        LOG.debug("Importing fb_pdnstools.record ...")
        import fb_pdnstools.record

        LOG.debug("Version of fb_pdnstools.record: {!r}.".format(fb_pdnstools.record.__version__))

        LOG.info("Testing import of PowerDNSRecord from fb_pdnstools.record ...")
        from fb_pdnstools.record import PowerDNSRecord

        record = PowerDNSRecord(appname=self.appname, verbose=self.verbose)
        LOG.debug("Empty PowerDNSRecord:\n{}".format(record))


# =============================================================================
if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsRecord('test_import_modules', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
