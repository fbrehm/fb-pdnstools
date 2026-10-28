#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for common used functions.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 by Frank Brehm, Berlin
"""

# Standard modules
import ipaddress
import logging
import re

# Third party modules

# Own modules
from .xlate import XLATOR

__version__ = "2.0.0"

_ = XLATOR.gettext

LOG = logging.getLogger(__name__)

SECONDS_PER_DAY = 24 * 60 * 60
SECONDS_PER_HOUR = 60 * 60
SECONDS_PER_MINUTE = 60

RE_PTR_SUFFIX_V4 = re.compile(r"\.in-addr\.arpa\.?$", re.IGNORECASE)
RE_PTR_SUFFIX_V6 = re.compile(r"\.ip6\.arpa\.?$", re.IGNORECASE)
RE_DOT = re.compile(r"\.")

PAT_IPV4_TUPLE = r"(\d|[1-9]\d|1\d\d|2[0-4]\d|35[0-5])"
PAT_IPV4_REV = r"^({tpl}\.){{0,3}}{tpl}$".format(tpl=PAT_IPV4_TUPLE)
RE_IPV4_REV = re.compile(PAT_IPV4_REV)

PAT_IPV6_REV = r"^(?:[0-9a-f]\.){0,31}[0-9a-f]$"
RE_IPV6_REV = re.compile(PAT_IPV6_REV, re.IGNORECASE)


# =============================================================================
def seconds2human(value, fs=" ", all_fields=False):
    """
    Convert the given value as seconds into a human readable format.

    For instance the value `286623` will be converted into `3d7h37m3s`.

    The units are:
        d - days
        h - hours
        m - minutes
        s - seconds

    If the value is negative, then result will be prepended by `-`.

    If the value is zero, then `0s`` will be returned.

    @param value: the value to convert. It will be interpreted as an integer value.
                  Float values are rounded to an integer.
    @type value: any
    @param fs: the field seperator between the parts of the result.
               e.g. if `fs` is ' ', then the latter result would be `3d 7h 37m 3s`.
    @type fs: str
    @param all_fields: show results of all measuring units, even if they are zero.
    @type all_fields: boolean

    @return: The seconds in a humen readable format.
    @rtype:: str
    """
    fs = str(fs)
    if isinstance(value, int):
        int_val = value
    elif isinstance(value, float):
        int_val = int(value + 0.5)
    elif value is None:
        msg = _("A None type for seconds cannot be converted in seconds.")
        raise TypeError(msg)
    else:
        try:
            int_val = int(value)
        except (TypeError, ValueError) as e:
            msg = _("The value {val!r} cannot be interpreted as seconds: {e}")
            raise ValueError(msg.format(val=value, e=e))

    if int_val == 0:
        if all_fields:
            return "0d" + fs + "0h" + fs + "0m" + fs + "0s"
        else:
            return "0s"

    result = ""
    if int_val < 0:
        result = "-"
        int_val *= -1

    days = int_val // SECONDS_PER_DAY
    rest_days = int_val % SECONDS_PER_DAY

    if days or all_fields:
        if result:
            result += fs
        result += "{}d".format(days)

    hours = rest_days // SECONDS_PER_HOUR
    rest_hours = rest_days % SECONDS_PER_HOUR

    if hours or all_fields:
        if result:
            result += fs
        result += "{}h".format(hours)

    minutes = rest_hours // SECONDS_PER_MINUTE
    seconds = rest_hours % SECONDS_PER_MINUTE

    if minutes or all_fields:
        if result:
            result += fs
        result += "{}m".format(minutes)

    if seconds or all_fields:
        if result:
            result += fs
        result += "{}s".format(seconds)

    return result


# =============================================================================
def ptr2address(reverse_str):
    """Transform a DNS PTR name into an IP address."""
    if not isinstance(reverse_str, str):
        raise TypeError(
            _("Wrong parameter type {!r} on calling ptr2address().").format(
                reverse_str.__class__.__name__
            )
        )

    # ----------------
    def _ptr2address_v4(rev_str):
        if not RE_IPV4_REV.match(rev_str):
            raise ValueError(_("Wrong parameter {!r} calling ptr2address().").format(reverse_str))

        parts = RE_DOT.split(rev_str)
        bitmask = 32
        while len(parts) < 4:
            parts.insert(0, "0")
            bitmask -= 8

        parts.reverse()

        address_str = ".".join(parts)
        if bitmask == 32:
            address = ipaddress.ip_address(address_str)
        else:
            address = ipaddress.ip_network(address_str + "/" + str(bitmask))

        return address

    # ----------------
    def _ptr2address_v6(rev_str):
        if not RE_IPV6_REV.match(rev_str):
            raise ValueError(_("Wrong parameter {!r} calling ptr2address().").format(reverse_str))

        parts = RE_DOT.split(rev_str)
        bitmask = 128
        while len(parts) < 32:
            parts.insert(0, "0")
            bitmask -= 4

        parts.reverse()

        tokens = []
        index = 0
        last = 4
        while index < 32:
            token = "".join(parts[index:last])
            tokens.append(token)
            index += 4
            last += 4

        address_str = ":".join(tokens)
        if bitmask == 128:
            address = ipaddress.ip_address(address_str)
        else:
            address = ipaddress.ip_network(address_str + "/" + str(bitmask))

        return address

    if RE_PTR_SUFFIX_V4.search(reverse_str):
        return _ptr2address_v4(RE_PTR_SUFFIX_V4.sub("", reverse_str))

    if RE_PTR_SUFFIX_V6.search(reverse_str):
        return _ptr2address_v6(RE_PTR_SUFFIX_V6.sub("", reverse_str))

    raise ValueError(_("Wrong parameter {!r} calling ptr2address().").format(reverse_str))


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
