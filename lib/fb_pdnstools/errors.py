#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@summary: The module for special error classes on PowerDNS API operations.
"""
from __future__ import absolute_import

# Standard modules

# Own modules
from fb_tools.errors import FbHandlerError

from .xlate import XLATOR

_ = XLATOR.gettext

__version__ = '0.2.1'


# =============================================================================
class PowerDNSHandlerError(FbHandlerError):
    """Base class for all exception belonging to PowerDNS."""
    pass


# =============================================================================
class PowerDNSZoneError(PowerDNSHandlerError):
    pass


# =============================================================================
class PowerDNSRecordError(PowerDNSHandlerError):
    pass


# =============================================================================
class PowerDNSRecordSetError(PowerDNSHandlerError):
    pass


# =============================================================================
class PowerDNSWrongSoaDataError(PowerDNSRecordSetError):

    # -------------------------------------------------------------------------
    def __init__(self, data):
        self.data = str(data)

    # -------------------------------------------------------------------------
    def __str__(self):

        msg = _("Could not interprete SOA data: {!r}.").format(self.data)
        return msg


# =============================================================================
class PDNSApiError(PowerDNSHandlerError):
    """Base class for more complex exceptions"""
    def __init__(self, resp, content, uri=None):
        self.resp = resp
        self.content = content
        self.uri = uri


# =============================================================================
class PDNSApiNotAuthorizedError(PDNSApiError):
    """The authorization information provided is not correct"""
    pass


# =============================================================================
class PDNSApiNotFoundError(PDNSApiError):
    """The ProfitBricks entity was not found"""
    pass


# =============================================================================
class PDNSApiValidationError(PDNSApiError):
    """The HTTP data provided is not valid"""
    pass


# =============================================================================
class PDNSApiRateLimitExceededError(PDNSApiError):
    """The number of requests sent have exceeded the allowed API rate limit"""
    pass


# =============================================================================
class PDNSApiRequestError(PDNSApiError):
    """Base error for request failures"""
    pass


# =============================================================================
class PDNSApiTimeoutError(PDNSApiRequestError):
    """Raised when a request does not finish in the given time span."""
    pass


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
