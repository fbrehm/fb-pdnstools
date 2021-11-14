#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 by Frank Brehm, Berlin
@summary: The module for a PowerDNS server handler object.
"""
from __future__ import absolute_import

# Standard modules
import logging
import re

# Third party modules

# Own modules
from fb_tools.common import pp, to_bool, to_str

from fb_tools.handling_obj import HandlingObject

from .xlate import XLATOR

from . import BasePowerDNSHandler, DEFAULT_PORT, DEFAULT_API_PREFIX

from .errors import PDNSApiNotFoundError, PDNSApiValidationError

from .zone import PowerDNSZone, PowerDNSZoneDict

__version__ = '0.8.0'
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PowerDNSServer(BasePowerDNSHandler):
    """
    Class for a PowerDNS server handler.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None,
            master_server=None, port=DEFAULT_PORT, key=None, use_https=False,
            path_prefix=DEFAULT_API_PREFIX, simulate=None, force=None,
            terminal_has_colors=False, initialized=False):

        self._api_servername = self.default_api_servername
        self._api_server_version = 'unknown'
        self.zones = None

        super(PowerDNSServer, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir,
            master_server=master_server, port=port, key=key, use_https=use_https,
            path_prefix=path_prefix, simulate=simulate, force=force,
            terminal_has_colors=terminal_has_colors, initialized=False,
        )

        self.initialized = initialized

    # -----------------------------------------------------------
    @property
    def api_server_version(self):
        "The version of the PowerDNS server, how provided by API."
        return self._api_server_version

    # -----------------------------------------------------------
    @HandlingObject.simulate.setter
    def simulate(self, value):
        self._simulate = to_bool(value)

        if self.initialized:
            LOG.debug(_("Setting simulate of all subsequent objects to {!r} ...").format(
                self.simulate))

        if self.zones:
            for zone_name in self.zones:
                self.zones[zone_name].simulate = self.simulate

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(PowerDNSServer, self).as_dict(short=short)
        res['api_server_version'] = self.api_server_version

        return res

    # -------------------------------------------------------------------------
    def get_api_server_version(self):

        path = "/servers/{}".format(self.api_servername)
        try:
            json_response = self.perform_request(path)
        except (PDNSApiNotFoundError, PDNSApiValidationError):
            LOG.error(_("Could not found server info."))
            return None
        if self.verbose > 2:
            LOG.debug(_("Got a response:") + '\n' + pp(json_response))

        if 'version' in json_response:
            self._api_server_version = to_str(json_response['version'])
            LOG.info(_("PowerDNS server version {!r}.").format(self.api_server_version))
            return self.api_server_version
        LOG.error(_("Did not found version info in server info:") + "\n" + pp(json_response))
        return None

    # -------------------------------------------------------------------------
    def get_api_zones(self):

        LOG.debug(_("Trying to get all zones from PDNS API ..."))

        path = "/servers/{}/zones".format(self.api_servername)
        json_response = self.perform_request(path)
        if self.verbose > 3:
            LOG.debug(_("Got a response:") + '\n' + pp(json_response))

        self.zones = PowerDNSZoneDict()

        for data in json_response:
            zone = PowerDNSZone.init_from_dict(
                data, appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
                master_server=self.master_server, port=self.port, key=self.key,
                use_https=self.use_https, timeout=self.timeout, path_prefix=self.path_prefix,
                simulate=self.simulate, force=self.force, initialized=True)
            self.zones.append(zone)
            if self.verbose > 3:
                print("{!r}".format(zone))

        if self.verbose > 1:
            msg = ngettext("Found a zone.", "Found {n} zones.", len(self.zones))
            LOG.debug(msg.format(n=len(self.zones)))

        if self.verbose > 2:
            if self.verbose > 3:
                LOG.debug(_("Zones:") + '\n' + pp(self.zones.as_list()))
            else:
                LOG.debug(_("Zones:") + '\n' + pp(list(self.zones.keys())))

        return self.zones

    # -------------------------------------------------------------------------
    def get_zone_for_item(self, item, is_fqdn=False):

        if not len(self.zones):
            self.get_api_zones()

        fqdn = self.name2fqdn(item, is_fqdn=is_fqdn)
        if not fqdn:
            return None

        if self.verbose > 2:
            LOG.debug(_("Searching an appropriate zone for item {i!r} - FQDN {f!r} ...").format(
                i=item, f=fqdn))

        for zone_name in reversed(self.zones.keys()):
            pattern = r'\.' + re.escape(zone_name) + '$'
            if self.verbose > 3:
                LOG.debug(_("Search pattern: {}").format(pattern))
            if re.search(pattern, fqdn):
                return zone_name
            zone = self.zones[zone_name]
            if zone_name != zone.name_unicode:
                pattern = r'\.' + re.escape(zone.name_unicode) + '$'
                if self.verbose > 3:
                    LOG.debug(_("Search pattern Unicode: {}").format(pattern))
                if re.search(pattern, fqdn):
                    return zone_name

        return None

    # -------------------------------------------------------------------------
    def get_all_zones_for_item(self, item, is_fqdn=False):

        if not len(self.zones):
            self.get_api_zones()

        fqdn = self.name2fqdn(item, is_fqdn=is_fqdn)
        if not fqdn:
            return []

        if self.verbose > 2:
            LOG.debug(_("Searching all appropriate zones for item {i!r} - FQDN {f!r} ...").format(
                i=item, f=fqdn))
        zones = []

        for zone_name in self.zones.keys():
            pattern = r'\.' + re.escape(zone_name) + '$'
            if self.verbose > 3:
                LOG.debug(_("Search pattern: {}").format(pattern))
            if re.search(pattern, fqdn):
                zones.append(zone_name)
                continue
            zone = self.zones[zone_name]
            if zone_name != zone.name_unicode:
                pattern = r'\.' + re.escape(zone.name_unicode) + '$'
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
