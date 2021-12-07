#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@license: LGPL3
@summary: test script (and module) for unit tests on zone classes
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

LOG = logging.getLogger('test_zone')


# =============================================================================
class TestPdnsZone(FbPdnsToolsTestcase):

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

        LOG.debug("Importing fb_pdnstools.zone ...")
        import fb_pdnstools.zone

        LOG.debug("Version of fb_pdnstools.zone: {!r}.".format(fb_pdnstools.zone.__version__))

        LOG.info("Testing import of PowerDNSRecord from fb_pdnstools.record ...")
        from fb_pdnstools.zone import PowerDNSZone

        zone = PowerDNSZone(appname=self.appname, verbose=self.verbose)
        LOG.debug("Empty PowerDNSZone:\n{}".format(zone))

        LOG.info("Testing import of PowerDNSZoneDict from fb_pdnstools.record ...")
        from fb_pdnstools.zone import PowerDNSZoneDict

        zone_map = PowerDNSZoneDict()
        LOG.debug("Empty PowerDNSZoneDict: {}".format(zone_map))

    # -------------------------------------------------------------------------
    def test_verify_fqdn(self):

        if self.verbose:
            print()
        LOG.info("Testing PowerDNSZone.verify_fqdn() ...")

        valid_fqdns = [
            '@', 'testing.com.', 'uhu.testing.com.', ' uhu.testing.com.',
            'uhu.banane.testing.com.', 'UHU.TESTING.COM.']
        invalid_fqdns_type = [None, 33, True]
        invalid_fqdns_value = [
            '', '.', 'bla.@', 'testing.com', 'test.com.', '.testing.com', '.testing.com.',
            '4+5.testing.com.', '.uhu.testing.com.', 'uhu.testing.net.']

        from fb_pdnstools.zone import PowerDNSZone

        js_zone = self.get_js_zone()

        zone = PowerDNSZone.init_from_dict(
            js_zone, appname=self.appname, verbose=self.verbose)
        if self.verbose > 1:
            LOG.debug("Zone: %%r: {!r}".format(zone))
        if self.verbose > 2:
            LOG.debug("zone.as_dict():\n{}".format(pp(zone.as_dict())))

        for fqdn in valid_fqdns:
            LOG.debug("Testing FQDN {f!r} for zone {z!r} ...".format(f=fqdn, z=zone.name))
            got_fqdn = zone.verify_fqdn(fqdn)
            LOG.debug("Got verified FQDN {!r}.".format(got_fqdn))
            self.assertIsNotNone(got_fqdn)

        for fqdn in invalid_fqdns_type:
            LOG.debug("Testing raise on FQDN {f!r} for zone {z!r} ...".format(f=fqdn, z=zone.name))
            with self.assertRaises(TypeError) as cm:
                got_fqdn = zone.verify_fqdn(fqdn)
                LOG.error("This FQDN {!r} should never be visible.".format(got_fqdn))
            e = cm.exception
            LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

            LOG.debug("Testing returning None on FQDN {f!r} for zone {z!r} ...".format(
                f=fqdn, z=zone.name))
            got_fqdn = zone.verify_fqdn(fqdn, raise_on_error=False)
            LOG.debug("Got back {!r}.".format(got_fqdn))
            self.assertIsNone(got_fqdn)

        for fqdn in invalid_fqdns_value:
            LOG.debug("Testing raise on FQDN {f!r} for zone {z!r} ...".format(f=fqdn, z=zone.name))
            with self.assertRaises(ValueError) as cm:
                got_fqdn = zone.verify_fqdn(fqdn)
                LOG.error("This FQDN {!r} should never be visible.".format(got_fqdn))
            e = cm.exception
            LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

            LOG.debug("Testing returning None on FQDN {f!r} for zone {z!r} ...".format(
                f=fqdn, z=zone.name))
            got_fqdn = zone.verify_fqdn(fqdn, raise_on_error=False)
            LOG.debug("Got back {!r}.".format(got_fqdn))
            self.assertIsNone(got_fqdn)

    # -------------------------------------------------------------------------
    def test_zone_simple(self):

        LOG.info("Testing class PowerDNSZone ...")

        from fb_pdnstools.zone import PowerDNSZone

        js_zone = self.get_js_zone()

        PowerDNSZone.warn_on_unknown_property = True
        zone = PowerDNSZone.init_from_dict(
            js_zone, appname=self.appname, verbose=self.verbose)
        LOG.debug("Zone: %%r: {!r}".format(zone))
        if self.verbose > 1:
            LOG.debug("Zone: %%s: {}".format(zone))
            LOG.debug("zone.as_dict():\n{}".format(pp(zone.as_dict())))

    # -------------------------------------------------------------------------
    def test_zone_get_soa(self):

        LOG.info("Testing class PowerDNSZone.get_soa() ...")

        from fb_pdnstools.zone import PowerDNSZone

        js_zone = self.get_js_zone()

        PowerDNSZone.warn_on_unknown_property = True
        zone = PowerDNSZone.init_from_dict(
            js_zone, appname=self.appname, verbose=self.verbose)
        if self.verbose > 1:
            LOG.debug("Zone: %%r: {!r}".format(zone))

        soa = zone.get_soa()
        if self.verbose > 2:
            LOG.debug("Got SOA object:\n{}".format(pp(soa.as_dict())))
        self.assertIsNotNone(soa)
        self.assertEqual(soa.primary, 'ns1.example.com.')
        self.assertEqual(soa.email, 'hostmaster.example.com.')
        self.assertEqual(soa.serial, 2018061201)
        self.assertEqual(soa.refresh, 10800)
        self.assertEqual(soa.retry, 1800)
        self.assertEqual(soa.expire, 604800)
        self.assertEqual(soa.ttl, 3600)


# =============================================================================
if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestPdnsZone('test_import_modules', verbose))
    suite.addTest(TestPdnsZone('test_verify_fqdn', verbose))
    suite.addTest(TestPdnsZone('test_zone_simple', verbose))
    suite.addTest(TestPdnsZone('test_zone_get_soa', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
