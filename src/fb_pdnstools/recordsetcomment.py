#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: An encapsulation class for a DNS record object by PowerDNS API.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
"""

from __future__ import absolute_import

# Standard modules
import datetime
import logging
import time

# Third party modules
from fb_tools.common import pp

# Own modules

from .base import GenericPdnsObject
from .descriptors import BooleanDescriptor
from .descriptors import IntegerDescriptor
from .descriptors import StringDescriptor
from .record import PowerDNSRecord
from .xlate import XLATOR

__version__ = "1.0.0"

LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
class PowerDNSRecordSetComment(GenericPdnsObject):
    """This class encapsulates a comment to a DNS Record set."""

    account = StringDescriptor(name="account", stripped=True, maybe_none=True)
    content = StringDescriptor(name="content", stripped=True)
    modified_at = IntegerDescriptor(name="modified_at", lower_limit=0)

    initialized = BooleanDescriptor(name="initialized")

    # -------------------------------------------------------------------------
    def __init__(
        self,
        account=None,
        content="",
        modified_at=None,
    ):
        """Initialize a PowerDNSRecordSetComment object."""
        self.account = account
        self.content = content
        if modified_at is None:
            modified_at = int(time.time() + 0.5)
        self.modified_at = modified_at
        self.initialized = False

        if self.valid:
            self.initialized = True

    # -------------------------------------------------------------------------
    @property
    def modified_date(self):
        """Give the modification of this comment as a datetime object."""
        return datetime.datetime.utcfromtimestamp(self.modified_at)

    # -------------------------------------------------------------------------
    @property
    def valid(self):
        """Is this a valid comment or not."""
        if self.account is None or self.modified_at is None:
            return False
        return True

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        self.initialized = False
        self.account = None
        self.content = ""
        self.modified_at = None

        super(PowerDNSRecord, self).import_data(data)

        if "account" in data:
            self.account = data["account"]
        if "content" in data:
            self.content = data["content"]
        if "modified_at" in data:
            self.modified_at = data["modified_at"]

        if self.valid:
            self.initialized = True

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        return {
            "account": self.account,
            "content": self.content,
            "modified_at": self.modified_at,
        }

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """
        if minimal:
            return self.export_data()

        res = super(PowerDNSRecordSetComment, self).as_dict(short=short)
        res.update(self.export_data())
        res["initialized"] = self.valid
        res["modified_date"] = self.modified_date
        res["valid"] = self.valid

        return res

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDNSRecordSetComment as a deep copy of the current object."""
        return PowerDNSRecordSetComment(
            account=self.account,
            content=self.content,
            modified_at=self.modified_at,
        )

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecast for translating object structure into a string.

        @return: structure as string
        @rtype:  str
        """
        return pp(self.export_data())

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("account={!r}".format(self.account))
        fields.append("content={!r}".format(self.content))
        fields.append("modified_at={!r}".format(self.modified_at))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        """Magic method for using it as the '=='-operator."""
        if self.verbose > 4:
            LOG.debug(_("Comparing {} objects ...").format(self.__class__.__name__))

        if not isinstance(other, PowerDNSRecordSetComment):
            return False

        if self.account != other.account:
            return False

        if self.content != other.content:
            return False

        if self.modified_at != other.modified_at:
            return False

        return True


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
