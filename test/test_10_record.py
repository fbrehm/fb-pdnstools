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

    # -------------------------------------------------------------------------
    def test_pdns_record(self):

        LOG.info("Testing class PowerDNSRecord ...")

        test_content = "www.testing.com."

        from fb_pdnstools.record import PowerDNSRecord

        LOG.debug("Creating an empty record.")
        record = PowerDNSRecord(
                appname=self.appname, verbose=self.verbose)
        LOG.debug("Record: %%r: {!r}".format(record))
        if self.verbose > 1:
            LOG.debug("Record: %%s: {}".format(record))
            LOG.debug("record.as_dict():\n{}".format(pp(record.as_dict())))
        self.assertIsNone(record.content)
        self.assertIsInstance(record.disabled, bool)
        self.assertFalse(record.disabled)

        LOG.debug("Creating an enabled record.")
        record = PowerDNSRecord(
            appname=self.appname, verbose=self.verbose, content=test_content)
        LOG.debug("Record: %%r: {!r}".format(record))
        if self.verbose > 1:
            LOG.debug("Record: %%s: {}".format(record))
            LOG.debug("record.as_dict():\n{}".format(pp(record.as_dict())))
        self.assertEqual(record.content, test_content)
        self.assertIsInstance(record.disabled, bool)
        self.assertFalse(record.disabled)

        LOG.debug("Creating a disabled record.")
        record = PowerDNSRecord(
            appname=self.appname, verbose=self.verbose, content=test_content, disabled=True)
        LOG.debug("Record: %%r: {!r}".format(record))
        LOG.debug("Record: %%s: {}".format(record))
        if self.verbose > 1:
            LOG.debug("record.as_dict():\n{}".format(pp(record.as_dict())))
        self.assertEqual(record.content, test_content)
        self.assertIsInstance(record.disabled, bool)
        self.assertTrue(record.disabled)

    # -------------------------------------------------------------------------
    def test_pdns_record_equality(self):

        LOG.info("Testing equal operator of class PowerDNSRecord ...")

        test_content = "www.testing.com."
        test_content2 = "www.uhu-banane.com."
        test_content3 = "www.Testing.com."

        from fb_pdnstools.record import PowerDNSRecord

        test_matrix = (
            (None, None, True),
            (test_content, None, False),
            (None, test_content, False),
            (test_content, test_content, True),
            (test_content, test_content2, False),
            (test_content, test_content3, True),
        )
        for test_set in test_matrix:
            rec1 = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_set[0])
            rec2 = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_set[1])
            expected = test_set[2]
            LOG.debug(
                "Comparing equality of record {r1!r} and record {r2!r}, expected: {ex}.".format(
                    r1=rec1.content, r2=rec2.content, ex=expected))
            if rec1 == rec2:
                result = True
            else:
                result = False
            LOG.debug("Result: {}".format(result))
            if expected:
                self.assertTrue(result)
            else:
                self.assertFalse(result)

    # -------------------------------------------------------------------------
    def test_pdns_record_gt(self):

        LOG.info("Testing the greater than operator of class PowerDNSRecord ...")

        test_content = "www.1testing.com."
        test_content2 = "www.2uhu-banane.com."
        test_content3 = "www.1Testing.com."

        from fb_pdnstools.record import PowerDNSRecord
        from fb_pdnstools.errors import PowerDNSWrongRecordTypeError

        LOG.debug("Testing the greater than operator with wrong argument ...")
        record = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_content)
        test_matrix = (
            (record, 'uhu'),
            (88, record)
        )
        for test_set in test_matrix:
            with self.assertRaises(TypeError) as cm:
                LOG.debug("Comparing {r1!r} with {r2!r} ...".format(
                    r1=test_set[0], r2=test_set[1]))
                if test_set[0] > test_set[1]:
                    print("This should not be visible!")
            e = cm.exception
            LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

        test_matrix = (
            (None, None, False),
            (test_content, None, True),
            (None, test_content, False),
            (test_content, test_content, False),
            (test_content, test_content2, False),
            (test_content2, test_content, True),
            (test_content, test_content3, False),
        )

        for test_set in test_matrix:
            rec1 = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_set[0])
            rec2 = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_set[1])
            expected = test_set[2]
            LOG.debug(
                "Comparing record {r1!r} > record {r2!r}, expected: {ex}.".format(
                    r1=rec1.content, r2=rec2.content, ex=expected))
            if rec1 > rec2:
                result = True
            else:
                result = False
            LOG.debug("Result: {}".format(result))
            if expected:
                self.assertTrue(result)
            else:
                self.assertFalse(result)

    # -------------------------------------------------------------------------
    def test_pdns_record_lt(self):

        LOG.info("Testing the less than operator of class PowerDNSRecord ...")

        test_content = "www.1testing.com."
        test_content2 = "www.2uhu-banane.com."
        test_content3 = "www.1Testing.com."

        from fb_pdnstools.record import PowerDNSRecord
        from fb_pdnstools.errors import PowerDNSWrongRecordTypeError

        LOG.debug("Testing the less than operator with wrong argument ...")
        record = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_content)
        test_matrix = (
            (record, 'uhu'),
            (88, record)
        )
        for test_set in test_matrix:
            with self.assertRaises(TypeError) as cm:
                LOG.debug("Comparing {r1!r} with {r2!r} ...".format(
                    r1=test_set[0], r2=test_set[1]))
                if test_set[0] < test_set[1]:
                    print("This should not be visible!")
            e = cm.exception
            LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

        test_matrix = (
            (None, None, False),
            (test_content, None, False),
            (None, test_content, True),
            (test_content, test_content, False),
            (test_content, test_content2, True),
            (test_content2, test_content, False),
            (test_content, test_content3, False),
        )

        for test_set in test_matrix:
            rec1 = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_set[0])
            rec2 = PowerDNSRecord(appname=self.appname, verbose=self.verbose, content=test_set[1])
            expected = test_set[2]
            LOG.debug(
                "Comparing record {r1!r} < record {r2!r}, expected: {ex}.".format(
                    r1=rec1.content, r2=rec2.content, ex=expected))
            if rec1 < rec2:
                result = True
            else:
                result = False
            LOG.debug("Result: {}".format(result))
            if expected:
                self.assertTrue(result)
            else:
                self.assertFalse(result)

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
    suite.addTest(TestPdnsRecord('test_pdns_record', verbose))
    suite.addTest(TestPdnsRecord('test_pdns_record_equality', verbose))
    suite.addTest(TestPdnsRecord('test_pdns_record_gt', verbose))
    suite.addTest(TestPdnsRecord('test_pdns_record_lt', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
