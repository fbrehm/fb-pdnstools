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
import locale
import logging
import os
import re
import sys
from functools import cmp_to_key
from pathlib import Path

# Third party modules
from fb_tools.common import compare_fqdn
from fb_tools.common import pp
from fb_tools.common import to_str

from rich import box
from rich.table import Table

# Own modules
from . import BasePowerDNSApplication
from .. import __version__ as GLOBAL_VERSION
from ..api.recordset import PowerDNSRecordSetList
from ..descriptors import BooleanDescriptor
from ..xlate import XLATOR

__version__ = "0.8.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PdnsRemoveAddrApp(BasePowerDNSApplication):
    """Class for the application object of the pdns-remove-addresses application."""

    show_simulate_option = True
    show_assume_options = True

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
                "to remove. If a file was given, then the addresses in there must be separated "
                "with whitespaces and/or newlines. Lines may be commented out by prepending them "
                "with a hash sign '#'."
            ),
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
                LOG.error(
                    _("File {f} does not exists.").format(
                        self.colored(str(afile), ["cyan", "bold"])
                    )
                )
                self.exit(1)
            if not afile.is_file():
                LOG.error(
                    _("File {f} is not a regular file.").format(
                        self.colored(str(afile), ["cyan", "bold"])
                    )
                )
                self.exit(1)
            if not os.access(str(afile), os.R_OK):
                LOG.error(
                    _("No read access to file {!r}.").format(
                        self.colored(str(afile), ["cyan", "bold"])
                    )
                )
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
            LOG.debug(
                _("Reading address file {} ...").format(self.colored(str(afile), ["cyan", "bold"]))
            )
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
            for addr in addresses:
                if addr not in self.addresses:
                    self.addresses.append(addr)

        if not addresses:
            LOG.warn(_("No addresses to remove found in {!r}.").format(str(afile)))

    # -------------------------------------------------------------------------
    def read_address_files(self):
        """Read all files containing addresses to remove."""
        for afile in self.address_files:
            self.read_address_file(afile)

    # -------------------------------------------------------------------------
    def _run(self):

        if self.verbose:
            LOG.debug("Starting {a!r}, version {v!r} ...".format(a=self.appname, v=self.version))

        ret = 0
        try:
            self.zones = self.pdns_api.get_api_zones()
            ret = self.verify_addresses(copy.copy(self.addresses))

            prompt = (
                _("Confirm deletion of DNS records [{yes}/{no}]").format(
                    yes=self.colored(_("Yes"), ["bold", "red"]),
                    no=self.colored(_("no"), ["bold", "green"]),
                )
                + ": "
            )

            if ret == 0:
                self.print_records_remove()
                if not self.ask_for_yes_or_no(prompt, True):
                    self.exit(1)
                self.countdown()
                self.do_remove()

        finally:
            # Cleaning up ...
            self.pdns_api = None

        self.exit_value = ret

    # -------------------------------------------------------------------------
    def do_remove(self):
        """Remove finally all addresses in DNS."""
        for zone_name in sorted(
            self.records2remove.keys(), key=lambda x: cmp_to_key(compare_fqdn)(x)
        ):
            print()
            zone = self.pdns_api.zones[zone_name]
            rrsets_rm = []
            for fqdn in self.records2remove[zone_name]:
                for rrset in self.records2remove[zone_name][fqdn]:
                    zone.add_rrset_for_remove(fqdn, rrset.type, rrsets_rm)

            if self.verbose > 3:
                LOG.debug("Struct rrsets_rm:\n" + pp(rrsets_rm))
            zone.del_rrsets(rrsets_rm)

            zone.notify()

        print()

    # -------------------------------------------------------------------------
    def _mangle_zones_of_records(self, zones_of_records, zone_name):

        for fqdn in zones_of_records[zone_name].keys():
            zone = self.pdns_api.zones[zone_name]
            if zone_name.endswith(".arpa."):
                rrset = zone.get_ptr_rrset(fqdn, raise_on_error=False)
                if rrset:
                    rrsets = [rrset]
                else:
                    rrsets = []
            else:
                rrsets = zone.get_address_rrsets(fqdn, raise_on_error=False)

            if rrsets:
                zones_of_records[zone_name][fqdn] = rrsets

    # -------------------------------------------------------------------------
    def verify_addresses(self, addresses):
        """Verify all given DNS addresses."""
        LOG.debug(_("Verifying all given DNS addresses."))

        self.fqdn2addr = {}
        fqdns_not_found = {}

        all_fqdns = self._canon_addresses(addresses)
        zones_of_records = self._get_zones_of_addresses(all_fqdns, fqdns_not_found)

        if not zones_of_records:
            print()
            msg = _("Did not found any addresses with an appropriate zone in PowerDNS.")
            LOG.error(msg)
            return 1

        if self.verbose > 1:
            LOG.debug(_("Found zones for addresses:") + "\n" + pp(zones_of_records))

        for zone_name in zones_of_records.keys():
            self._mangle_zones_of_records(zones_of_records, zone_name)

        fqdns_found = []

        # if self.verbose:
        #     print()
        #     z = {}
        #     for zone_name in zones_of_records.keys():
        #         z[zone_name] = {}
        #         for fqdn in zones_of_records[zone_name].keys():
        #             rrsets = zones_of_records[zone_name][fqdn]
        #             if isinstance(rrsets, PowerDNSRecordSetList):
        #                 rrsets = rrsets.as_list()
        #             z[zone_name][fqdn] = rrsets
        #     LOG.debug("zones_of_records:\n" + pp(z))
        #     print()

        for zone_name in zones_of_records.keys():
            for fqdn in zones_of_records[zone_name].keys():
                if zones_of_records[zone_name][fqdn]:
                    rrsets = zones_of_records[zone_name][fqdn]
                    if isinstance(rrsets, PowerDNSRecordSetList):
                        rrsets = rrsets.as_list()
                    if zone_name not in self.records2remove:
                        self.records2remove[zone_name] = {}
                    self.records2remove[zone_name][fqdn] = rrsets
                    if fqdn not in fqdns_found:
                        fqdns_found.append(fqdn)
                else:
                    fqdns_not_found[fqdn] = self.fqdn2addr[fqdn]

        if self.remove_reverse:
            self.get_reverse_pointers(fqdns_not_found)

        fqdns_found.sort()

        if self.verbose > 2:
            LOG.debug(_("The following FQDNs were found:") + "\n" + pp(fqdns_found))

        if fqdns_not_found:
            msg = _("The following addresses (FQDNs) are not found:")
            for fqdn in fqdns_not_found:
                msg += "\n  * {!r}".format(fqdn)
                if fqdn in self.fqdn2addr:
                    msg += " ({!r})".format(self.fqdn2addr[fqdn])
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

            fqdn_puny = to_str(fqdn.encode("idna"))
            if fqdn_puny not in all_fqdns:
                all_fqdns.append(fqdn_puny)
            self.fqdn2addr[fqdn_puny] = addr

        if self.verbose > 2:
            LOG.debug(_("Canonized addresses:") + "\n" + pp(all_fqdns))
        return all_fqdns

    # -------------------------------------------------------------------------
    def _get_zones_of_addresses(self, fqdns, fqdns_not_found):

        if self.verbose > 1:
            LOG.debug(_("Retrieve zones for canonized addresses."))
        zones_of_records = {}

        for fqdn in fqdns:

            zones = self.pdns_api.get_all_zones_for_item(fqdn)
            if not zones:
                LOG.warning(_("Did not found an appropriate zone for address {!r}.").format(fqdn))
                fqdns_not_found[fqdn] = self.fqdn2addr[fqdn]
                continue

            for zone_name in zones:
                if zone_name not in zones_of_records:
                    zones_of_records[zone_name] = {}
                zones_of_records[zone_name][fqdn] = {}

        if self.verbose > 2:
            LOG.debug(_("Zones of addresses:") + "\n" + pp(zones_of_records))
        return zones_of_records

    # -------------------------------------------------------------------------
    def get_reverse_pointers(self, fqdns_not_found):
        """Collect reverse pointers of A- and AAAA-records, which should be removed."""
        if self.verbose > 1:
            LOG.debug(
                _(
                    "Trying to get all reverse pointers of A- and AAAA-records, "
                    "which should be removed."
                )
            )

        addresses = {}

        for zone_name in self.records2remove:
            for fqdn in self.records2remove[zone_name]:
                for rrset in self.records2remove[zone_name][fqdn]:
                    if rrset.type in ("A", "AAAA"):
                        for record in rrset.records:
                            address = record.content
                            fqdn = self.pdns_api.name2fqdn(address)
                            addresses[address] = fqdn
                            self.fqdn2addr[fqdn] = address

        if self.verbose > 1:
            LOG.debug(_("Got reverse addresses to remove:") + "\n" + pp(addresses))

        zones_of_records = self._get_zones_of_addresses(addresses.values(), fqdns_not_found)

        if not zones_of_records:
            return

        for zone_name in zones_of_records.keys():
            for fqdn in zones_of_records[zone_name].keys():
                zone = self.pdns_api.zones[zone_name]
                zones_of_records[zone_name][fqdn] = []
                if zone_name.endswith(".arpa."):
                    rrset = zone.get_ptr_rrset(fqdn, raise_on_error=False)
                    if rrset:
                        rrsets = [rrset]
                    else:
                        rrsets = []
                    zones_of_records[zone_name][fqdn] = rrsets

        for zone_name in zones_of_records.keys():
            for fqdn in zones_of_records[zone_name].keys():
                if zones_of_records[zone_name][fqdn]:
                    rrsets = zones_of_records[zone_name][fqdn]
                    if isinstance(rrsets, PowerDNSRecordSetList):
                        rrsets = rrsets.as_list()
                    if zone_name not in self.records2remove:
                        self.records2remove[zone_name] = {}
                    self.records2remove[zone_name][fqdn] = rrsets
                    if fqdn in fqdns_not_found:
                        del fqdns_not_found[fqdn]
                else:
                    fqdns_not_found[fqdn] = self.fqdn2addr[fqdn]

    # -------------------------------------------------------------------------
    def print_records_remove(self):
        """Display all DNS records to remove on screen."""
        table_title = _("All DNS records to remove") + "\n"
        show_header = True
        box_style = box.ROUNDED

        count = 0
        for zone_name in self.records2remove.keys():
            for _rrset in self.records2remove[zone_name]:
                count += 1

        if count:
            caption = "\n" + ngettext(
                "Total one DNS record to remove.", "Total {} DNS records to remove.", count
            ).format(count)
        else:
            caption = "\n" + _("Found no DNS records to remove.")

        if self.quiet:
            show_header = False
            table_title = None
            box_style = None
            caption = None

        table = Table(
            title=table_title,
            title_style="bold cyan",
            caption=caption,
            caption_style="default on default",
            caption_justify="left",
            box=box_style,
            show_header=show_header,
            show_footer=False,
        )

        table.add_column(header=_("Name"))
        table.add_column(header=_("Name Unicode / Address"))
        table.add_column(header=_("Zone"))
        table.add_column(header=_("Type"))
        table.add_column(header=_("Record"))
        table.add_column(header=_("Status"))

        for zone_name in sorted(
            self.records2remove.keys(), key=lambda x: cmp_to_key(compare_fqdn)(x)
        ):
            zone = self.pdns_api.zones[zone_name]
            for fqdn in self.records2remove[zone_name].keys():
                for rrset in self.records2remove[zone_name][fqdn]:
                    # LOG.debug(f"Rrset: {rrset!r}")
                    for record in rrset.records:
                        # LOG.debug(f"Record: {record!r}")
                        row = []
                        row.append(self.pdns_api.decanon_name(fqdn))
                        if zone.reverse_zone:
                            row.append(str(rrset.address))
                        else:
                            row.append(rrset.name_unicode)
                        row.append(self.pdns_api.decanon_name(zone_name))
                        row.append(rrset.type)
                        row.append(self.pdns_api.decanon_name(record.content))
                        if record.disabled:
                            row.append(_("Disabled"))
                        else:
                            row.append(_("Enabled"))

                        table.add_row(*row)

        self.rich_console.print(table)
        if not self.quiet:
            print()


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
