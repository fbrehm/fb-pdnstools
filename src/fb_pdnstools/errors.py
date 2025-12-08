#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
summary: The module for special error classes on PowerDNS API operations.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2024 Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules

# Own modules
from fb_tools.errors import FbHandlerError

from .xlate import XLATOR

_ = XLATOR.gettext

__version__ = "1.0.0"


# =============================================================================
class PowerDNSHandlerError(FbHandlerError):
    """Base class for all exception belonging to PowerDNS."""

    pass


# =============================================================================
class PowerDNSZoneError(PowerDNSHandlerError):
    """Exception class for errors in DNS zones handling."""

    pass


# =============================================================================
class PDNSNoRecordsToRemove(PowerDNSZoneError):
    """Special exception for the case, that there are no more Records left to remove."""

    # -------------------------------------------------------------------------
    def __init__(self, zone_name):
        """Initialize the PDNSNoRecordsToRemove object."""
        self.zone_name = zone_name

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string."""
        msg = _("No Resource Record Sets found to remove from zone {!r}.").format(self.zone_name)
        return msg


# =============================================================================
class PowerDNSRecordError(PowerDNSHandlerError):
    """Exception class for errors in DNS records handling."""

    pass


# =============================================================================
class PowerDNSWrongRecordTypeError(PowerDNSRecordError, TypeError):
    """Special exception in case of a wrong DNS record type."""

    pass


# =============================================================================
class PowerDNSRecordSetError(PowerDNSHandlerError):
    """Exception class for errors in DNS record sets handling."""

    pass


# =============================================================================
class PowerDNSWrongSoaDataError(PowerDNSRecordSetError):
    """Special exception in case of wrong DNS SOA record data."""

    # -------------------------------------------------------------------------
    def __init__(self, data):
        """Initialize the PowerDNSWrongSoaDataError object."""
        self.data = str(data)

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string."""
        msg = _("Could not interprete SOA data: {!r}.").format(self.data)
        return msg


# =============================================================================
class PDNSApiError(PowerDNSHandlerError):
    """Base class for more complex exceptions."""

    # -------------------------------------------------------------------------
    def __init__(self, code, msg, uri=None):
        """Initialize the PDNSApiError object."""
        self.code = code
        self.msg = msg
        self.uri = uri

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string."""
        if self.uri:
            msg = _("Got a {code} error code from {uri!r}: {msg}").format(
                code=self.code, uri=self.uri, msg=self.msg
            )
        else:
            msg = _("Got a {code} error code: {msg}").format(code=self.code, msg=self.msg)

        return msg


# =============================================================================
class PDNSApiNotAuthorizedError(PDNSApiError):
    """The authorization information provided is not correct."""

    pass


# =============================================================================
class PDNSApiNotFoundError(PDNSApiError):
    """The ProfitBricks entity was not found."""

    pass


# =============================================================================
class PDNSApiValidationError(PDNSApiError):
    """The HTTP data provided is not valid."""

    pass


# =============================================================================
class PDNSApiRateLimitExceededError(PDNSApiError):
    """The number of requests sent have exceeded the allowed API rate limit."""

    pass


# =============================================================================
class PDNSApiRequestError(PDNSApiError):
    """Base error for request failures."""

    pass


# =============================================================================
class PDNSApiTimeoutError(PDNSApiRequestError):
    """Raised when a request does not finish in the given time span."""

    pass


# =============================================================================
class PDNSRequestError(PowerDNSHandlerError):
    """Raised, when some other exceptions occured on a HTTP(S) request."""

    # -------------------------------------------------------------------------
    def __init__(self, msg, uri=None, request=None, response=None):
        """Initialize the PDNSRequestError object."""
        self.msg = msg
        self.uri = uri
        self.request = request
        self.response = response

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string."""
        msg = _("Got an error requesting {uri!r}: {msg}").format(uri=self.uri, msg=self.msg)
        if self.request:
            cls = ""
            if not isinstance(self.request, str):
                cls = self.request.__class__.__name__ + " - "
            msg += " / Request: {c}{e}".format(c=cls, e=self.request)
        if self.response:
            cls = ""
            if not isinstance(self.response, str):
                cls = self.response.__class__.__name__ + " - "
            msg += " / Response: {c}{e}".format(c=cls, e=self.response)

        return msg


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
