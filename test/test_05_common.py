#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on common.py.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 Frank Brehm, Berlin
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

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

# Third party modules
# from fb_tools.common import pp

from general import FbPdnsToolsTestcase, get_arg_verbose, init_root_logger

LOG = logging.getLogger('test_common')


# =============================================================================
class TestPdnsCommon(FbPdnsToolsTestcase):
    """Testcase for tests on fb_pdnstools.common."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_import(self):
        """Testing import of module fb_pdnstools.common ..."""
        LOG.info('Test importing fb_pdnstools.common ...')

        LOG.debug('Importing fb_pdnstools.common ...')
        import fb_pdnstools.common

        LOG.debug('Version of fb_pdnstools.common: {!r}.'.format(
            fb_pdnstools.common.__version__))

    # -------------------------------------------------------------------------
    def test_seconds2human(self):
        """Testing public function seconds2human() from fb_pdnstools.common."""
        LOG.info('Testing seconds2human() from fb_pdnstools.common ...')

        from fb_pdnstools.common import seconds2human

        # Records of test_data_good:
        #   * seconds as input value
        #   * result without fs and all_fields
        #   * result with fs=' ', but without all_fields
        #   * result with fs=''_', but without all_fields
        #   * result without fs, but with all_fields
        #   * result with fs=' ' and with all_fields

        test_data_good = (
            (0, '0s', '0s', '0s', '0d0h0m0s', '0d 0h 0m 0s'),
            (1, '1s', '1s', '1s', '0d0h0m1s', '0d 0h 0m 1s'),
            (-1, '-1s', '- 1s', '-_1s', '-0d0h0m1s', '- 0d 0h 0m 1s'),
            (181, '3m1s', '3m 1s', '3m_1s', '0d0h3m1s', '0d 0h 3m 1s'),
            (600, '10m', '10m', '10m', '0d0h10m0s', '0d 0h 10m 0s'),
            (31267, '8h41m7s', '8h 41m 7s', '8h_41m_7s', '0d8h41m7s', '0d 8h 41m 7s'),
            (286623, '3d7h37m3s', '3d 7h 37m 3s', '3d_7h_37m_3s', '3d7h37m3s', '3d 7h 37m 3s'),
            ('31267', '8h41m7s', '8h 41m 7s', '8h_41m_7s', '0d8h41m7s', '0d 8h 41m 7s'),
            (b'31267', '8h41m7s', '8h 41m 7s', '8h_41m_7s', '0d8h41m7s', '0d 8h 41m 7s'),
        )

        LOG.debug('Testing good values ...')
        for data_row in test_data_good:

            if self.verbose > 1:
                msg = 'Testing seconds2human({v!r}, fs='', all_fields=False) => {r!r}'.format(
                    v=data_row[0], r=data_row[1])
                LOG.debug(msg)
            result = seconds2human(data_row[0], fs='', all_fields=False)
            if self.verbose > 1:
                LOG.debug('Result: {!r}'.format(result))
            self.assertEqual(result, data_row[1])

            if self.verbose > 1:
                msg = 'Testing seconds2human({v!r}, fs=' ', all_fields=False) => {r!r}'.format(
                    v=data_row[0], r=data_row[2])
                LOG.debug(msg)
            result = seconds2human(data_row[0], fs=' ', all_fields=False)
            if self.verbose > 1:
                LOG.debug('Result: {!r}'.format(result))
            self.assertEqual(result, data_row[2])

            if self.verbose > 1:
                msg = 'Testing seconds2human({v!r}, fs="_", all_fields=False) => {r!r}'.format(
                    v=data_row[0], r=data_row[3])
                LOG.debug(msg)
            result = seconds2human(data_row[0], fs='_', all_fields=False)
            if self.verbose > 1:
                LOG.debug('Result: {!r}'.format(result))
            self.assertEqual(result, data_row[3])

            if self.verbose > 1:
                msg = 'Testing seconds2human({v!r}, fs='', all_fields=True) => {r!r}'.format(
                    v=data_row[0], r=data_row[4])
                LOG.debug(msg)
            result = seconds2human(data_row[0], fs='', all_fields=True)
            if self.verbose > 1:
                LOG.debug('Result: {!r}'.format(result))
            self.assertEqual(result, data_row[4])

            if self.verbose > 1:
                msg = 'Testing seconds2human({v!r}, fs=' ', all_fields=True) => {r!r}'.format(
                    v=data_row[0], r=data_row[5])
                LOG.debug(msg)
            result = seconds2human(data_row[0], fs=' ', all_fields=True)
            if self.verbose > 1:
                LOG.debug('Result: {!r}'.format(result))
            self.assertEqual(result, data_row[5])


# =============================================================================
if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info('Starting tests ...')

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsCommon('test_import', verbose))
    suite.addTest(TestPdnsCommon('test_seconds2human', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
