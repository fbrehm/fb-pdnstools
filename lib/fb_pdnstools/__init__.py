#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@summary: The module for a base PowerDNS handler object.
"""
from __future__ import absolute_import

# Standard modules
import os
import logging
import re
import json
import copy
import socket
import ipaddress

from abc import ABCMeta

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

# Third party modules
import requests
import urllib3

import six
from six import add_metaclass

# Own modules
from fb_tools.common import pp, to_bool, RE_DOT_AT_END, reverse_pointer, to_str

from fb_tools.handling_obj import HandlingObject

from .xlate import XLATOR

from .errors import PowerDNSHandlerError, PDNSApiError, PDNSApiNotAuthorizedError
from .errors import PDNSApiNotFoundError, PDNSApiValidationError, PDNSApiRateLimitExceededError

__version__ = '0.2.0'
LOG = logging.getLogger(__name__)
LIBRARY_NAME = "fb-pdns-api-client"

LOGLEVEL_REQUESTS_SET = False

DEFAULT_PORT = 8081
DEFAULT_TIMEOUT = 20
DEFAULT_API_PREFIX = '/api/v1'
DEFAULT_USE_HTTPS = False

FQDN_REGEX = re.compile(r'^((?!-)[-A-Z\d]{1,62}(?<!-)\.)+[A-Z]{1,62}\.?$', re.IGNORECASE)

VALID_RRSET_TYPES = [
    'SOA', 'A', 'AAAA', 'AFSDB', 'APL', 'CAA', 'CDNSKEY', 'CDS', 'CERT', 'CNAME', 'DHCID',
    'DLV', 'DNAME', 'DNSKEY', 'DS', 'HIP', 'HINFO', 'IPSECKEY', 'ISDN', 'KEY', 'KX', 'LOC',
    'MB', 'MINFO', 'MX', 'NAPTR', 'NS', 'NSAP', 'NSEC', 'NSEC3', 'NSEC3PARAM', 'OPT', 'PTR',
    'RP', 'RRSIG', 'SIG', 'SPF', 'SRV', 'SSHFP', 'TA', 'TKEY', 'TLSA', 'TSIG', 'TXT', 'URI',
    'WKS', 'X25'
]

_ = XLATOR.gettext



# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
