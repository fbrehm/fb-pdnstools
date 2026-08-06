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
import re

# Third party modules
from fb_tools.common import to_str

# Own modules

from ..base import GenericPdnsObject
from ..common import seconds2human
from ..descriptors import BooleanDescriptor
from ..descriptors import IntegerDescriptor
from ..descriptors import StringDescriptor
from ..errors import PowerDNSWrongSoaDataError
from ..xlate import XLATOR

__version__ = "1.1.0"

LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
class PowerDnsSOAData(GenericPdnsObject):
    """Encapsulation class of a SOA (Start of authority) DNS record."""

    re_soa_data = re.compile(r"^\s*(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$")
    re_ws = re.compile(r"\s+")

    primary = StringDescriptor(name="primary", lowcase=True, stripped=True, maybe_none=True)
    email = StringDescriptor(name="email", lowcase=True, stripped=True, maybe_none=True)
    serial = IntegerDescriptor(name="serial", lower_limit=0, maybe_none=True)
    refresh = IntegerDescriptor(name="refresh", lower_limit=0, maybe_none=True)
    retry = IntegerDescriptor(name="retry", lower_limit=0, maybe_none=True)
    expire = IntegerDescriptor(name="expire", lower_limit=0, maybe_none=True)
    ttl = IntegerDescriptor(name="ttl", lower_limit=0, maybe_none=True)

    initialized = BooleanDescriptor(name="initialized")

    # -------------------------------------------------------------------------
    def __init__(
        self,
        primary=None,
        email=None,
        serial=None,
        refresh=None,
        retry=None,
        expire=None,
        ttl=None,
    ):
        """Initialize a PowerDnsSOAData record."""
        self.primary = primary
        self.email = email
        self.serial = serial
        self.refresh = refresh
        self.retry = retry
        self.expire = expire
        self.ttl = ttl
        self.initialized = False

        if self.valid:
            self.initialized = True

    # -----------------------------------------------------------
    @property
    def refresh_human(self):
        """Return the refresh time in a human readable format."""
        if self._refresh is None:
            return None
        return seconds2human(self._refresh)

    # -----------------------------------------------------------
    @property
    def retry_human(self):
        """Return the retry time in a human readable format."""
        if self._retry is None:
            return None
        return seconds2human(self._retry)

    # -----------------------------------------------------------
    @property
    def expire_human(self):
        """Return the expire time in a human readable format."""
        if self._expire is None:
            return None
        return seconds2human(self._expire)

    # -----------------------------------------------------------
    @property
    def ttl_human(self):
        """Return the ttl of the zone in a human readable format."""
        if self._ttl is None:
            return None
        return seconds2human(self._ttl)

    # -----------------------------------------------------------
    @property
    def data(self):
        """Return a string representation of SOA data."""
        if self.primary is None:
            return None
        if self.email is None:
            return None
        if self.serial is None:
            return None
        if self.refresh is None:
            return None
        if self.retry is None:
            return None
        if self.expire is None:
            return None
        if self.ttl is None:
            return None
        return "{_primary} {_email} {_serial} {_refresh} {_retry} {_expire} {_ttl}".format(
            **self.__dict__
        )

    # -----------------------------------------------------------
    @property
    def data_human(self):
        """Return a string representation of SOA data in a human readable format."""
        if self.primary is None:
            return None
        if self.email is None:
            return None
        if self.serial is None:
            return None
        if self.refresh is None:
            return None
        if self.retry is None:
            return None
        if self.expire is None:
            return None
        if self.ttl is None:
            return None
        return "{primary} {email} {serial} {refresh!r} {retry!r} {expire!r} {ttl!r}".format(
            primary=self.primary,
            email=self.email,
            serial=self.serial,
            refresh=self.refresh_human,
            retry=self.retry_human,
            expire=self.expire_human,
            ttl=self.ttl_human,
        )

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        self.initialized = False
        self.primary = None
        self.email = None
        self.serial = None
        self.refresh = None
        self.retry = None
        self.expire = None
        self.ttl = None

        line = self.re_ws.sub(" ", to_str(data))
        match = self.re_soa_data.match(line)
        if not match:
            raise PowerDNSWrongSoaDataError(data)

        self.primary = match.group(1)
        self.email = match.group(2)
        self.serial = match.group(3)
        self.refresh = match.group(4)
        self.retry = match.group(5)
        self.expire = match.group(6)
        self.ttl = match.group(7)

        if self.valid:
            self.initialized = True

    # -------------------------------------------------------------------------
    @property
    def valid(self):
        """Is this a valid SOA or not."""
        if self.primary is None:
            return False
        if self.serial is None:
            return False
        if self.refresh is None:
            return False
        if self.retry is None:
            return False
        if self.expire is None:
            return False
        if self.ttl is None:
            return False

        return True

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        return {
            "primary": self.primary,
            "email": self.email,
            "serial": self.serial,
            "refresh": self.refresh,
            "retry": self.retry,
            "expire": self.expire,
            "ttl": self.ttl,
        }

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(PowerDnsSOAData, self).as_dict(short=short)

        res.update(self.export_data())

        res["data"] = self.data
        res["data_human"] = self.data_human
        res["expire_human"] = self.expire_human
        res["refresh_human"] = self.refresh_human
        res["retry_human"] = self.retry_human
        res["ttl_human"] = self.ttl_human
        res["valid"] = self.valid

        return res

    # -------------------------------------------------------------------------
    @classmethod
    def init_from_data(cls, data):
        """Create a PowerDnsSOAData on base of the SOA data given from DNS."""
        soa = cls()
        soa.import_data(data)
        return soa

    # -------------------------------------------------------------------------
    def get_repr_fields(self):
        """Return a list of parameters prepared for __repr__()."""
        fields = []

        fields.append("primary={!r}".format(self.primary))
        fields.append("email={!r}".format(self.email))
        fields.append("serial={!r}".format(self.serial))
        fields.append("refresh={!r}".format(self.refresh))
        fields.append("retry={!r}".format(self.retry))
        fields.append("expire={!r}".format(self.expire))
        fields.append("ttl={!r}".format(self.ttl))

        fields += super(PowerDnsSOAData, self).get_repr_fields()

        return fields

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDnsSOAData as a deep copy of the current object."""
        soa = PowerDnsSOAData(
            primary=self.primary,
            email=self.email,
            serial=self.serial,
            refresh=self.refresh,
            retry=self.retry,
            expire=self.expire,
            ttl=self.ttl,
        )
        return soa

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        """Magic method for using it as the '=='-operator."""
        if not isinstance(other, PowerDnsSOAData):
            return False

        if self.primary != other.primary:
            return False
        if self.email != other.email:
            return False
        if self.serial != other.serial:
            return False
        if self.refresh != other.refresh:
            return False
        if self.retry != other.retry:
            return False
        if self.expire != other.expire:
            return False
        if self.ttl != other.ttl:
            return False

        return True

    # -------------------------------------------------------------------------
    def increase_serial(self):
        """Increase the serial number in current SOA to the current date + sequential number."""
        i = 0
        tpl = "{year:4d}{month:02d}{day:02d}{nr:02d}"
        curdate = datetime.date.today()
        new_serial = 0

        params = {
            "year": curdate.year,
            "month": curdate.month,
            "day": curdate.day,
            "nr": i,
        }

        while new_serial <= self.serial:
            new_serial = int(tpl.format(**params))
            if new_serial > self.serial:
                break
            i += 1
            if i > 99:
                msg = _(
                    "Serial overflow - old serial {o} is in future, new serial {n} "
                    "has reached its maximum value."
                ).format(o=self.serial, n=new_serial)
                raise ValueError(msg)
            params["nr"] = i

        self.serial = new_serial
        return new_serial


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
