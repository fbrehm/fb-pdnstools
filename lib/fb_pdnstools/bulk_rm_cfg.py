#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 by Frank Brehm, Berlin
@summary: A module for providing a configuration for the pdns-bulk-remove application
"""
from __future__ import absolute_import

# Standard module
import logging
import re

# Third party modules

# Own modules
from fb_tools.common import to_bool

from fb_tools.config import ConfigError, BaseConfiguration

from . import DEFAULT_PORT, DEFAULT_API_PREFIX

__version__ = '0.2.0'
LOG = logging.getLogger(__name__)


# =============================================================================
class PdnsBulkRmConfigError(ConfigError):
    """Base error class for all exceptions happened during
    execution this configured application"""

    pass


# =============================================================================
class PdnsBulkRmCfg(BaseConfiguration):
    """
    A class for providing a configuration for the GetVmApplication class
    and methods to read it from configuration files.
    """

    default_pdns_master = 'master.pp-dns.com'
    default_pdns_api_port = DEFAULT_PORT
    default_pdns_api_https = False
    default_pdns_api_prefix = DEFAULT_API_PREFIX

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None,
            encoding=None, config_dir=None, config_file=None, initialized=False):

        self.pdns_master = self.default_pdns_master
        self.pdns_api_port = self.default_pdns_api_port
        self.pdns_api_key = None
        self.pdns_api_https = self.default_pdns_api_https
        self.pdns_api_prefix = self.default_pdns_api_prefix

        super(PdnsBulkRmCfg, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir,
            encoding=encoding, config_dir=config_dir, config_file=config_file, initialized=False,
        )

        if initialized:
            self.initialized = True

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(PdnsBulkRmCfg, self).as_dict(short=short)

        res['pdns_api_key'] = None
        if self.pdns_api_key:
            if self.verbose > 4:
                res['pdns_api_key'] = self.pdns_api_key
            else:
                res['pdns_api_key'] = '*******'

        return res

    # -------------------------------------------------------------------------
    def eval_config_section(self, config, section_name):

        super(PdnsBulkRmCfg, self).eval_config_section(config, section_name)

        if section_name.lower() in ('pdns', 'powerdns'):
            self._eval_config_pdns(config, section_name)
            return

        if self.verbose > 1:
            LOG.debug("Unhandled configuration section {!r}.".format(section_name))

    # -------------------------------------------------------------------------
    def _eval_config_pdns(self, config, section_name):

        if self.verbose > 1:
            LOG.debug("Checking config section {!r} ...".format(section_name))

        re_api_key = re.compile(r'^\s*(?:api[_-]?)?key\s*', re.IGNORECASE)
        re_api_prefix = re.compile(r'^\s*(?:api[_-]?)?prefix\s*', re.IGNORECASE)

        for (key, value) in config.items(section_name):

            if key.lower() == 'master':
                self.pdns_master = value
                continue
            elif key.lower() == 'port':
                self.pdns_api_port = int(value)
                continue
            elif re_api_key.match(key) and str(value).strip():
                self.pdns_api_key = str(value).strip()
                continue
            elif key.lower() == 'https':
                self.pdns_api_https = to_bool(value)
                continue
            elif re_api_prefix.match(key):
                self.pdns_api_prefix = str(value).strip()

        return


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
