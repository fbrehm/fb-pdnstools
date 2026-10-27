#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for the 'pdns-remove-addresses' application object.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 by Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import copy
# import ipaddress
import locale
import logging
import os
import re
import sys
# from functools import cmp_to_key
from pathlib import Path

# Third party modules
from fb_tools.common import pp
# from fb_tools.common import reverse_pointer
# from fb_tools.common import to_bool
from fb_tools.common import to_str

# Own modules
from . import BasePowerDNSApplication
# from . import PdnsAppError
from .. import __version__ as GLOBAL_VERSION
from ..descriptors import BooleanDescriptor
from ..xlate import XLATOR

__version__ = "0.3.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

# =============================================================================
class PdnsRemoveAddrApp(BasePowerDNSApplication):
    """Class for the application object of the pdns-remove-addresses application."""

    show_simulate_option = True

    remove_reverse = BooleanDescriptor(name="remove_reverse")

    re_comment = re.compile(r"\s*#.*")
    re_whitespace = re.compile(r"\s+")

    # -------------------------------------------------------------------------
    def __init__(self, version=GLOBAL_VERSION, *args, **kwargs):
        """Initialize the PdnsRemoveAddrApp object."""
        desc = _(
            "Removes the given addresses (A-, AAAA- or CNAME-Records) completety from "
            "PowerDNS. If there are multiple entries to a DNS-Name, all appropriate "
            "records are removed. Additionally all appropriate reverse entries (PTR-records) "
            "were also removed, if they are pointing back to the given A- or AAAA-record."
        )

        self.remove_reverse = True

        self.address_files = []
        self.addresses = []
        self.records2remove = {}
        self.expected_ptr = None
        self.zones = {}

        super(PdnsRemoveAddrApp, self).__init__(
            *args,
            description=desc,
            version=version,
            **kwargs,
        )

        self.initialized = True

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(PdnsRemoveAddrApp, self).as_dict(short=short)
        res["remove_reverse"] = self.remove_reverse

        return res

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """Public available method to initiate the argument parser."""
        app_group = self.arg_parser.add_argument_group(_("Options of {}").format(self.appname))

        app_group.add_argument(
            "-N",
            "--no-reverse",
            action="store_true",
            dest="no_reverse",
            help=_(
                "Don't remove reverse DNS entries (PTR records) to the given addresses. "
                "(Default: False - reverse entries will be removed)."
            ),
        )

        app_group.add_argument(
            "addresses",
            metavar=_("ADDRESS|@FILE"),
            type=str,
            nargs="+",
            help=_(
                "Addresses to remove or a file (given as @filename), containing the addresses "
                "to remove. If a file was given, then the addresses in ther  must be separated "
                "with whitespaces and/or newlines. Lines ay be commented out by prepending them "
                "with a hash sign '#'."
            )
        )

        super(PdnsRemoveAddrApp, self).init_arg_parser()

    # -------------------------------------------------------------------------
    def post_init(self):
        """Execute this method before calling run()."""
        self.initialized = False

        super(PdnsRemoveAddrApp, self).post_init()

        if self.address_files:
            self.read_address_files()

        if not self.addresses:
            LOG.error(_("No addresses to remove given."))
            self.exit(1)

        self.addresses.sort()

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):
        """Parse the command line options."""
        super(PdnsRemoveAddrApp, self).perform_arg_parser()

        if self.args.no_reverse:
            self.remove_reverse = False

        if self.args.addresses:
            for address_token in self.args.addresses:
                self._perform_address_token(address_token)

    # -------------------------------------------------------------------------
    def _perform_address_token(self, address_token):

        if address_token.startswith("@"):
            afile = Path(address_token.replace("@", "", 1))
            if not afile.exists():
                LOG.error(_("File {f} does not exists.").format(
                    self.colored(str(afile), ["cyan", "bold"])))
                self.exit(1)
            if not afile.is_file():
                LOG.error(_("File {f} is not a regular file.").format(
                    self.colored(str(afile), ["cyan", "bold"])))
                self.exit(1)
            if not os.access(str(afile), os.R_OK):
                LOG.error(_("No read access to file {!r}.").format(
                    self.colored(str(afile), ["cyan", "bold"])))
                self.exit(1)
            afile = afile.resolve()
            if afile not in self.address_files:
                self.address_files.append(afile)
            return

        addr = address_token.strip().lower()
        if addr != "" and addr not in self.addresses:
            self.addresses.append(addr)

    # -------------------------------------------------------------------------
    def read_address_file(self, afile):
        """Read the file containing all addresses to remove."""
        if self.verbose > 1:
            LOG.debug(_("Reading address file {} ...").format(
                self.colored(str(afile), ["cyan", "bold"])))
        content = afile.read_text(encoding=self.encoding, errors="surrogateescape")
        if self.verbose > 2:
            LOG.debug(_("Content of {!r}:").format(str(afile)) + "\n" + content)

        addresses = []
        for line in content.splitlines():
            line_stripped = self.re_comment.sub("", line).strip()
            if line_stripped == "":
                continue
            for token in self.re_whitespace.split(line_stripped):
                addr = token.strip().lower()
                if addr != "" and addr not in addresses:
                    addresses.append(addr)

        if addresses:
            self.addresses = addresses

        if not self.addresses:
            LOG.error(_("No addresses to remove found in {!r}.").format(str(afile)))
            # self.exit(1)

    # -------------------------------------------------------------------------
    def read_address_files(self):
        """Read all files containing addresses to remove."""
        for afile in self.address_files:
            self.read_address_file(afile)

    # -------------------------------------------------------------------------
    def _run(self):

        print()
        LOG.debug("Starting {a!r}, version {v!r} ...".format(a=self.appname, v=self.version))

        ret = 0
        try:
            self.zones = self.pdns_api.get_api_zones()
            ret = self.verify_addresses(copy.copy(self.addresses))

        finally:
            # Cleaning up ...
            self.pdns_api = None

        self.exit_value = ret

    # -------------------------------------------------------------------------
    def verify_addresses(self, addresses):
        """Verify all given DNS addresses."""
        LOG.debug(_("Verifying all given DNS addresses."))

        fqdns_found = []

        all_fqdns = self._canon_addresses(addresses)
        zones_of_records = self._get_zones_of_addresses(all_fqdns)

        if not zones_of_records:
            msg = _("Did not found any addresses with an appropriate zone in PowerDNS.")
            LOG.error(msg)
            return 1

        if self.verbose > 1:
            LOG.debug(_("Found zones for addresses:") + "\n" + pp(zones_of_records))

        for zone_name in zones_of_records:
            fqdns_found = self._verify_fqdns_in_pdns_zones(
                zone_name, zones_of_records, fqdns_found
            )
        if self.verbose > 2:
            LOG.debug(_("The following FQDNs were found:") + "\n" + pp(fqdns_found))

        fqdns_not_found = []
        for fqdn in all_fqdns:
            if fqdn not in fqdns_found:
                fqdns_not_found.append(fqdn)
        if fqdns_not_found:
            msg = _("The following addresses (FQDNs) are not found:")
            for fqdn in fqdns_not_found:
                msg += "\n  * {!r}".format(fqdn)
            LOG.warning(msg)

        if not self.records2remove:
            return 1

        if self.verbose > 2:
            msg = _("Found resource record sets to remove:")
            msg += "\n" + pp(self.records2remove)
            LOG.debug(msg)

        return 0

    # -------------------------------------------------------------------------
    def _canon_addresses(self, addresses):

        if self.verbose > 1:
            LOG.debug(_("Canonizing all given addresses."))
        all_fqdns = []

        for addr in addresses:

            fqdn = self.pdns_api.name2fqdn(addr)
            if not fqdn:
                LOG.warning(_("Address {!r} could not interpreted as a FQDN.").format(addr))
                continue
            if fqdn not in all_fqdns:
                all_fqdns.append(fqdn)

        if self.verbose > 2:
            LOG.debug(_("Canonized addresses:") + "\n" + pp(all_fqdns))
        return all_fqdns

    # -------------------------------------------------------------------------
    def _get_zones_of_addresses(self, fqdns):

        if self.verbose > 1:
            LOG.debug(_("Retrieve zones for canonized addresses."))
        zones_of_records = {}

        for fqdn in fqdns:

            zones = self.pdns_api.get_all_zones_for_item(fqdn)
            if not zones:
                LOG.warning(_("Did not found an appropriate zone for address {!r}.").format(fqdn))
                continue

            for zone_name in zones:
                if zone_name not in zones_of_records:
                    zones_of_records[zone_name] = {}
                zones_of_records[zone_name][fqdn] = {}

        if self.verbose > 2:
            LOG.debug(_("Zones of addresses:") + "\n" + pp(zones_of_records))
        return zones_of_records

    # -------------------------------------------------------------------------
    def _verify_fqdns_in_pdns_zones(self, zone_name, zones_of_records, fqdns_found=None):

        if self.verbose > 1:
            LOG.debug(_("Verifying FQDNs for zone {!r}.").format(zone_name))

        if fqdns_found is None:
            fqdns_found = []

        zone = self.pdns_api.zones[zone_name]
        zone.update()
        if self.verbose > 1:
            LOG.debug(
                _("Found {c} resource record sets (RRSET) for zone {z!r}.").format(
                    c=len(zone.rrsets), z=zone_name
                )
            )

        for fqdn in zones_of_records[zone_name]:
            fqdns_in_zone_found = self._verify_fqdn_in_pdns_zone(zone_name, fqdn)
            if fqdns_in_zone_found:
                fqdns_found += fqdns_in_zone_found

        return fqdns_found

    # -------------------------------------------------------------------------
    def _verify_fqdn_in_pdns_zone(self, zone_name, fqdn):

        zone = self.pdns_api.zones[zone_name]
        fqdns_in_zone_found = []

        fqdn_puny = to_str(fqdn.encode("idna"))
        if self.verbose > 1:
            if fqdn != fqdn_puny:
                LOG.debug(
                    _("Searching {f!r} ({p!r}) in zone {z!r} ...").format(
                        f=fqdn, p=fqdn_puny, z=zone_name
                    )
                )
            else:
                LOG.debug(_("Searching {f!r} in zone {z!r} ...").format(f=fqdn, z=zone_name))

        for rrset in zone.rrsets:

            if rrset.name != fqdn:
                if fqdn == fqdn_puny:
                    continue
                if rrset.name != fqdn_puny:
                    continue

            rrset2remove = {"fqdn": fqdn_puny, "type": rrset.type.upper(), "records": []}
            found = False
            if zone.reverse_zone:
                if rrset.type.upper() == "PTR":
                    found = True
            else:
                if rrset.type.upper() in ("A", "AAAA", "CNAME"):
                    found = True
            if not found:
                continue

            for record in rrset.records:
                if zone.reverse_zone and rrset.type.upper() == "PTR":
                    if self.expected_ptr is not None and fqdn_puny in self.expected_ptr:
                        ptr = self.pdns_api.decanon_name(fqdn_puny)
                        exp = self.pdns_api.decanon_name(self.expected_ptr[fqdn_puny])
                        addr = self.pdns_api.decanon_name(record.content)
                        if self.verbose > 1:
                            LOG.debug(_("Expexted PTR: {p!r} => {a!r}.").format(p=ptr, a=exp))
                        if record.content != self.expected_ptr[fqdn_puny]:
                            LOG.warning(
                                _(
                                    "PTR {p!r} does not pointing to expected {e!r}, "
                                    "but to {c!r} instead, ignoring for deletion."
                                ).format(p=ptr, e=exp, c=addr)
                            )
                            continue
                record2remove = {"content": record.content, "disabled": record.disabled}
                rrset2remove["records"].append(record2remove)
            if zone_name not in self.records2remove:
                self.records2remove[zone_name] = []
            self.records2remove[zone_name].append(rrset2remove)
            if fqdn_puny not in fqdns_in_zone_found:
                fqdns_in_zone_found.append(fqdn_puny)

        return fqdns_in_zone_found

# =============================================================================
def main():
    """Entrypoint for pdns-remove-addresses."""
    my_path = Path(sys.argv[0])
    appname = my_path.name

    locale.setlocale(locale.LC_ALL, "")

    app = PdnsRemoveAddrApp(appname=appname)
    app.initialized = True

    if app.verbose > 2:
        print(_("{c}-Object:\n{a}").format(c=app.__class__.__name__, a=app), file=sys.stderr)

    app()

    sys.exit(0)


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
