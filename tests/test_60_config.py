#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on module fb_pdnstools.config.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2026 Frank Brehm, Berlin
@license: GPL3
"""

import logging
import os
import sys
import textwrap
import uuid
from pathlib import Path, PosixPath

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from fb_tools.common import pp

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, libdir)

from general import FbPdnsToolsTestcase, get_arg_verbose, init_root_logger

LOG = logging.getLogger("test-config")


# =============================================================================
class TestPdnsConfig(FbPdnsToolsTestcase):
    """Testcase for unit tests on VmwareConfiguration objects."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        super(TestPdnsConfig, self).setUp()

        self.test_dir = Path(__file__).parent.resolve()
        self.base_dir = self.test_dir.parent
        self.test_cfg_dir = self.test_dir / "test-config"
        self._appname = "test-config"

    # -------------------------------------------------------------------------
    def tearDown(self):
        """Tear down routine for calling each particular test method."""
        pass

    # -------------------------------------------------------------------------
    def test_import(self):
        """Test import of fb_vmware.config."""
        LOG.info(self.get_method_doc())

        import fb_pdnstools.config

        LOG.debug("Version of fb_pdnstools.config: " + fb_pdnstools.config.__version__)

        LOG.info("Testing import of VmwareConfigError from fb_pdnstools.config ...")
        from fb_pdnstools.config import PowerDNSConfigError
        doc = textwrap.dedent(PowerDNSConfigError.__doc__)
        LOG.debug("Description of VmwareConfigError: " + doc)

        LOG.info("Testing import of PdnsApiConfigInfo from fb_pdnstools.config ...")
        from fb_pdnstools.config import PdnsApiConfigInfo
        doc = textwrap.dedent(PdnsApiConfigInfo.__doc__)
        LOG.debug("Description of PdnsApiConfigInfo: " + doc)

        LOG.info("Testing import of PdnsApiConfig from fb_vmware.config ...")
        from fb_pdnstools.config import PdnsApiConfig
        doc = textwrap.dedent(PdnsApiConfig.__doc__).strip()
        LOG.debug("Description of PdnsApiConfig: " + doc)

    # -------------------------------------------------------------------------
    def test_info_object(self):
        """Test init of a PdnsApiConfigInfo object."""
        LOG.info(self.get_method_doc())

        from fb_pdnstools.config import PdnsApiConfigInfo
        from fb_pdnstools import MAX_PORT_NUMBER

        info = PdnsApiConfigInfo()

        LOG.debug("PdnsApiConfigInfo %r: {!r}".format(info))
        LOG.debug("PdnsApiConfigInfo %s:\n" + pp(str(info)))

        if self.verbose:
            print()

        LOG.info("Setting some valid values in PdnsApiConfigInfo object ...")

        testkey = str(uuid.uuid4())
        prefix = PdnsApiConfigInfo.default_prefix

        info.host = "dnsmaster.uhu-banane.de"
        info.port = 8088
        info.timeout = 30
        info.use_https = False
        info.key = testkey

        info.initialized = True

        LOG.debug("PdnsApiConfigInfo %r: {!r}".format(info))
        LOG.debug("PdnsApiConfigInfo %s:\n" + pp(str(info)))

        self.assertEqual(info.host, "dnsmaster.uhu-banane.de")
        self.assertEqual(info.port, 8088)
        self.assertEqual(info.timeout, 30)
        self.assertEqual(info.prefix, prefix)
        self.assertFalse(info.use_https)
        self.assertEqual(info.key, testkey)
        self.assertTrue(info.initialized)

        if self.verbose:
            print()

        LOG.info("Init a PdnsApiConfigInfo object with from_config ...")

        section = {
            "host": "Dnsmaster.Uhu-Banane.de",
            "port": 8088,
            "prefix": "/api/v2",
            "https": "False",
            "Timeout": 30,
            "API-Key": testkey,
        }
        LOG.debug("Using test config:\n" + pp(section))
        info = PdnsApiConfigInfo.from_config("pdns", section)

        LOG.debug("PdnsApiConfigInfo %r: {!r}".format(info))
        LOG.debug("PdnsApiConfigInfo %s:\n" + pp(str(info)))

        self.assertEqual(info.host, "dnsmaster.uhu-banane.de")
        self.assertEqual(info.port, 8088)
        self.assertEqual(info.timeout, 30)
        self.assertEqual(info.prefix, PosixPath("/api/v2"))
        self.assertTrue(info.prefix.is_absolute())
        self.assertFalse(info.use_https)
        self.assertEqual(info.key, testkey)
        self.assertTrue(info.initialized)

        if self.verbose:
            print()

        LOG.info("Testing PdnsApiConfigInfo object with wrong values for attributes ...")

        test_data_list = [
            ["host", ""],
            ["port", ""],
            ["port", "bla"],
            ["port", False],
            ["port", "-10"],
            ["port", MAX_PORT_NUMBER + 10],
            ["use_https", None],
            ["key", ""],
            ["prefix", ""],
            ["prefix", "api"],
            ["timeout", ""],
            ["timeout", "bla"],
            ["timeout", False],
            ["timeout", "-10"],
            ["timeout", 3601],
        ]
        info = PdnsApiConfigInfo()
        for test_data in test_data_list:
            attr = test_data[0]
            val = test_data[1]
            LOG.debug(f"Testing attribute {attr!r} with value {val!r} ...")
            with self.assertRaises((TypeError, ValueError)) as cm:
                setattr(info, attr, val)
                LOG.error("This message should never be visible.")
            e = cm.exception
            LOG.debug("{} raised: {}".format(e.__class__.__name__, e))

        # cfg = VmwareConfiguration(
        #     appname=self.appname,
        #     config_dir="test",
        #     additional_stems="test",
        #     verbose=self.verbose,
        # )
        # LOG.debug("VmwareConfiguration %%r: %r", cfg)
        # LOG.debug("VmwareConfiguration %%s: %s", str(cfg))

    # # -------------------------------------------------------------------------
    # def test_read_config(self):
    #     """Test reading of config."""
    #     LOG.info(self.get_method_doc())

    #     from fb_vmware.config import VmwareConfiguration

    #     cfg = VmwareConfiguration(
    #         appname=self.appname,
    #         config_dir="test",
    #         additional_stems="test",
    #         verbose=self.verbose,
    #     )
    #     cfg.read()
    #     cfg.eval()
    #     LOG.debug("VmwareConfiguration %%s: %s", str(cfg))


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestPdnsConfig("test_import", verbose))
    suite.addTest(TestPdnsConfig("test_info_object", verbose))
    # suite.addTest(TestPdnsConfig("test_read_config", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
