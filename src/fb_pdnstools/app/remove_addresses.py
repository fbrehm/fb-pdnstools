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
# import ipaddress
import locale
import logging
import os
import re
import sys
# from functools import cmp_to_key
from pathlib import Path

# Third party modules

# Own modules
from . import BasePowerDNSApplication
# from . import PdnsAppError
from .. import __version__ as GLOBAL_VERSION
from ..descriptors import BooleanDescriptor
from ..xlate import XLATOR

__version__ = "0.2.0"
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
            LOG.debug(_("Content of {!r}:").format(str(self.address_file)) + "\n" + content)

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
