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
import copy
import datetime
import logging
import re
import time

try:
    from collections.abc import MutableSequence
except ImportError:
    from collections import MutableSequence

# Third party modules
from fb_tools.common import compare_fqdn
from fb_tools.common import pp
from fb_tools.common import to_str
from fb_tools.common import to_utf8

# Own modules

from .base import GenericPdnsObject
from .common import seconds2human
from .descriptors import BooleanDescriptor
from .descriptors import IntegerDescriptor
from .descriptors import RrsetTypeDescriptor
from .descriptors import StringDescriptor
from .errors import PowerDNSRecordSetError
from .errors import PowerDNSWrongRecordTypeError
from .errors import PowerDNSWrongSoaDataError
from .xlate import XLATOR

__version__ = "2.2.0"

LOG = logging.getLogger(__name__)

TYPE_ORDER = {
    "SOA": 0,
    "NS": 1,
    "MX": 2,
    "A": 3,
    "AAAA": 4,
    "CNAME": 5,
    "SRV": 6,
    "TXT": 7,
    "SPF": 8,
    "PTR": 9,
}
DEFAULT_RRSET_TTL = 3600

_ = XLATOR.gettext


# =============================================================================
def compare_rrsets(x, y):
    """Compare two DNS record sets - thich function can be used for sorting record set lists."""
    if not isinstance(x, PowerDNSRecordSet):
        raise TypeError(
            _("Argument {a} {v!r} must be a {o} object.").format(a="x", v=x, o="PowerDNSRecordSet")
        )

    if not isinstance(y, PowerDNSRecordSet):
        raise TypeError(
            _("Argument {a} {v!r} must be a {o} object.").format(a="y", v=y, o="PowerDNSRecordSet")
        )

    ret = compare_fqdn(x.name, y.name)
    if ret:
        return ret

    xt = 99
    yt = 99
    if x.type.upper() in TYPE_ORDER:
        xt = TYPE_ORDER[x.type.upper()]
    if y.type.upper() in TYPE_ORDER:
        yt = TYPE_ORDER[y.type.upper()]

    if xt < yt:
        return -1
    if xt > yt:
        return 1
    return 0


# =============================================================================
class PowerDNSRecord(GenericPdnsObject):
    """Encapsulation class of a DNS record (part of a DNS record set) in PowerDNS."""

    content = StringDescriptor(name="content", stripped=True)
    disabled = BooleanDescriptor(name="disabled")
    initialized = BooleanDescriptor(name="initialized")

    # -------------------------------------------------------------------------
    def __init__(
        self,
        content="",
        disabled=False,
    ):
        """Initialize a PowerDNSRecord record."""
        self.content = content
        self.disabled = disabled
        self.initialized = True

    # -----------------------------------------------------------
    @property
    def enabled(self):
        """Flag, whether the record is enabled or not."""
        if self.disabled:
            return False
        return True

    @enabled.setter
    def enabled(self, value):
        v = bool(value)
        if v:
            self.disabled = False
        else:
            self.disabled = True

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        self.initialized = False
        self.content = ""
        self.disabled = False

        super(PowerDNSRecord, self).import_data(data)

        if "content" in data:
            self.content = data["content"]
        if "disabled" in data:
            self.disabled = data["disabled"]

        self.initialized = True

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        return {
            "content": self.content,
            "disabled": self.disabled,
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

        res = super(PowerDNSRecord, self).as_dict(short=short)
        res.update(self.export_data())
        res["enabled"] = self.enabled
        res["initialized"] = self.initialized

        return res

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDNSRecord as a deep copy of the current object."""
        return PowerDNSRecord(content=self.content, disabled=self.disabled)

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecast into a string.

        @return: structure as string
        @rtype:  str
        """
        return pp(self.as_dict(short=True))

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("content={!r}".format(self.content))
        fields.append("disabled={!r}".format(self.disabled))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        """Magic method for using it as the '=='-operator."""
        if not isinstance(other, PowerDNSRecord):
            return False

        if self.content.lower() == other.content.lower():
            return True

        return False

    # -------------------------------------------------------------------------
    def __lt__(self, other):
        """Magic method for using it as the '<'-operator."""
        if not isinstance(other, PowerDNSRecord):
            msg = _("Wrong type {cls} of other parameter {other!r} for comparision.").format(
                cls=other.__class__.__name__, other=other
            )
            raise PowerDNSWrongRecordTypeError(msg)

        if self == other:
            return False

        return self.content.lower() < other.content.lower()

    # -------------------------------------------------------------------------
    def __gt__(self, other):
        """Magic method for using it as the '>'-operator."""
        if not isinstance(other, PowerDNSRecord):
            msg = _("Wrong type {cls} of other parameter {other!r} for comparision.").format(
                cls=other.__class__.__name__, other=other
            )
            raise PowerDNSWrongRecordTypeError(msg)

        if self == other:
            return False

        return self.content.lower() > other.content.lower()


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
class PowerDNSRecordList(MutableSequence):
    """A list containing Power DNS Records (as parts of a Record Set)."""

    msg_no_pdns_record = _("Invalid type {t!r} as an item of a {c}, only {o} objects are allowed.")

    # -------------------------------------------------------------------------
    def __init__(self, *records):
        """Initialize a PowerDNSRecordList object."""
        self._list = []

        for record in records:
            self.append(record)

    # -------------------------------------------------------------------------
    def index(self, record, *args):
        """Return the numeric index of the given record in current list."""
        i = None
        j = None

        if len(args) > 0:
            if len(args) > 2:
                raise TypeError(
                    _("{m} takes at most {max} arguments ({n} given).").format(
                        m="index()", max=3, n=len(args) + 1
                    )
                )
            i = int(args[0])
            if len(args) > 1:
                j = int(args[1])

        index = 0
        start = 0
        if i is not None:
            start = i
            if i < 0:
                start = len(self._list) + i
        wrap = False
        end = len(self._list)
        if j is not None:
            if j < 0:
                end = len(self._list) + j
                if end < index:
                    wrap = True
            else:
                end = j
        for index in list(range(len(self._list))):
            item = self._list[index]
            if index < start:
                continue
            if index >= end and not wrap:
                break
            if item == record:
                return index

        if wrap:
            for index in list(range(len(self._list))):
                item = self._list[index]
                if index >= end:
                    break
            if item == record:
                return index

        msg = _("Record {!r} is not in Record list.").format(record.content)
        raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __contains__(self, record):
        """Return whether the given record is contained in current list."""
        if not isinstance(record, PowerDNSRecord):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=record.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecord"
                )
            )

        if not self._list:
            return False

        for item in self._list:
            if item == record:
                return True

        return False

    # -------------------------------------------------------------------------
    def count(self, record):
        """Return the number of records which are equal to the given one in current list."""
        if not isinstance(record, PowerDNSRecord):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=record.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecord"
                )
            )

        if not self._list:
            return 0

        num = 0
        for item in self._list:
            if item == record:
                num += 1
        return num

    # -------------------------------------------------------------------------
    def __len__(self):
        """Return the number of records in current list."""
        return len(self._list)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        """Get a record from current list by the given numeric index."""
        return self._list.__getitem__(key)

    # -------------------------------------------------------------------------
    def __reversed__(self):
        """Reverse the records in list in place."""
        return reversed(self._list)

    # -------------------------------------------------------------------------
    def __setitem__(self, key, record):
        """Replace the record at the given numeric index by the given one."""
        if not isinstance(record, PowerDNSRecord):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=record.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecord"
                )
            )

        self._list.__setitem__(key, record)

    # -------------------------------------------------------------------------
    def __delitem__(self, key):
        """Remove the record at the given numeric index from list."""
        del self._list[key]

    # -------------------------------------------------------------------------
    def append(self, record):
        """Append the given record to the current list."""
        if not isinstance(record, PowerDNSRecord):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=record.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecord"
                )
            )

        self._list.append(record)

    # -------------------------------------------------------------------------
    def insert(self, index, record):
        """Insert the given record in current list at given index."""
        if not isinstance(record, PowerDNSRecord):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=record.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecord"
                )
            )

        self._list.insert(index, record)

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDNSRecordList as a deep copy of the current object."""
        new_list = self.__class__()
        for record in self._list:
            new_list.append(copy.copy(record))
        return new_list

    # -------------------------------------------------------------------------
    def clear(self):
        """Remove all items from the PowerDNSRecordList."""
        self._list = []

    # -------------------------------------------------------------------------
    def clean(self):
        """Do exactly the same like clear() (wrapper for it)."""
        return self.clear()

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        # res = []
        # for rrset in self:
        #     res.append(rrset.export_data())
        # return res
        return [r.export_data() for r in self]

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transform the element of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """
        if minimal:
            return self.export_data()

        return [r.as_dict(short=short) for r in self]


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
class PowerDNSRecordSet(GenericPdnsObject):
    """Encapsulates a set of DNS records wth the same name and the same type."""

    default_ttl = DEFAULT_RRSET_TTL

    name = StringDescriptor(
        name="name", lowcase=True, stripped=True, not_empty=True, maybe_none=True
    )
    type = RrsetTypeDescriptor(name="type", maybe_none=True)  # noqa: A003
    ttl = IntegerDescriptor(name="ttl", lower_limit=0)

    initialized = BooleanDescriptor(name="initialized")

    # -------------------------------------------------------------------------
    def __init__(
        self,
        name=None,
        type=None,  # noqa: A002
        ttl=DEFAULT_RRSET_TTL,
    ):
        """Initialize a PowerDNSRecordSet object."""
        # {   'comments': [],
        #     'name': 'www.bmwi.tv.',
        #     'records': [{'content': '77.74.236.5', 'disabled': False}],
        #     'ttl': 3600,
        #     'type': 'A'},
        self.records = PowerDNSRecordList()
        self.comments = []
        self.name = name
        self.ttl = ttl
        self.type = type
        self.initialized = False

    # -----------------------------------------------------------
    @property
    def valid(self):
        """Is this a valid Resource rescord set or not."""
        if self.name is None:
            return False
        if not len(self.records):
            return False
        if self.type is None:
            return False
        if self.ttl is None:
            return False

        return True

    # -----------------------------------------------------------
    @property
    def name_unicode(self):
        """Give the name of the resource record set in unicode, if it is an IDNA encoded zone."""
        name = self.name
        if name is None:
            return None
        if "xn--" in name:
            return to_utf8(name).decode("idna")
        return name

    # -----------------------------------------------------------
    @property
    def ttl_human(self):
        """Return the ttl of the record set in a human readable format."""
        if self._ttl is None:
            return None
        return seconds2human(self._ttl)

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        self.initialized = False

        self.name = None
        self.type = None
        self.ttl = DEFAULT_RRSET_TTL

        self.records = PowerDNSRecordList()
        self.comments = []

        super(PowerDNSRecordSet, self).import_data(data)

        self.name = data["name"]
        self.type = data["type"]
        if "ttl" in data:
            self.ttl = data["ttl"]

        if "comments" in data and data["comments"]:
            for comment_dict in data["comments"]:
                acc = None
                cont = ""
                modified_at = None
                if "account" in comment_dict:
                    acc = comment_dict["account"]
                if "content" in comment_dict:
                    cont = comment_dict["content"]
                if "modified_at" in comment_dict:
                    modified_at = comment_dict["modified_at"]
                comment = PowerDNSRecordSetComment(
                    account=acc,
                    content=cont,
                    modified_at=modified_at,
                )
                self.comments.append(comment)

        if "records" in data:
            for single_record in data["records"]:
                record = PowerDNSRecord(
                    content=single_record["content"],
                    disabled=single_record["disabled"],
                )
                record.initialized = True
                self.records.append(record)

        if self.valid:
            self.initialized = True

    # -------------------------------------------------------------------------
    @classmethod
    def init_from_dict(cls, data):
        """Create a new PowerDNSRecordSet object based on a given dict."""
        rrset = cls()
        rrset.import_data(data)
        return rrset

    # -------------------------------------------------------------------------
    def name_relative(self, reference):
        """Extract the name from the current set name relative to the given reference."""
        # current name must be an absolute name
        if not self.name.endswith("."):
            return self.name

        # reference name must be an absolute name
        if not reference.endswith("."):
            return self.name

        ref_escaped = r"\." + re.escape(reference) + r"$"
        rel_name = re.sub(ref_escaped, "", self.name)
        return rel_name

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        return {
            "comments": [c.export_data() for c in self.comments],
            "name": self.name,
            "records": self.records.export_data(),
            "type": self.type,
            "ttl": self.ttl,
        }

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transform the element of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """
        if minimal:
            return self.export_data()

        res = super(PowerDNSRecordSet, self).as_dict(short=short)

        res["name"] = self.name
        res["type"] = self.type
        res["ttl"] = self.ttl
        res["ttl_human"] = self.ttl_human
        res["name_unicode"] = self.name_unicode
        res["initialized"] = self.initialized
        res["valid"] = self.valid
        res["comments"] = [c.as_dict(short=short) for c in self.comments]
        res["records"] = self.records.as_dict(short=short)

        return res

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecast for translating object structure into a string.

        @return: structure as string
        @rtype:  str
        """
        return pp(self.as_dict(short=True))

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("name={!r}".format(self.name))
        fields.append("type={!r}".format(self.type))
        fields.append("ttl={!r}".format(self.ttl))
        fields.append("comments=[" + ", ".join([repr(c) for c in self.comments]) + "]")
        fields.append("records=[" + ", ".join([repr(r) for r in self.records]) + "]")

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDNSRecordSet as a deep copy of the current object."""
        rrset = PowerDNSRecordSet(
            name=self.name,
            type=self.type,
            ttl=self.ttl,
        )

        rrset.comments = copy.copy(self.comments)
        rrset.records = copy.copy(self.records)

        if rrset.valid:
            rrset.initialized = True
        else:
            rrset.initialized = False

        return rrset

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        """Magic method for using it as the '=='-operator."""
        if not isinstance(other, PowerDNSRecordSet):
            return False

        if self.name != other.name:
            return False

        if self.type != other.type:
            return False

        return True

    # -------------------------------------------------------------------------
    def get_soa_data(self):
        """Extract a PowerDnsSOAData object from record content, if current type is SOA."""
        if self.type != "SOA":
            msg = (
                _("Cannot create {o} from record set:").format(o="PowerDnsSOAData")
                + "\n"
                + pp(self.as_dict())
            )
            raise PowerDNSRecordSetError(msg)

        if not self.records:
            msg = _("RecordSet has no records:") + "\n" + pp(self.as_dict())
            raise PowerDNSRecordSetError(msg)

        record = self.records[0]
        soa = PowerDnsSOAData.init_from_data(record.content)
        return soa


# =============================================================================
class PowerDNSRecordSetList(MutableSequence):
    """A list containing Power DNS Record Sets (of a zone)."""

    msg_no_pdns_rrset = _("Invalid type {t!r} as an item of a {c}, only {o} objects are allowed.")

    # -------------------------------------------------------------------------
    def __init__(self, *rrsets):
        """Initialize a PowerDNSRecordSetList object."""
        self._list = []

        for rrset in rrsets:
            self.append(rrset)

    # -------------------------------------------------------------------------
    def index(self, rrset, *args):
        """Return the numeric index of the given record set in current list."""
        i = None
        j = None

        if len(args) > 0:
            if len(args) > 2:
                raise TypeError(
                    _("{m} takes at most {max} arguments ({n} given).").format(
                        m="index()", max=3, n=len(args) + 1
                    )
                )
            i = int(args[0])
            if len(args) > 1:
                j = int(args[1])

        index = 0
        start = 0
        if i is not None:
            start = i
            if i < 0:
                start = len(self._list) + i
        wrap = False
        end = len(self._list)
        if j is not None:
            if j < 0:
                end = len(self._list) + j
                if end < index:
                    wrap = True
            else:
                end = j
        for index in list(range(len(self._list))):
            item = self._list[index]
            if index < start:
                continue
            if index >= end and not wrap:
                break
            if item == rrset:
                return index

        if wrap:
            for index in list(range(len(self._list))):
                item = self._list[index]
                if index >= end:
                    break
            if item == rrset:
                return index

        msg = _("RecordSet {n!r} ({n}) is not in RecordSet list.").format(
            n=rrset.name, t=rrset.type
        )
        raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __contains__(self, rrset):
        """Return whether the given record set is contained in current list."""
        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=rrset.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecordSet"
                )
            )

        if not self._list:
            return False

        for item in self._list:
            if item == rrset:
                return True

        return False

    # -------------------------------------------------------------------------
    def count(self, rrset):
        """Return the number of record sets which are equal to the given one in current list."""
        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=rrset.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecordSet"
                )
            )

        if not self._list:
            return 0

        num = 0
        for item in self._list:
            if item == rrset:
                num += 1
        return num

    # -------------------------------------------------------------------------
    def __len__(self):
        """Return the number of record sets in current list."""
        return len(self._list)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        """Get a record set from current list by the given numeric index."""
        return self._list.__getitem__(key)

    # -------------------------------------------------------------------------
    def __reversed__(self):
        """Reverse the record sets in list in place."""
        return reversed(self._list)

    # -------------------------------------------------------------------------
    def __setitem__(self, key, rrset):
        """Replace the record set at the given numeric index by the given one."""
        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=rrset.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecordSet"
                )
            )

        self._list.__setitem__(key, rrset)

    # -------------------------------------------------------------------------
    def __delitem__(self, key):
        """Remove the record set at the given numeric index from list."""
        del self._list[key]

    # -------------------------------------------------------------------------
    def append(self, rrset):
        """Append the given record set to the current list."""
        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=rrset.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecordSet"
                )
            )

        self._list.append(rrset)

    # -------------------------------------------------------------------------
    def insert(self, index, rrset):
        """Insert the given record set in current list at given index."""
        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(
                self.msg_no_pdns_record.format(
                    t=rrset.__class__.__name__, c=self.__class__.__name__, o="PowerDNSRecordSet"
                )
            )

        self._list.insert(index, rrset)

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDNSRecordSetList as a deep copy of the current object."""
        new_list = self.__class__()
        for rrset in self._list:
            new_list.append(copy.copy(rrset))
        return new_list

    # -------------------------------------------------------------------------
    def clear(self):
        """Remove all items from the PowerDNSRecordSetList."""
        self._list = []

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        return [r.export_data() for r in self]

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transform the element of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """
        if minimal:
            return self.export_data()

        return [r.as_dict(short=short) for r in self]


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
