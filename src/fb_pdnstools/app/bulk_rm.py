#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for the 'pdns-bulk-remove' application object.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 by Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import copy
import ipaddress
import locale
import logging
import os
import pathlib
import re
import sys
from functools import cmp_to_key

# Third party modules
from fb_tools.argparse_actions import CfgFileOptionAction

# Own modules
from . import BasePowerDNSApplication
from . import PdnsAppError
from .. import __version__ as GLOBAL_VERSION
from ..descriptors import BooleanDescriptor
from ..xlate import XLATOR

__version__ = "0.1.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

# =============================================================================
class PdnsBulkRmApp(BasePowerDNSApplication):
    """Class for the application object of the pdns-bulk-remove application."""

    show_simulate_option = True

    remove_reverse = BooleanDescriptor(name="remove_reverse")

    # -------------------------------------------------------------------------
    def __init__(self, version=GLOBAL_VERSION, *args, **kwargs):
        """Initialize the PdnsBulkRmApp object."""
        desc = _(
            "Removes the given addresses (A-, AAAA- or CNAME-Records) completety from "
            "PowerDNS. If there are multiple entries to a DNS-Name, all appropriate "
            "records are removed. Additionally all appropriate reverse entries (PTR-records) "
            "were also removed, if they are pointing back to the given A- or AAAA-record."
        )

        self.remove_reverse = True

        self.address_file = None

        self.addresses = []
        self.records2remove = {}
        self.expected_ptr = None

        super(PdnsBulkRmApp, self).__init__(
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
        res = super(PdnsBulkRmApp, self).as_dict(short=short)
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

        # file_group = app_group.add_mutually_exclusive_group()

        app_group.add_argument(
            "-F",
            "--file",
            metavar=_("FILE"),
            dest="addr_file",
            type=pathlib.Path,
            action=CfgFileOptionAction,
            help=_(
                "File containing the addresses to remove. The addresses must be "
                "whitespace separeted, lines may be commented out by prepending them "
                "with a hash sign '#'. This option is mutually exclusive with "
                "giving the addresses as command line arguments."
            ),
        )

        app_group.add_argument(
            "addresses",
            metavar=_("ADDRESS"),
            type=str,
            nargs="*",
            help=_(
                "Addresses to remove. This option is mutually exclusive with the {!r} option."
            ).format("-F/--file"),
        )

        super(PdnsBulkRmApp, self).init_arg_parser()

    # -------------------------------------------------------------------------
    def post_init(self):
        """Execute this method before calling run()."""
        self.initialized = False

        super(PdnsBulkRmApp, self).post_init()

        if self.address_file:
            self.read_address_file()

        if not self.addresses:
            LOG.error(_("No addresses to remove given."))
            self.exit(1)

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):
        """Parse the command line options."""
        super(PdnsBulkRmApp, self).perform_arg_parser()

        if self.args.no_reverse:
            self.remove_reverse = False

        if self.args.addr_file:
            afile = self.args.addr_file
            if not os.access(str(afile), os.R_OK):
                msg = _("No read access to file {!r}.").format(str(afile))
                LOG.error(msg)
                self.exit(1)
            self.address_file = afile

        if self.args.addresses:
            for address in self.args.addresses:
                addr = address.strip().lower()
                if addr != "" and addr not in self.addresses:
                    self.addresses.append(addr)

    # -------------------------------------------------------------------------
    def read_address_file(self):
        """Read the file containing all addresses to remove."""
        content = self.read_file(self.address_file)
        if self.verbose > 2:
            LOG.debug(_("Content of {!r}:").format(str(self.address_file)) + "\n" + content)

        re_comment = re.compile(r"\s*#.*")
        re_whitespace = re.compile(r"\s+")

        addresses = []
        for line in content.splitlines():
            line_stripped = re_comment.sub("", line).strip()
            if line_stripped == "":
                continue
            for token in re_whitespace.split(line_stripped):
                addr = token.strip().lower()
                if addr != "" and addr not in addresses:
                    addresses.append(addr)

        if addresses:
            self.addresses = addresses

        if not self.addresses:
            LOG.error(_("No addresses to remove found in {!r}.").format(str(self.address_file)))
            self.exit(1)

    # -------------------------------------------------------------------------
    def _run(self):

        print()
        LOG.debug("Starting {a!r}, version {v!r} ...".format(a=self.appname, v=self.version))


# =============================================================================
def main():
    """Entrypoint for pdns-bulk-remove."""
    my_path = pathlib.Path(sys.argv[0])
    appname = my_path.name

    locale.setlocale(locale.LC_ALL, "")

    app = PdnsBulkRmApp(appname=appname)
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
