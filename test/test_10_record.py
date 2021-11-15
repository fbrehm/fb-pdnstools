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
import datetime

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
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    def test_import_modules(self):

        if self.verbose:
            print()
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

        if self.verbose:
            print()
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

        if self.verbose:
            print()
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

        if self.verbose:
            print()
        LOG.info("Testing the greater than operator of class PowerDNSRecord ...")

        test_content = "www.1testing.com."
        test_content2 = "www.2uhu-banane.com."
        test_content3 = "www.1Testing.com."

        from fb_pdnstools.record import PowerDNSRecord

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

        if self.verbose:
            print()
        LOG.info("Testing the less than operator of class PowerDNSRecord ...")

        test_content = "www.1testing.com."
        test_content2 = "www.2uhu-banane.com."
        test_content3 = "www.1Testing.com."

        from fb_pdnstools.record import PowerDNSRecord

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

    # -------------------------------------------------------------------------
    def test_pdns_recordset_comment(self):

        if self.verbose:
            print()
        LOG.info("Testing class PowerDNSRecordSetComment ...")

        test_account = 'tester'
        test_content = "Test comment"
        test_modified_at = 1000 * 24 * 60 * 60

        from fb_pdnstools.record import PowerDNSRecordSetComment

        LOG.debug("Creating an empty, invalid comment.")
        empty_comment = PowerDNSRecordSetComment(
            appname=self.appname, verbose=self.verbose)
        LOG.debug("Empty comment: %%r: {!r}".format(empty_comment))
        LOG.debug("Empty comment: %%s: {}".format(empty_comment))
        if self.verbose > 1:
            LOG.debug("Empty comment.as_dict():\n{}".format(pp(empty_comment.as_dict())))
        LOG.debug("Empty comment.as_dict(minimal=True): {}".format(
            pp(empty_comment.as_dict(minimal=True))))
        self.assertIsNone(empty_comment.account)
        self.assertEqual(empty_comment.content, '')
        self.assertIsInstance(empty_comment.modified_at, int)
        self.assertGreaterEqual(empty_comment.modified_at, 0)
        self.assertIsInstance(empty_comment.modified_date, datetime.datetime)
        self.assertFalse(empty_comment.valid)
        del empty_comment

        LOG.debug("Creating an non empty, valid comment.")
        comment = PowerDNSRecordSetComment(
            appname=self.appname, verbose=self.verbose, account=test_account, content=test_content)
        LOG.debug("Comment: %%r: {!r}".format(comment))
        LOG.debug("Comment: %%s: {}".format(comment))
        if self.verbose > 1:
            LOG.debug("Comment.as_dict():\n{}".format(pp(comment.as_dict())))
        LOG.debug("Comment.as_dict(minimal=True): {}".format(
            pp(comment.as_dict(minimal=True))))
        self.assertEqual(comment.account, test_account)
        self.assertEqual(comment.content, test_content)
        self.assertIsInstance(comment.modified_at, int)
        self.assertGreaterEqual(comment.modified_at, 0)
        self.assertIsInstance(comment.modified_date, datetime.datetime)
        self.assertTrue(comment.valid)

        LOG.debug("Creating a comment with a defined modified_at property.")
        comment = PowerDNSRecordSetComment(
            appname=self.appname, verbose=self.verbose,
            account=test_account, content=test_content, modified_at=test_modified_at)
        LOG.debug("Comment: %%s: {}".format(comment))
        if self.verbose > 1:
            LOG.debug("Comment: %%r: {!r}".format(comment))
        if self.verbose > 2:
            LOG.debug("Ccomment.as_dict():\n{}".format(pp(comment.as_dict())))
        self.assertIsInstance(comment.modified_at, int)
        self.assertEqual(comment.modified_at, test_modified_at)
        self.assertIsInstance(comment.modified_date, datetime.datetime)

        LOG.debug("Testing raising errors on wrong (String) modified_at property.")
        with self.assertRaises(ValueError) as cm:
            comment = PowerDNSRecordSetComment(
                appname=self.appname, verbose=self.verbose,
                account=test_account, content=test_content, modified_at='bla')
        e = cm.exception
        LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

        LOG.debug("Testing raising errors on wrong (negative) modified_at property.")
        with self.assertRaises(ValueError) as cm:
            comment = PowerDNSRecordSetComment(
                appname=self.appname, verbose=self.verbose,
                account=test_account, content=test_content, modified_at=-100)
        e = cm.exception
        LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

    # -------------------------------------------------------------------------
    def test_pdns_recordset_simple(self):

        if self.verbose:
            print()
        LOG.info("Testing class PowerDNSRecordSet ...")

        from fb_pdnstools.record import PowerDNSRecordSet

        js_rrset = self.get_js_a_rrset()

        rrset = PowerDNSRecordSet.init_from_dict(
            js_rrset, appname=self.appname, verbose=self.verbose)
        LOG.debug("RecordSet: %%r: {!r}".format(rrset))
        if self.verbose > 1:
            LOG.debug("RecordSet: %%s: {}".format(rrset))
            LOG.debug("rrset.as_dict():\n{}".format(pp(rrset.as_dict())))
        LOG.debug("RecordSet.as_dict(minimal=True): {}".format(
            pp(rrset.as_dict(minimal=True))))

    # -------------------------------------------------------------------------
    def test_pdns_recordset_with_comment(self):

        if self.verbose:
            print()
        LOG.info("Testing class PowerDNSRecordSet with comments ...")

        from fb_pdnstools.record import PowerDNSRecordSet

        js_rrset = self.get_js_a_rrset_comment()

        rrset = PowerDNSRecordSet.init_from_dict(
            js_rrset, appname=self.appname, verbose=self.verbose)
        LOG.debug("RecordSet: %%r: {!r}".format(rrset))
        if self.verbose > 1:
            LOG.debug("RecordSet: %%s: {}".format(rrset))
            LOG.debug("rrset.as_dict():\n{}".format(pp(rrset.as_dict())))
        LOG.debug("RecordSet.as_dict(minimal=True): {}".format(
            pp(rrset.as_dict(minimal=True))))


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
    suite.addTest(TestPdnsRecord('test_pdns_recordset_comment', verbose))
    suite.addTest(TestPdnsRecord('test_pdns_recordset_simple', verbose))
    suite.addTest(TestPdnsRecord('test_pdns_recordset_with_comment', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
