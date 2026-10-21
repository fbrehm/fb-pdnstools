#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: A module for providing a configuration for PowerDNS applications.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2022 - 2026 by Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard module
import logging
import os
import re

# Third party modules

from fb_tools.common import is_sequence
from fb_tools.common import pp
from fb_tools.common import to_bool
from fb_tools.multi_config import BaseMultiConfig
from fb_tools.obj import FbBaseObject

# Own modules
from . import DEFAULT_API_PREFIX
from . import DEFAULT_PORT
from . import DEFAULT_TIMEOUT
from . import DEFAULT_USE_HTTPS
from . import MAX_PORT_NUMBER
from .base import GenericPdnsObject
from .descriptors import BooleanDescriptor
from .descriptors import IntegerDescriptor
from .descriptors import PosixPathDescriptor
from .descriptors import StringDescriptor
from .errors import PowerDNSConfigError
from .xlate import XLATOR

__version__ = "0.2.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

DEFAULT_CONFIG_DIR = "fbrehm"

# =============================================================================
class PdnsApiConfigInfo(GenericPdnsObject):
    """Encapsulating all necessary data to connect to a PowerDNS API."""

    default_port = DEFAULT_PORT
    default_use_https = DEFAULT_USE_HTTPS
    default_prefix = DEFAULT_API_PREFIX
    default_timeout = DEFAULT_TIMEOUT

    # Object properties
    host = StringDescriptor(
        name="host", lowcase=True, stripped=True, maybe_none=True, not_empty=True)
    port = IntegerDescriptor(name="port", lower_limit=1, upper_limit=MAX_PORT_NUMBER)
    use_https = BooleanDescriptor(name="use_https")
    key = StringDescriptor(name="key", stripped=True, maybe_none=True, not_empty=True)
    prefix = PosixPathDescriptor(name="prefix", must_absolute=True, maybe_none=True)
    timeout = IntegerDescriptor(name="timeout", lower_limit=1, upper_limit=3600)
    initialized = BooleanDescriptor(name="initialized")

    port.lower_limit_msg = _(
        "Invalid port number {v} for the PowerDNS API, must be greater than zero."
    )
    port.upper_limit_msg = _(
        "Invalid port number {{v}} for the PowerDNS API, must be less or equal to {m}."
    ).format(m=MAX_PORT_NUMBER)

    re_use_https = re.compile(r"^(?:use[-_]?)?https$", re.IGNORECASE)
    re_api_key = re.compile(r"^(?:api[-_]?)?key$", re.IGNORECASE)

    # -------------------------------------------------------------------------
    def __init__(
        self,
        host=None,
        port=DEFAULT_PORT,
        use_https=DEFAULT_USE_HTTPS,
        key=None,
        prefix=DEFAULT_API_PREFIX,
        timeout=DEFAULT_TIMEOUT,
        initialized=False
    ):
        """Initialize the PdnsApiConfigInfo object."""
        self.host = host
        self.port = port
        self.use_https = use_https
        self.key = key
        self.prefix = prefix
        self.timeout = timeout
        self.initialized = False

        if initialized:
            self.initialized = True

    # -------------------------------------------------------------------------
    @classmethod
    def from_config(cls, section_name, section, raise_on_error=False):
        """Create a new PdnsApiConfigInfo object based on the data from config."""
        info = cls(initialized=False)

        try:
            for key in section.keys():
                value = section[key]

                if key.lower() == "host":
                    info.host = value
                    continue
                if key.lower() == "port":
                    info.port = value
                    continue
                if cls.re_use_https.match(key):
                    info.use_https = value
                    continue
                if cls.re_api_key.match(key):
                    info.key = value
                    continue
                if key.lower() == "prefix":
                    info.prefix = value
                    continue
                if key.lower() == "timeout":
                    info.timeout = value
                    continue

                msg = _(
                    "Unknown key {k!r} with value {v!r} for PowerDNS API in section {sec!r} found."
                ).format(k=key, v=value, sec=section_name)
                LOG.warn(msg)

        except Exception as e:
            msg = _("{e} in section {sn!r} for PowerDNS:").format(
                e=e.__class__.__name__, sn=section_name
            )
            msg += " " + str(e)
            if raise_on_error:
                raise PowerDNSConfigError(msg)
            else:
                LOG.warn(msg)

        if not info.host or not info.key:
            if raise_on_error:
                msg = _(
                    "There must be given at least the PowerDNS API hostname and the "
                    "API key in section {sn!r}."
                ).format(sec=section_name)
                raise PowerDNSConfigError(msg)
            else:
                msg = _(
                    "There should be given at least the PowerDNS API hostname and the "
                    "API key in section {sn!r}."
                ).format(sec=section_name)
                LOG.debug(msg)

        info.initialized = True

        return info

    # -------------------------------------------------------------------------
    def get_repr_fields(self):
        """Return a list of parameters prepared for __repr__()."""
        fields = []

        if self.host is not None:
            fields.append(f"host={self.host!r}")
        if self.port != DEFAULT_PORT:
            fields.append(f"port={self.port!r}")
        if self.use_https != DEFAULT_USE_HTTPS:
            fields.append(f"use_https={self.use_https!r}")
        if self.key is not None:
            fields.append("key={!r}".format("********"))
        if self.timeout != DEFAULT_TIMEOUT:
            fields.append(f"timeout={self.timeout!r}")
        if str(self.prefix) != DEFAULT_API_PREFIX:
            fields.append(f"prefix={self.prefix!r}")
        if self.initialized:
            fields.append(f"initialized={self.initialized!r}")

        return fields

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data."""
        super(PdnsApiConfigInfo, self).import_data(data)
        self.initialized = False

        if "host" in data:
            self.host = data["host"]
        if "port" in data:
            self.port = data["port"]
        if "key" in data:
            self.key = data["key"]
        if "prefix" in data:
            self.prefix = data["prefix"]
        if "use_https" in data:
            self.use_https = data["use_https"]
        if "timeout" in data:
            self.timeout = data["timeout"]

        self.initialized = True

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        res = {
            "host": self.host,
            "port": self.port,
            "key": self.key,
            "default_port": self.default_port,
            "default_prefix": self.default_prefix,
            "default_timeout": self.default_timeout,
            "prefix": self.prefix,
            "use_https": self.use_https,
            "timeout": self.timeout,
        }

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
        res = super(PdnsApiConfigInfo, self).as_dict(short=short)

        res.update(self.export_data())

        res["initialized"] = self.initialized

        if self.key:
            if "SHOW_PDNS_SECRETS" in os.environ and to_bool(os.environ["SHOW_PDNS_SECRETS"]):
                res["key"] = self.key
            elif self.key:
                res["key"] = "*******"

        return res

# =============================================================================
class PdnsApiConfig(BaseMultiConfig):
    """
    A class for providing a configuration for a PowerDNS API instance.

    There are also methods to read it from configuration files.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        config_dir=DEFAULT_CONFIG_DIR,
        additional_stems=None,
        mandatory=False,
        initialized=False,
        **kwargs
    ):
        """Initialize a PdnsApiConfig object."""
        self.mandatory = bool(mandatory)

        add_stems = []
        if additional_stems:
            if is_sequence(additional_stems):
                for stem in additional_stems:
                    add_stems.append(stem)
            else:
                add_stems.append(additional_stems)

        if "pdns" not in add_stems:
            add_stems.append("pdns")
        if "powerdns" not in add_stems:
            add_stems.append("powerdns")

        self.pdns_api = None

        super(PdnsApiConfig, self).__init__(
            version=version,
            config_dir=config_dir,
            additional_stems=add_stems,
            initialized=False,
        )

        if initialized:
            self.initialized = True

    # -------------------------------------------------------------------------
    def eval(self):     # noqa: A003
        """Evaluate configuration and store it in object properties."""
        super(PdnsApiConfig, self).eval()

        if not self.pdns_api:
            msg = _("Did not found configuration for PowerDNS.") + " "

            if self.config_files:
                cfgfiles = [str(f) for f in self.config_files].sort(key=str.lower)
                msg += "Considered configuration files:" + "\n"
                msg += pp(cfgfiles)
            else:
                msg += "No appropriate configuration files found."

            if self.mandatory:
                raise PowerDNSConfigError(msg)
            else:
                LOG.debug(msg)

    # -------------------------------------------------------------------------
    def eval_section(self, section_name):
        """Evaluate a particular configuration section."""
        super(PdnsApiConfig, self).eval_section(section_name)
        sn = section_name.lower()

        if sn == "pdns" or sn == "powerdns":

            section = self.cfg[section_name]

            if self.verbose > 2:
                LOG.debug(
                    _("Evaluating config section {!r}:").format(section_name) + "\n" + pp(section)
                )

            self.pdns_api = PdnsApiConfigInfo.from_config(
                section_name=section_name,
                section=section,
                verbose=self.verbose,
                base_dir=self.base_dir,
            )


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
