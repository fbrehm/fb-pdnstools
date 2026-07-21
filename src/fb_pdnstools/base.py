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

# Third party modules
from fb_tools.common import RE_DOT_AT_END
from fb_tools.common import reverse_pointer
from fb_tools.common import to_bool
from fb_tools.common import to_str
from fb_tools.handling_obj import HandlingObject

import six
from six import add_metaclass

# Own modules
from . import VALID_RRSET_TYPES
from .descriptors import IntegerDescriptor
from .descriptors import StringArrayDescriptor
from .descriptors import StringDescriptor
from .errors import PowerDNSHandlerError
from .xlate import XLATOR

__version__ = "0.4.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
@add_metaclass(ABCMeta)
class BasePdnsObject(HandlingObject):
    """
    Base class for a PowerDNS object.

    Properties:
    * address_family      (str or int   - rw) (inherited from HandlingObject)
    * appname             (str          - rw) (inherited from FbBaseObject)
    * assumed_answer      (None or bool - rw) (inherited from HandlingObject)
    * base_dir            (pathlib.Path - rw) (inherited from FbBaseObject)
    * cache_dir           (pathlib.Path - rw) (inherited from HandlingObject)
    * data_dir            (pathlib.Path - rw) (inherited from HandlingObject)
    * force               (bool         - rw) (inherited from HandlingObject)
    * initialized         (bool         - rw) (inherited from FbBaseObject)
    * interrupted         (bool         - rw) (inherited from HandlingObject)
    * is_venv             (bool         - ro) (inherited from HandlingObject)
    * project_name        (str)         - rw) (inherited from HandlingObject)
    * prompt_timeout      (int          - rw) (inherited from HandlingObject)
    * quiet               (bool         - rw) (inherited from HandlingObject)
    * simulate            (bool         - rw) (inherited from HandlingObject)
    * state_dir           (pathlib.Path - rw) (inherited from HandlingObject)
    * terminal_has_colors (bool         - rw) (inherited from HandlingObject)
    * verbose             (int          - rw) (inherited from FbBaseObject)
    * version             (str          - ro) (inherited from FbBaseObject)

    Public attributes:
    * add_search_paths       Array of Path
    * signals_dont_interrupt Array of int

     Must not be instantiated directly.
    """

    fields = {"description": {"type": "str", "desc": "Bogus field", "default": "Senseless stuff."}}

    base_init_args = (
        "appname",
        "assumed_answer",
        "base_dir",
        "cache_dir",
        "data_dir",
        "force",
        "initialized",
        "project_name",
        "quiet",
        "runtime_dir",
        "simulate",
        "state_dir",
        "terminal_has_colors",
        "verbose",
        "version",
    )

    # -------------------------------------------------------------------------
    @classmethod
    def init_field_objects(cls):
        """Initialise all API fields as attributes."""
        for field_name in cls.fields:
            ftype = cls.fields[field_name]["type"]

            lowcase = False
            if "lowcase" in cls.fields[field_name]:
                lowcase = to_bool(cls.fields[field_name]["lowcase"])

            stripped = False
            if "stripped" in cls.fields[field_name]:
                stripped = to_bool(cls.fields[field_name]["stripped"])

            if ftype == "int":
                desriptor_class = IntegerDescriptor
            elif ftype == "str":
                desriptor_class = StringDescriptor
            elif ftype == "array_of_str":
                desriptor_class = StringArrayDescriptor
            else:
                msg = _("Unknown field type {!r}.").format(ftype)
                raise RuntimeError(msg)

            desriptor = desriptor_class()
            desriptor.__set_name__(cls, field_name)

            if field_name in ("str", "array_of_str"):
                desriptor.lowcase = lowcase
                desriptor.stripped = stripped

            setattr(cls, field_name, desriptor)

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        *args,
        **kwargs,
    ):
        """Initialize a BasePdnsObject object."""
        self.init_field_objects()

        for field_name in self.fields:
            default = self.fields[field_name]["default"]
            cls = self.__class__.__name__
            LOG.debug(f"Setting default of {cls}.{field_name} to {default!r}.")
            setattr(self, field_name, default)

        base_kwargs = {}
        for key in kwargs.keys():
            if key in self.base_init_args:
                base_kwargs[key] = kwargs[key]
            elif key not in self.fields:
                msg = _("Invalid parameter {p!r} for {c}.{f}.").format(
                    p=key, c=self.__class__.__name__, f="__init__()"
                )
                raise PowerDNSHandlerError(msg)

        for key in self.base_init_args:
            if key in kwargs:
                del kwargs[key]

        # LOG.debug("base_kwargs:" + "\n" + pp(base_kwargs))
        # LOG.debug("Remaining kwargs:" + "\n" + pp(kwargs))

        super(BasePdnsObject, self).__init__(*args, **base_kwargs, version=version)

        if "initialized" in kwargs:
            self.initialized = kwargs["initialized"]

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(BasePdnsObject, self).as_dict(short=short)

        for field_name in self.fields:
            value = getattr(self, field_name)
            res[field_name] = value

        return res

    # -------------------------------------------------------------------------
    @abstractmethod
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<%s()>" % (self.__class__.__name__)
        return out

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
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
