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

        LOG.debug("Importing fb_pdnstools ...")
        import fb_pdnstools

        LOG.debug("Version of fb_pdnstools: {!r}.".format(fb_pdnstools.__version__))

        LOG.debug("Importing fb_pdnstools.errors ...")
        import fb_pdnstools.errors
        LOG.debug("Version of fb_pdnstools.errors: {!r}.".format(
            fb_pdnstools.errors.__version__))

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

    # -------------------------------------------------------------------------
    def test_error_classes(self):

        LOG.info("Testing loading and function of different error handler classes ...")

        LOG.debug("Testing PowerDNSHandlerError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PowerDNSHandlerError
        with self.assertRaises(PowerDNSHandlerError) as cm:
            raise PowerDNSHandlerError('bla')
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PowerDNSZoneError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PowerDNSZoneError
        with self.assertRaises(PowerDNSZoneError) as cm:
            raise PowerDNSZoneError('bla')
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PowerDNSRecordError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PowerDNSRecordError
        with self.assertRaises(PowerDNSRecordError) as cm:
            raise PowerDNSRecordError('bla')
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PowerDNSRecordSetError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PowerDNSRecordSetError
        with self.assertRaises(PowerDNSRecordSetError) as cm:
            raise PowerDNSRecordSetError('bla')
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PowerDNSWrongSoaDataError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PowerDNSWrongSoaDataError
        with self.assertRaises(PowerDNSWrongSoaDataError) as cm:
            raise PowerDNSWrongSoaDataError({'uhu': 'banane'})
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        msg = "Undfined test error"

        LOG.debug("Testing PDNSApiError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PDNSApiError
        uris = (None, 'https://pdnsmaster.uhu-banane.eu')
        code = 404
        for uri in uris:
            with self.assertRaises(PDNSApiError) as cm:
                raise PDNSApiError(code, msg, uri)
            e = cm.exception
            LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PDNSApiNotAuthorizedError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PDNSApiNotAuthorizedError
        with self.assertRaises(PDNSApiNotAuthorizedError) as cm:
            raise PDNSApiNotAuthorizedError(401, msg)
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PDNSApiNotFoundError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PDNSApiNotFoundError
        with self.assertRaises(PDNSApiNotFoundError) as cm:
            raise PDNSApiNotFoundError(404, msg)
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PDNSApiValidationError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PDNSApiValidationError
        with self.assertRaises(PDNSApiValidationError) as cm:
            raise PDNSApiValidationError(422, msg, 'https://pdnsmaster.uhu-banane.eu')
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PDNSApiRateLimitExceededError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PDNSApiRateLimitExceededError
        with self.assertRaises(PDNSApiRateLimitExceededError) as cm:
            raise PDNSApiRateLimitExceededError(429, msg)
        e = cm.exception
        LOG.debug("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))

        LOG.debug("Testing PDNSApiRequestError from fb_pdnstools.errors ...")
        from fb_pdnstools.errors import PDNSApiRequestError
        with self.assertRaises(PDNSApiRequestError) as cm:
            raise PDNSApiRequestError(419, 'I am not a tea pot.')
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

    suite.addTest(TestPdnsToolsBase('test_import_modules', verbose))
    suite.addTest(TestPdnsToolsBase('test_base_class', verbose))
    suite.addTest(TestPdnsToolsBase('test_error_classes', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
