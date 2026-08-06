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
from collections.abc import Mapping

# Third party modules

from fb_tools.common import pp, to_bool, to_str
from fb_tools.handling_obj import HandlingObject

try:
        from semver import Version
except ImportError:
        from semver import VersionInfo as Version

# Own modules
from .. import DEFAULT_API_PREFIX
from .. import DEFAULT_PORT
from .. import DEFAULT_SERVER_AUTOPRIMARIES_URl
from .. import DEFAULT_SERVER_CONFIG_URL
from .. import DEFAULT_SERVER_DAEMON_TYPE
from .. import DEFAULT_SERVER_NAME
from .. import DEFAULT_SERVER_TYPE
from .. import DEFAULT_SERVER_ZONES_URL
from ..descriptors import PosixPathDescriptor
from ..descriptors import StringDescriptor
from ..descriptors import VersionDescriptor
from ..errors import PDNSApiNotFoundError, PDNSApiValidationError
from ..requestable import BasePdnsRequestableObject
from ..xlate import XLATOR
from .zone import PowerDNSZone
from .zonedict import PowerDNSZoneDict

__version__ = "2.0.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PowerDNSServer(BasePdnsRequestableObject):
    """Class for a PowerDNS server handler."""

    autoprimaries_url = PosixPathDescriptor(
        "autoprimaries_url", must_absolute=False, maybe_none=False
    )
    config_url = PosixPathDescriptor("config_url", must_absolute=False, maybe_none=False)
    daemon_type = StringDescriptor("daemon_type", maybe_none=True, stripped=True)
    server_version = VersionDescriptor("server_version", maybe_none=True)
    type = StringDescriptor("type", maybe_none=True, stripped=True)
    url = PosixPathDescriptor("url", must_absolute=False, maybe_none=False)
    zones_url = PosixPathDescriptor("zones_url", must_absolute=False, maybe_none=False)

    default_autoprimaries_url = "servers/" + DEFAULT_SERVER_NAME + "/" + DEFAULT_SERVER_AUTOPRIMARIES_URl
    default_config_url = "servers/" + DEFAULT_SERVER_NAME + "/" + DEFAULT_SERVER_CONFIG_URL
    default_url = "servers/" + DEFAULT_SERVER_NAME
    default_zones_url = "servers/" + DEFAULT_SERVER_NAME + "/" + DEFAULT_SERVER_ZONES_URL

    # -------------------------------------------------------------------------
    def __init__(
            self,
            autoprimaries_url=None,
            config_url=None,
            daemon_type=None,
            server_version=None,
            type=None,
            url=None,
            zones_url=None,
            version=__version__,
            **kwargs
        ):
        """Initialize a PowerDNSServer record."""
        self.autoprimaries_url = self.default_autoprimaries_url
        self.config_url = self.default_config_url
        self.daemon_type = DEFAULT_SERVER_DAEMON_TYPE
        self.server_version = None
        self.type = DEFAULT_SERVER_TYPE
        self.url = self.default_url
        self.zones_url = self.default_zones_url

        self.zones = None

        LOG.debug("Got kwargs:\n" + pp(kwargs))

        super(PowerDNSServer, self).__init__(version=version, **kwargs)

        if autoprimaries_url is not None:
            url = re_api_prefix.sub("", autoprimaries_url)
            url = re_autoprimary.sub("", url)
            self.autoprimaries_url = url

        if config_url is not None:
            url = re_api_prefix.sub("", config_url)
            url = re_config.sub("", url)
            self.config_url = url

        if daemon_type is not None:
            self.daemon_type = daemon_type

        if server_version is not None:
            self.server_version = server_version

        if type is not None:
            self.type = type

        if url is not None:
            self.url = url

        if zones_url is not None:
            url = re_api_prefix.sub("", zones_url)


        self.zones = None

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

        res["autoprimaries_url"] = str(self.path_prefix) + "/" + str(self.autoprimaries_url) + "{/autoprimary}"
        res["config_url"] = str(self.path_prefix) + "/" + self.config_url + "{/config_setting}"
        res["daemon_type"] = self.daemon_type
        res["id"] = self.api_servername
        res["type"] = self.type
        res["url"] = self.str(self.path_prefix)
        if self.url:
            res["url"] += "/" + self.url
        res["version"] = str(self.server_version)
        res["zones_url"] = str(self.path_prefix) + "/" + self.zones_url + "{/zone}"
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

        res["autoprimaries_url"] = self.autoprimaries_url
        res["config_url"] = self.config_url
        res["daemon_type"] = self.daemon_type
        res["server_version"] = self.server_version
        res["type"] = self.type
        res["url"] = self.url
        res["zones_url"] = self.zones_url

        return res

    # -------------------------------------------------------------------------
    def import_server_data(self, data):
        """Import data from API related to the API server itself."""
        if not isinstance(data, Mapping):
            msg = _("Given data are not a Mapping, but a {what} instead.").format(
                what=data.__class__.__name__
            )
            raise TypeError(msg)

        LOG.debug("Importing server related data ...")
        if self.verbose > 1:
            LOG.debug("Server data to import:" + "\n" + pp(data))

        pat_api_prefix = re.escape(str(self.path_prefix)) + r"/"
        pat_autoprimary = r"\{/autoprimary\}"
        pat_config = r"\{/config_setting\}"
        pat_zone = r"\{/zone\}"

        re_api_prefix = re.compile(pat_api_prefix)
        re_autoprimary = re.compile(pat_autoprimary)
        re_config = re.compile(pat_config)
        re_zone = re.compile(pat_zone)

        if "autoprimaries_url" in data:
            ap_url = re_api_prefix.sub("", data["autoprimaries_url"])
            ap_url = re_autoprimary.sub("", ap_url)
            self.autoprimaries_url = ap_url

        if "config_url" in data:
            url = re_api_prefix.sub("", data["config_url"])
            url = re_config.sub("", url)
            self.config_url = url

        if "daemon_type" in data:
            self.daemon_type = data["daemon_type"]

        if "id" in data:
            self.api_servername = data["id"]

        if "type" in data:
            self.type = data["type"]

        if url is not None:
            url = re_api_prefix.sub("", data["url"])
            self.url = url

        if "version" in data:
            self.server_version =  data["version"]

        if "zones_url" in data:
            url = re_api_prefix.sub("", data["zones_url"])
            url = re_zone.sub("", url)
            self.zones_url = url

    # -------------------------------------------------------------------------
    def get_repr_fields(self):
        """Return a list of parameters prepared for __repr__()."""
        fields = []

        if str(self.autoprimaries_url) != self.default_autoprimaries_url:
            fields.append("autoprimaries_url={!r}".format(str(self.autoprimaries_url)))
        if str(self.config_url) != self.default_config_url:
            fields.append("config_url={!r}".format(str(self.config_url)))
        if self.daemon_type != DEFAULT_SERVER_DAEMON_TYPE:
            fields.append("daemon_type={!r}".format(self.daemon_type))
        if self.server_version:
            fields.append("server_version={!r}".format(str(self.server_version)))
        if self.type != DEFAULT_SERVER_TYPE:
            fields.append("type={!r}".format(self.type))
        if str(self.url) != self.default_url:
            fields.append("urll={!r}".format(str(self.url)))
        if str(self.zones_url) != self.default_zones_url:
            fields.append("zones_url={!r}".format(str(self.zones_url)))

        fields += super(PowerDNSServer, self).get_repr_fields()

        return fields

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
    def get_server_version(self):
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
            self._server_version = to_str(json_response["version"])
            LOG.info(_("PowerDNS server version {!r}.").format(self.server_version))
            return self.server_version
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
