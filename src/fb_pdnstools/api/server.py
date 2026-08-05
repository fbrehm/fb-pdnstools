#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for a PowerDNS server handler object.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 by Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import logging
import re

# Third party modules

from fb_tools.common import pp, to_bool, to_str
from fb_tools.handling_obj import HandlingObject

# Own modules
from .. import DEFAULT_API_PREFIX
from .. import DEFAULT_PORT
from .zone import PowerDNSZone
from .zonedict import PowerDNSZoneDict
from ..descriptors import StringDescriptor
from ..errors import PDNSApiNotFoundError, PDNSApiValidationError
from ..requestable import BasePdnsRequestableObject
from ..xlate import XLATOR

__version__ = "1.2.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PowerDNSServer(BasePdnsRequestableObject):
    """Class for a PowerDNS server handler."""

    api_server_version = StringDescriptor("api_server_version", stripped=True)

    # -------------------------------------------------------------------------
    def __init__(self, version=__version__, **kwargs):
        """Initialize a PowerDNSServer record."""
        self.api_server_version = "unknown"
        self.zones = None

        LOG.debug("Got kwargs:\n" + pp(kwargs))

        super(PowerDNSServer, self).__init__(version=version, **kwargs)

        if "initialized" in kwargs:
            self.initialized = kwargs["initialized"]

    # -----------------------------------------------------------
    @HandlingObject.simulate.setter
    def simulate(self, value):
        """Override the setter of the simulate property."""
        self._simulate = to_bool(value)

        if self.initialized:
            LOG.debug(
                _("Setting simulate of all subsequent objects to {!r} ...").format(self.simulate)
            )

        if self.zones:
            for zone_name in self.zones:
                self.zones[zone_name].simulate = self.simulate

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        res = super(PowerDNSServer, self).export_data()

        res["api_server_version"] = self.api_server_version
        res["zones"] = {}

        if self.zones:
            for zone_name in self.zones:
                res["zones"][zone_name] = self.zones[zone_name].export_data()

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
        res = super(PowerDNSServer, self).as_dict(short=short)

        res["api_server_version"] = self.api_server_version

        return res

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        super(PowerDNSServer, self).import_data(data)
        self.initialized = False

        if not self.zones:
            self.zones = PowerDNSZoneDict()

        for zone_name in data:
            zone_data = data[zone_name]
            zone = PowerDNSZone.init_from_dict(
                zone_data,
                appname=self.appname,
                verbose=self.verbose,
                base_dir=self.base_dir,
                master_server=self.master_server,
                port=self.port,
                api_key=self.api_key,
                use_https=self.use_https,
                timeout=self.timeout,
                path_prefix=self.path_prefix,
                simulate=self.simulate,
                force=self.force,
                initialized=True,
            )
            self.zones[zone_name] = zone

        self.initialized = True

    # -------------------------------------------------------------------------
    def get_api_server_version(self):
        """Retreive from PowerDNS API their server version."""
        path = "/servers/{}".format(self.api_servername)
        try:
            json_response = self.perform_request(path)
        except (PDNSApiNotFoundError, PDNSApiValidationError):
            LOG.error(_("Could not found server info."))
            return None
        if self.verbose > 2:
            LOG.debug(_("Got a response:") + "\n" + pp(json_response))

        if "version" in json_response:
            self._api_server_version = to_str(json_response["version"])
            LOG.info(_("PowerDNS server version {!r}.").format(self.api_server_version))
            return self.api_server_version
        LOG.error(_("Did not found version info in server info:") + "\n" + pp(json_response))
        return None

    # -------------------------------------------------------------------------
    def get_api_zones(self):
        """Pull from PowerDNS API a list of all zones and return them as a PowerDNSZoneDict."""
        LOG.debug(_("Trying to get all zones from PDNS API ..."))

        path = "/servers/{}/zones".format(self.api_servername)
        json_response = self.perform_request(path)
        if self.verbose > 3:
            LOG.debug(_("Got a response:") + "\n" + pp(json_response))

        self.zones = PowerDNSZoneDict()

        for data in json_response:
            zone = PowerDNSZone.init_from_dict(
                data,
                appname=self.appname,
                verbose=self.verbose,
                base_dir=self.base_dir,
                master_server=self.master_server,
                port=self.port,
                api_key=self.api_key,
                use_https=self.use_https,
                timeout=self.timeout,
                path_prefix=self.path_prefix,
                simulate=self.simulate,
                force=self.force,
                initialized=True,
            )
            self.zones.append(zone)
            if self.verbose > 3:
                print("{!r}".format(zone))

        if self.verbose > 1:
            msg = ngettext("Found a zone.", "Found {n} zones.", len(self.zones))
            LOG.debug(msg.format(n=len(self.zones)))

        if self.verbose > 2:
            if self.verbose > 3:
                LOG.debug(_("Zones:") + "\n" + pp(self.zones.as_list()))
            else:
                LOG.debug(_("Zones:") + "\n" + pp(list(self.zones.keys())))

        return self.zones

    # -------------------------------------------------------------------------
    def get_zone_for_item(self, item, is_fqdn=False):
        """Search for the best fitting zone for the given FQDN."""
        if not len(self.zones):
            self.get_api_zones()

        fqdn = self.name2fqdn(item, is_fqdn=is_fqdn)
        if not fqdn:
            return None

        if self.verbose > 2:
            LOG.debug(
                _("Searching an appropriate zone for item {i!r} - FQDN {f!r} ...").format(
                    i=item, f=fqdn
                )
            )

        for zone_name in reversed(self.zones.keys()):
            pattern = r"\." + re.escape(zone_name) + "$"
            if self.verbose > 3:
                LOG.debug(_("Search pattern: {}").format(pattern))
            if re.search(pattern, fqdn):
                return zone_name
            zone = self.zones[zone_name]
            if zone_name != zone.name_unicode:
                pattern = r"\." + re.escape(zone.name_unicode) + "$"
                if self.verbose > 3:
                    LOG.debug(_("Search pattern Unicode: {}").format(pattern))
                if re.search(pattern, fqdn):
                    return zone_name

        return None

    # -------------------------------------------------------------------------
    def get_all_zones_for_item(self, item, is_fqdn=False):
        """Search for all fitting zones for the given FQDN."""
        if not len(self.zones):
            self.get_api_zones()

        fqdn = self.name2fqdn(item, is_fqdn=is_fqdn)
        if not fqdn:
            return []

        if self.verbose > 2:
            LOG.debug(
                _("Searching all appropriate zones for item {i!r} - FQDN {f!r} ...").format(
                    i=item, f=fqdn
                )
            )
        zones = []

        for zone_name in self.zones.keys():
            pattern = r"\." + re.escape(zone_name) + "$"
            if self.verbose > 3:
                LOG.debug(_("Search pattern: {}").format(pattern))
            if re.search(pattern, fqdn):
                zones.append(zone_name)
                continue
            zone = self.zones[zone_name]
            if zone_name != zone.name_unicode:
                pattern = r"\." + re.escape(zone.name_unicode) + "$"
                if self.verbose > 3:
                    LOG.debug(_("Search pattern Unicode: {}").format(pattern))
                if re.search(pattern, fqdn):
                    zones.append(zone_name)

        return zones


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
