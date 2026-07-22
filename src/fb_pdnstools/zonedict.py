#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: An encapsulation class for zone objects by PowerDNS API.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import logging
from collections.abc import MutableMapping
from functools import cmp_to_key

# Third party modules
from fb_tools.common import compare_fqdn

# Own modules
from .zone import PowerDNSZone
from .xlate import XLATOR

__version__ = "1.0.0"

LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PowerDNSZoneDict(MutableMapping):
    """
    A dictionary containing PDNS Zone objects.

    It works like a dict.
    i.e.:
    zones = PowerDNSZoneDict(PowerDNSZone(name='pp.com', ...))
    and
    zones['pp.com'] returns a PowerDNSZone object for zone 'pp.com'
    """

    msg_invalid_zone_type = _("Invalid item type {{!r}} to set, only {} allowed.").format(
        "PowerDNSZone"
    )
    msg_key_not_name = _("The key {k!r} must be equal to the zone name {n!r}.")
    msg_none_type_error = _("None type as key is not allowed.")
    msg_empty_key_error = _("Empty key {!r} is not allowed.")
    msg_no_zone_dict = _("Object {o!r} is not a {e} object.")

    # -------------------------------------------------------------------------
    # __init__() method required to create instance from class.
    def __init__(self, *args, **kwargs):
        """Initialize a PowerDNSZoneDict object."""
        self._map = {}

        for arg in args:
            self.append(arg)

    # -------------------------------------------------------------------------
    def _set_item(self, key, zone):

        if not isinstance(zone, PowerDNSZone):
            raise TypeError(self.msg_invalid_zone_type.format(zone.__class__.__name__))

        zone_name = zone.name
        if zone_name != key.lower():
            raise KeyError(self.msg_key_not_name.format(k=key, n=zone_name))

        self._map[zone_name] = zone

    # -------------------------------------------------------------------------
    def append(self, zone):
        """Append the given zone to the current dict."""
        if not isinstance(zone, PowerDNSZone):
            raise TypeError(self.msg_invalid_zone_type.format(zone.__class__.__name__))
        self._set_item(zone.name, zone)

    # -------------------------------------------------------------------------
    def _get_item(self, key):

        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == "":
            raise ValueError(self.msg_empty_key_error.format(key))

        return self._map[zone_name]

    # -------------------------------------------------------------------------
    def get(self, key):
        """Get a zone from current dict by its zone name as key."""
        return self._get_item(key)

    # -------------------------------------------------------------------------
    def _del_item(self, key, strict=True):

        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == "":
            raise ValueError(self.msg_empty_key_error.format(key))

        if not strict and zone_name not in self._map:
            return

        del self._map[zone_name]

    # -------------------------------------------------------------------------
    # The next five methods are requirements of the ABC.
    def __setitem__(self, key, value):
        """Set a zone in current dict by its zone name as key."""
        self._set_item(key, value)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        """Get a zone from current dict by its zone name as key."""
        return self._get_item(key)

    # -------------------------------------------------------------------------
    def __delitem__(self, key):
        """Remove the zone in dict with the given zone name as key."""
        self._del_item(key)

    # -------------------------------------------------------------------------
    def __iter__(self):
        """Iterate through all zone names in current dict."""
        for zone_name in self.keys():
            yield zone_name

    # -------------------------------------------------------------------------
    def __len__(self):
        """Return the number of zones in current dict."""
        return len(self._map)

    # -------------------------------------------------------------------------
    # The next methods aren't required, but nice for different purposes:
    def __str__(self):
        """Return simple dict representation of the mapping."""
        return str(self._map)

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Echoes class, zone_id, & reproducible representation in the REPL."""
        return "{}, {}({})".format(
            super(PowerDNSZoneDict, self).__repr__(), self.__class__.__name__, self._map
        )

    # -------------------------------------------------------------------------
    def __contains__(self, key):
        """Return whether the given zone name is contained in current dict."""
        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == "":
            raise ValueError(self.msg_empty_key_error.format(key))

        return zone_name in self._map

    # -------------------------------------------------------------------------
    def keys(self):
        """Return a sorted list of all zone names in this dict."""
        return sorted(
            self._map.keys(), key=lambda x: cmp_to_key(compare_fqdn)(self._map[x].name_unicode)
        )

    # -------------------------------------------------------------------------
    def items(self):
        """Return tuples (zone name + object as tuple) of this dict in a sorted manner."""
        item_list = []

        for zone_name in self.keys():
            item_list.append((zone_name, self._map[zone_name]))

        return item_list

    # -------------------------------------------------------------------------
    def values(self):
        """Return all zone objects in this dict."""
        value_list = []
        for zone_name in self.keys():
            value_list.append(self._map[zone_name])
        return value_list

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        """Magic method for using it as the '=='-operator."""
        if not isinstance(other, PowerDNSZoneDict):
            raise TypeError(self.msg_no_zone_dict.format(o=other, e="PowerDNSZoneDict"))

        return self._map == other._map

    # -------------------------------------------------------------------------
    def __ne__(self, other):
        """Magic method for using it as the '!='-operator."""
        if not isinstance(other, PowerDNSZoneDict):
            raise TypeError(self.msg_no_zone_dict.format(o=other, e="PowerDNSZoneDict"))

        return self._map != other._map

    # -------------------------------------------------------------------------
    def pop(self, key, *args):
        """Get and return the zone by its name and remove it in dict."""
        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == "":
            raise ValueError(self.msg_empty_key_error.format(key))

        return self._map.pop(zone_name, *args)

    # -------------------------------------------------------------------------
    def popitem(self):
        """Remove and return a arbitrary (zone name and object) pair from the dictionary."""
        if not len(self._map):
            return None

        zone_name = self.keys()[0]
        zone = self._map[zone_name]
        del self._map[zone_name]
        return (zone_name, zone)

    # -------------------------------------------------------------------------
    def clear(self):
        """Remove all items from the dictionary."""
        self._map = {}

    # -------------------------------------------------------------------------
    def setdefault(self, key, default):
        """
        Return the zone, if the key is in dict.

        If not, insert key with a value of default and return default.
        """
        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == "":
            raise ValueError(self.msg_empty_key_error.format(key))

        if not isinstance(default, PowerDNSZone):
            raise TypeError(self.msg_invalid_zone_type.format(default.__class__.__name__))

        if zone_name in self._map:
            return self._map[zone_name]

        self._set_item(zone_name, default)
        return default

    # -------------------------------------------------------------------------
    def update(self, other):
        """Update the dict with the key/value pairs from other, overwriting existing keys."""
        if isinstance(other, PowerDNSZoneDict) or isinstance(other, dict):
            for zone_name in other.keys():
                self._set_item(zone_name, other[zone_name])
            return

        for tokens in other:
            key = tokens[0]
            value = tokens[1]
            self._set_item(key, value)

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """Transform the elements of the object into a dict."""
        res = {}
        for zone_name in self._map:
            res[zone_name] = self._map[zone_name].as_dict(short)
        return res

    # -------------------------------------------------------------------------
    def as_list(self, short=True):
        """Return a list with all zones transformed to a dict."""
        res = []
        for zone_name in self.keys():
            res.append(self._map[zone_name].as_dict(short))
        return res


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
