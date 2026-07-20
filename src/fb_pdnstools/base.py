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
from abc import ABCMeta

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

# Third party modules
from fb_tools.common import RE_DOT_AT_END
from fb_tools.common import pp
from fb_tools.common import reverse_pointer
from fb_tools.common import to_bool
from fb_tools.common import to_str
from fb_tools.handling_obj import HandlingObject

import requests
from requests.exceptions import RequestException

import six
from six import add_metaclass

import urllib3

# Own modules
from . import DEFAULT_API_PREFIX
from . import DEFAULT_PORT
from . import DEFAULT_TIMEOUT
from . import DEFAULT_USE_HTTPS
from . import LIBRARY_NAME
from . import MAX_PORT_NUMBER
from . import VALID_RRSET_TYPES
from .errors import PDNSApiError
from .errors import PDNSApiNotAuthorizedError
from .errors import PDNSApiNotFoundError
from .errors import PDNSApiRateLimitExceededError
from .errors import PDNSApiValidationError
from .errors import PDNSRequestError
from .errors import PowerDNSHandlerError
from .xlate import XLATOR

__version__ = "2.0.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
@add_metaclass(ABCMeta)
class BasePdnsObject(HandlingObject):
    """
    Base class for a PowerDNS object.

    Properties:
    * address_family      (str or int   - rw)
    * appname             (str          - rw) (inherited from FbBaseObject)
    * assumed_answer      (None or bool - rw)
    * base_dir            (pathlib.Path - rw) (inherited from FbBaseObject)
    * cache_dir           (pathlib.Path - rw)
    * data_dir            (pathlib.Path - rw)
    * force               (bool         - rw)
    * initialized         (bool         - rw) (inherited from FbBaseObject)
    * interrupted         (bool         - rw)
    * is_venv             (bool         - ro)
    * project_name        (str)         - rw)
    * prompt_timeout      (int          - rw)
    * quiet               (bool         - rw)
    * simulate            (bool         - rw)
    * state_dir           (pathlib.Path - rw)
    * terminal_has_colors (bool         - rw)
    * verbose             (int          - rw) (inherited from FbBaseObject)
    * version             (str          - ro) (inherited from FbBaseObject)

    Public attributes:
    * add_search_paths       Array of Path
    * signals_dont_interrupt Array of int
     Must not be instantiated directly.
    """

    fields = {
        "description": "",
    }

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        *args,
        **kwargs,
    ):
        """Initialize a BasePdnsObject object."""
        super(BasePdnsObject, self).__init__(*args, **kwargs, version=version)

        if "initialized" in kwargs:
            self.initialized = kwargs["initialized"]

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

