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
import logging
import re
from collections.abc import MutableSequence
from functools import cmp_to_key

# Third party modules
from fb_tools.common import compare_fqdn
from fb_tools.common import pp
from fb_tools.common import to_utf8

# Own modules

from .base import GenericPdnsObject
from .common import seconds2human
from .descriptors import BooleanDescriptor
from .descriptors import IntegerDescriptor
from .descriptors import RrsetTypeDescriptor
from .descriptors import StringDescriptor
from .errors import PowerDNSRecordSetError
from .record import PowerDNSRecord
from .record import PowerDNSRecordList
from .recordsetcomment import PowerDNSRecordSetComment
from .soa import PowerDnsSOAData
from .xlate import XLATOR

__version__ = "1.1.0"

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

    # -------------------------------------------------------------------------
    def sort(self, reverse=False):
        """Sorts the resource records in place."""
        self._list.sort(reverse=reverse, key=cmp_to_key(compare_rrsets))


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
