#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for a base PowerDNS object.

This class is a successor of fb_tools.handling_obj.HandlingObject.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
"""

from __future__ import absolute_import

# Standard modules
import ipaddress
import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping

# Third party modules
from fb_tools.common import RE_DOT_AT_END
from fb_tools.common import reverse_pointer
from fb_tools.common import to_str
from fb_tools.handling_obj import HandlingObject
from fb_tools.obj import FbBaseObject
from fb_tools.obj import FbGenericBaseObject

import six
from six import add_metaclass

# Own modules
from . import VALID_RRSET_TYPES
from .xlate import XLATOR

__version__ = "0.5.1"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
@add_metaclass(ABCMeta)
class GenericPdnsObject(FbGenericBaseObject):
    """
    Generic base class for a PowerDNS object.

    Must not be instantiated directly.
    """

    # -------------------------------------------------------------------------
    @abstractmethod
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        if not isinstance(data, Mapping):
            msg = _("Given data are not a Mapping, but a {what} instead.").format(
                what=data.__class__.__name__
            )
            raise TypeError(msg)

    # -------------------------------------------------------------------------
    @abstractmethod
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        return {}

    # -------------------------------------------------------------------------
    def canon_name(self, name):
        """Canonize the DNS name, that means ensure a dot at the end of the name."""
        ret = RE_DOT_AT_END.sub(".", name, 1)
        return ret

    # -------------------------------------------------------------------------
    def name2fqdn(self, name, is_fqdn=False):
        """
        Transform the given name into a canonized FQDN.

        If an IP address as name is given (and the parameter 'is_fqdn' is False), then
        this name will be transformed into a reverse pointer address
        (e.g. '4.3.2.1..in-addr.arpa.').
        """
        fqdn = name

        if not is_fqdn:
            try:
                address = ipaddress.ip_address(name)
                fqdn = reverse_pointer(address)
                is_fqdn = False
            except ValueError:
                if self.verbose > 3:
                    LOG.debug(_("Name {!r} is not a valid IP address.").format(name))
                is_fqdn = True
                fqdn = name

        if ":" in fqdn:
            LOG.error(_("Invalid FQDN {!r}.").format(fqdn))
            return None

        return self.canon_name(fqdn)

    # -------------------------------------------------------------------------
    def decanon_name(self, name):
        """Decanonize the FQDN - removing possible dots at the end of the name."""
        ret = RE_DOT_AT_END.sub("", name)
        return ret

    # -------------------------------------------------------------------------
    def verify_rrset_type(self, rtype, raise_on_error=True):
        """Verify, that the given name is a valid RRset type name."""
        if not isinstance(rtype, six.string_types):
            msg = _("A rrset type must be a string type, but is {!r} instead.").format(rtype)
            if raise_on_error:
                raise TypeError(msg)
            LOG.error(msg)
            return None

        type_used = to_str(rtype).strip().upper()
        if not type_used:
            msg = _("Invalid, empty rrset type {!r} given.").format(rtype)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        if type_used not in VALID_RRSET_TYPES:
            msg = _("Invalid rrset type {!r} given.").format(rtype)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        return type_used


# =============================================================================
@add_metaclass(ABCMeta)
class BasePdnsObject(FbBaseObject, GenericPdnsObject):
    """
    Base class for a PowerDNS object.

    Must not be instantiated directly.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        **kwargs,
    ):
        """Initialize a PowerDNSRecord record."""
        super(BasePdnsObject, self).__init__(version=version, **kwargs)


# =============================================================================
@add_metaclass(ABCMeta)
class BasePdnsHandler(HandlingObject, GenericPdnsObject):
    """
    Base class for a PowerDNS handler object.

    Must not be instantiated directly.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        **kwargs,
    ):
        """Initialize a PowerDNSRecord record."""
        super(BasePdnsHandler, self).__init__(version=version, **kwargs)


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
