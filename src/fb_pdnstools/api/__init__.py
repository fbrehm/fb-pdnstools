#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for a PowerDNS instance handler object.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 by Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import logging
import re
from collections.abc import Mapping

# Third party modules

from fb_tools.common import is_sequence
from fb_tools.common import pp, to_bool, to_str
from fb_tools.handling_obj import HandlingObject

# Own modules
from .. import DEFAULT_API_PREFIX
from .. import DEFAULT_PORT
from ..descriptors import PosixPathDescriptor
from ..descriptors import StringArrayDescriptor
from ..descriptors import StringDescriptor
from ..errors import PDNSApiResponseError
from ..errors import PDNSApiNotFoundError, PDNSApiValidationError
from ..requestable import BasePdnsRequestableObject
from ..xlate import XLATOR
from ..zone import PowerDNSZone
from ..zonedict import PowerDNSZoneDict

__version__ = "0.1.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PowerDnsApiRoot(BasePdnsRequestableObject):
    """Class for a PowerDNS server handler."""

    api_features = StringArrayDescriptor(name="api_features")
    server_url = PosixPathDescriptor(name="server_url", must_absolute=False, maybe_none=False)

    # -------------------------------------------------------------------------
    def __init__(self, version=__version__, **kwargs):
        """Initialize a PowerDnsApiRoot object."""
        LOG.debug("Got kwargs:\n" + pp(kwargs))

        self.api_features = []
        self.server_url = "servers"
        self.servers = {}

        super(PowerDnsApiRoot, self).__init__(version=version, **kwargs)

        if "initialized" in kwargs:
            self.initialized = kwargs["initialized"]

    # -------------------------------------------------------------------------
    @property
    def request_url_root(self):
        """Return the URL to request for the API root."""
        return self._build_url("")

    # -------------------------------------------------------------------------
    @property
    def request_url_servers(self):
        """Return the URL to request for the API servers."""
        return self._build_url("/" + str(self.server_url))


    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        res = super(PowerDnsApiRoot, self).export_data()

        res["server_url"] = self.server_url

        return res

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(PowerDnsApiRoot, self).as_dict(short=short)

        res["request_url_root"] = self.request_url_root
        res["request_url_servers"] = self.request_url_servers
        res["server_url"] = self.server_url

        return res

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        super(PowerDnsApiRoot, self).import_data(data)
        self.initialized = False

        if "server_url" in data:
            self.server_url = data["server_url"]

        self.initialized = True

    # -------------------------------------------------------------------------
    def explore(self, deep=False):
        """Exploring all data for this API object."""
        LOG.debug(_("Exploring all from API root ..."))

        json_response = self.perform_request("")
        if self.verbose > 3:
            LOG.debug(_("Got a response:") + "\n" + pp(json_response))

        if not is_sequence(json_response):
            msg = _("Response is not a sequence:") + "\n" + pp(json_response)
            raise PDNSApiResponseError(msg)

        if not len(json_response):
            raise PDNSApiResponseError(_("Response has no items."))

        if not isinstance(json_response[0], Mapping):
            msg = _("First response item is not a mapping:") + "\n" + pp(json_response[0])
            raise PDNSApiResponseError(msg)

        if "api_features" in json_response[0]:
            self.api_features = json_response[0]["api_features"]

        if "server_url" in json_response[0]:
            self._set_server_url(json_response[0]["server_url"])

        self.explore_servers(deep=deep)

    # -------------------------------------------------------------------------
    def explore_servers(self, deep=False):
        """Explore all servers from API and build PowerDnsApiRoot objects from them."""
        LOG.debug(_("Exploring all servers from API ..."))

        json_response = self.perform_request("/" + str(self.server_url))
        if self.verbose > 3:
            LOG.debug(_("Got a response:") + "\n" + pp(json_response))

        if not is_sequence(json_response):
            msg = _("Response is not a sequence:") + "\n" + pp(json_response)
            raise PDNSApiResponseError(msg)

        if not len(json_response):
            raise PDNSApiResponseError(_("Response has no items."))

        if self.verbose > 1:
            LOG.debug("Response:" + "\n" + pp(json_response))

        self.servers = {}

        i = 0
        for item in json_response:
            if not isinstance(item, Mapping):
                msg = _("Response item {} is not a mapping:").format(i) + "\n" + pp(item)
                raise PDNSApiResponseError(msg)

            if self.verbose > 1:
                msg = "Creating API server object from:" + "\n" + pp(item)

            i += 1


    # -------------------------------------------------------------------------
    def _set_server_url(self, server_url):

        server_url = str(server_url)
        if self.verbose > 3:
            LOG.debug(f"Mangling server URL: {server_url!r}")

        pat_api_prefix = re.escape(str(self.path_prefix)) + r"/"
        if self.verbose > 3:
            LOG.debug(f"Pattern api prefix: {pat_api_prefix!r}.")
        pat_servers = r"\{/server\}"
        if self.verbose > 3:
            LOG.debug(f"Pattern servers: {pat_servers!r}.")


        server_url = re.sub(pat_api_prefix, "", server_url)
        server_url = re.sub(pat_servers, "", server_url)

        if self.verbose > 2:
            LOG.debug(f"Found server URL: {server_url!r}")

        self.server_url = server_url


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
