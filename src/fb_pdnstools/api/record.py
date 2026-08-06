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
from collections.abc import MutableSequence

# Third party modules
from fb_tools.common import pp

# Own modules

from ..base import GenericPdnsObject
from ..descriptors import BooleanDescriptor
from ..descriptors import StringDescriptor
from ..errors import PowerDNSWrongRecordTypeError
from ..xlate import XLATOR

__version__ = "3.1.0"

LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


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
    def get_repr_fields(self):
        """Return a list of parameters prepared for __repr__()."""
        fields = []

        fields.append("content={!r}".format(self.content))
        fields.append("disabled={!r}".format(self.disabled))

        fields += super(PowerDNSRecord, self).get_repr_fields()

        return fields

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

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
