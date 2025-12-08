#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for a base PowerDNS handler object.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2024 Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import re

__version__ = "1.1.0"

# This library name will be used as a part of the user agent in HTTP(S) requests
LIBRARY_NAME = "fb-pdns-api-client"

VALID_RRSET_TYPES = [
    "SOA",
    "A",
    "AAAA",
    "AFSDB",
    "APL",
    "CAA",
    "CDNSKEY",
    "CDS",
    "CERT",
    "CNAME",
    "DHCID",
    "DLV",
    "DNAME",
    "DNSKEY",
    "DS",
    "HIP",
    "HINFO",
    "IPSECKEY",
    "ISDN",
    "KEY",
    "KX",
    "LOC",
    "MB",
    "MINFO",
    "MX",
    "NAPTR",
    "NS",
    "NSAP",
    "NSEC",
    "NSEC3",
    "NSEC3PARAM",
    "OPT",
    "PTR",
    "RP",
    "RRSIG",
    "SIG",
    "SPF",
    "SRV",
    "SSHFP",
    "TA",
    "TKEY",
    "TLSA",
    "TSIG",
    "TXT",
    "URI",
    "WKS",
    "X25",
]

DEFAULT_PORT = 8081
DEFAULT_TIMEOUT = 20
DEFAULT_API_PREFIX = "/api/v1"
DEFAULT_USE_HTTPS = False

MAX_PORT_NUMBER = (2**16) - 1

FQDN_REGEX = re.compile(r"^((?!-)[-A-Z\d]{1,62}(?<!-)\.)+[A-Z]{1,62}\.?$", re.IGNORECASE)


# Own modules
from .errors import PDNSApiError  # noqa: F401
from .errors import PDNSApiNotAuthorizedError  # noqa: F401
from .errors import PDNSApiNotFoundError  # noqa: F401
from .errors import PDNSApiRateLimitExceededError  # noqa: F401
from .errors import PDNSApiRequestError  # noqa: F401
from .errors import PDNSApiTimeoutError  # noqa: F401
from .errors import PDNSApiValidationError  # noqa: F401
from .errors import PDNSNoRecordsToRemove  # noqa: F401
from .errors import PowerDNSHandlerError  # noqa: F401
from .errors import PowerDNSRecordError  # noqa: F401
from .errors import PowerDNSRecordSetError  # noqa: F401
from .errors import PowerDNSWrongRecordTypeError  # noqa: F401
from .errors import PowerDNSWrongSoaDataError  # noqa: F401
from .errors import PowerDNSZoneError  # noqa: F401
from .record import PowerDNSRecord  # noqa: F401
from .record import PowerDNSRecordList  # noqa: F401
from .record import PowerDNSRecordSet  # noqa: F401
from .record import PowerDNSRecordSetComment  # noqa: F401
from .record import PowerDNSRecordSetList  # noqa: F401
from .record import PowerDnsSOAData  # noqa: F401
from .server import PowerDNSServer  # noqa: F401
from .zone import PowerDNSZone  # noqa: F401
from .zone import PowerDNSZoneDict  # noqa: F401


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
