#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: A base module for all PowerDNS application classes.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2022 - 2026 by Frank Brehm, Berlin
"""
from __future__ import absolute_import, print_function

# Standard modules
import copy
import os

# Third party modules
from fb_tools.argparse_actions import RangeOptionAction
from fb_tools.argparse_actions import TimeoutOptionAction
from fb_tools.cfg_app import FbConfigApplication
from fb_tools.common import pp
from fb_tools.errors import FbAppError
from fb_tools.multi_config import DEFAULT_ENCODING

from rich import box
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

# Own modules
from .. import __version__ as GLOBAL_VERSION
from .. import DEFAULT_API_PREFIX
from .. import DEFAULT_PORT
from .. import DEFAULT_TIMEOUT
from .. import DEFAULT_USE_HTTPS
from .. import MAX_API_TIMEOUT
from .. import MAX_PORT_NUMBER
from .. import PowerDNSServer
from ..config import PdnsApiConfig
from ..config import PdnsApiConfigInfo
from ..errors import PowerDNSHandlerError
from ..xlate import DOMAIN
from ..xlate import LOCALE_DIR
from ..xlate import XLATOR
from ..xlate import __base_dir__ as __xlate_base_dir__
from ..xlate import __lib_dir__ as __xlate_lib_dir__
from ..xlate import __mo_file__ as __xlate_mo_file__
from ..xlate import __module_dir__ as __xlate_module_dir__

__version__ = "0.1.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

# =============================================================================
class PdnsAppError(FbAppError, PowerDNSHandlerError):
    """Base exception class for all exceptions in all PowerDNS application classes."""

    pass

# =============================================================================
class BasePowerDNSApplication(FbConfigApplication):
    """Base class for all PowerDNS application classes."""

    term_colors = {
        "kitty": "256",
        "256color": "256",
        "16color": "standard",
    }

    # -------------------------------------------------------------------------
    def __init__(self, version=GLOBAL_VERSION, cfg_class=PdnsApiConfig, **kwargs):
        """Initialize a BasePowerDNSApplication object."""
        self.rich_console = None
        self.pdns_api = None
        self.pdns_api_info = None

        super(BasePowerDNSApplication, self).__init__(
            version=version,
            cfg_class=cfg_class,
            **kwargs
        )

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(BasePowerDNSApplication, self).as_dict(short=short)

        res["xlate"]["fb_pdnstools"] = {
            "__module_dir__": __xlate_module_dir__,
            "__lib_dir__": __xlate_lib_dir__,
            "__base_dir__": __xlate_base_dir__,
            "LOCALE_DIR": LOCALE_DIR,
            "DOMAIN": DOMAIN,
            "__mo_file__": __xlate_mo_file__,
        }

        return res

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """Public available method to initiate the argument parser."""
        pdns_group = self.arg_parser.add_argument_group(_("PowerDNS options"))

        pdns_group.add_argument(
            "-H",
            "--host",
            dest="host",
            metavar=_("HOST"),
            help=_("Address or hostname of the PowerDNS server providing the API.")
        )

        pdns_group.add_argument(
            "-P",
            "--port",
            dest="port",
            type=int,
            metavar=_("PORT"),
            action=RangeOptionAction,
            min_val=1,
            max_val=MAX_PORT_NUMBER,
            help=_("Port on PowerDNS server for API on (Default: {}).").format(DEFAULT_PORT),
        )

        pdns_group.add_argument(
            "-K",
            "--key",
            "--api-key",
            metavar="KEY",
            dest="api_key",
            help=_("The API key for accessing the PowerDNS API."),
        )

        https_group = pdns_group.add_mutually_exclusive_group()
        if DEFAULT_USE_HTTPS:
            default_https_on = _("on")
            default_https_off = _("off")
        else:
            default_https_on = _("off")
            default_https_off = _("on")
        https_group.add_argument(
            "--https",
            action="store_true",
            dest="https",
            help=_("Use HTTPS to access the PowerDNS API (Default: {}).").format(default_https_on),
        )
        https_group.add_argument(
            "--no-https",
            action="store_false",
            dest="https",
            help=_("Use No HTTPS to access the PowerDNS API (Default: {}).").format(
                default_https_off
            ),
        )

        pdns_group.add_argument(
            "--prefix",
            dest="api_path_prefix",
            help=_(
                "The global prefix for all paths for accessing the PowerDNS API "
                "(Default: {!r})."
            ).format(DEFAULT_API_PREFIX),
        )

        pdns_group.add_argument(
            "--timeout",
            metavar=_("SECONDS"),
            dest="api_timeout",
            type=int,
            action=TimeoutOptionAction,
            max_timeout=MAX_API_TIMEOUT,
            help=_("The timeout in seconds for PowerDNS API requests. Default: {}").format(
                DEFAULT_TIMEOUT,
            ),
        )

        super(BasePowerDNSApplication, self).init_arg_parser()

    # -------------------------------------------------------------------------
    def post_init(self):
        """Execute this method before calling run()."""
        self.initialized = False

        super(BasePowerDNSApplication, self).post_init()

        self.pdns_api_info = copy.copy(self.cfg.pdns_api)
        self.perform_arg_parser_pdns()

        self.pdns_api = PowerDNSServer(
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            master_server=self.pdns_api_info.host,
            port=self.pdns_api_info.port,
            key=self.pdns_api_info.key,
            use_https=self.pdns_api_info.use_https,
            path_prefix=self.pdns_api_info.prefix,
            timeout=self.pdns_api_info.timeout,
            simulate=self.simulate,
            force=self.force,
            initialized=True,
        )

        args_color = getattr(self.args, "color", "auto")
        if args_color == "auto":
            self.rich_console = Console()
        else:
            color_system = None
            if args_color == "yes":
                color_term = os.environ.get("COLORTERM", "").strip().lower()
                if color_term in ("truecolor", "24bit"):
                    color_system = "truecolor"
                else:
                    color_system = "standard"
                    term = os.environ.get("TERM", "").strip().lower()
                    _term_name, _hyphen, colors = term.rpartition("-")
                    color_system = self.term_colors.get(colors, "standard")

            self.rich_console = Console(color_system=color_system)

    # -------------------------------------------------------------------------
    def perform_arg_parser_pdns(self):
        """Execute some actions after parsing the command line parameters."""
        host = getattr(self.args, "host", None)
        if host:
            self.pdns_api_info.host = self.args.host

        port = getattr(self.args, "port", None)
        if port:
            self.pdns_api_info.port = self.args.port

        use_https = getattr(self.args, "https", None)
        if use_https is not None:
            self.pdns_api_info.use_https = use_https

        key = getattr(self.args, "api_key", None)
        if key:
            self.pdns_api_info.key = key

        prefix = getattr(self.args, "api_path_prefix", None)
        if prefix:
            self.pdns_api_info.prefix = prefix

        timeout = getattr(self.args, "api_timeout", None)
        if timeout:
            self.pdns_api_info.timeout = timeout

    # -------------------------------------------------------------------------
    def pre_run(self):
        """Execute some actions before the main routine."""
        LOG.debug(_("Actions before running main routine."))

        if self.simulate:
            message = _("Simulation mode - nothing will be done in real.")
            if self.quiet:
                box_style = None
            sim_panel = Panel(
                message,
                box=box.ROUNDED,
                style="bold cyan",
                border_style="bold yellow",
            )
            self.rich_console.print(sim_panel)


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
