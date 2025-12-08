#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for a base PowerDNS handler object.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2024 Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import copy
import ipaddress
import json
import logging
import os
import re
import socket
from abc import ABCMeta

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

# Third party modules
from fb_tools.common import RE_DOT_AT_END
from fb_tools.common import pp
from fb_tools.common import reverse_pointer
from fb_tools.common import to_bool
from fb_tools.common import to_str
from fb_tools.handling_obj import HandlingObject

import requests
from requests.exceptions import RequestException

import six
from six import add_metaclass

import urllib3

# Own modules
from . import DEFAULT_API_PREFIX
from . import DEFAULT_PORT
from . import DEFAULT_TIMEOUT
from . import DEFAULT_USE_HTTPS
from . import LIBRARY_NAME
from . import MAX_PORT_NUMBER
from . import VALID_RRSET_TYPES
from .errors import PDNSApiError
from .errors import PDNSApiNotAuthorizedError
from .errors import PDNSApiNotFoundError
from .errors import PDNSApiRateLimitExceededError
from .errors import PDNSApiValidationError
from .errors import PDNSRequestError
from .errors import PowerDNSHandlerError
from .xlate import XLATOR


__version__ = "1.0.0"
LOG = logging.getLogger(__name__)

LOGLEVEL_REQUESTS_SET = False

_ = XLATOR.gettext


# =============================================================================
@add_metaclass(ABCMeta)
class BasePowerDNSHandler(HandlingObject):
    """
    Base class for a PowerDNS handler object.

    Must not be instantiated directly.
    """

    show_simulate_option = True

    default_port = DEFAULT_PORT
    default_timeout = DEFAULT_TIMEOUT
    default_api_servername = "localhost"

    loglevel_requests_set = False

    re_request_id = re.compile(r"/requests/([-a-f0-9]+)/", re.IGNORECASE)

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        master_server=None,
        port=DEFAULT_PORT,
        key=None,
        use_https=DEFAULT_USE_HTTPS,
        timeout=None,
        path_prefix=DEFAULT_API_PREFIX,
        *args,
        **kwargs,
    ):
        """Initialize a BasePowerDNSHandler object."""
        self._master_server = master_server
        self._port = self.default_port
        self._key = key
        self._use_https = False
        self._path_prefix = path_prefix
        self._timeout = self.default_timeout
        self._user_agent = "{}/{}".format(LIBRARY_NAME, __version__)
        self._api_servername = self.default_api_servername
        self._mocked = False
        self.mocking_paths = []

        super(BasePowerDNSHandler, self).__init__(*args, **kwargs, version=version)

        self.use_https = use_https
        self.port = port
        self.timeout = timeout

        global LOGLEVEL_REQUESTS_SET

        if not LOGLEVEL_REQUESTS_SET:
            msg = _("Setting loglevel of the {m} module to {ll}.").format(
                m="requests", ll="WARNING"
            )
            LOG.debug(msg)
            logging.getLogger("requests").setLevel(logging.WARNING)
            LOGLEVEL_REQUESTS_SET = True

        if "initialized" in kwargs:
            self.initialized = kwargs["initialized"]

    # -----------------------------------------------------------
    @property
    def master_server(self):
        """Return the hostname or address of the PowerDNS master server."""
        return self._master_server

    @master_server.setter
    def master_server(self, value):
        if value is None:
            self._master_server = None
            return

        val = str(value).strip().lower()
        if val == "":
            self._master_server = None
        else:
            self._master_server = val

    # -----------------------------------------------------------
    @property
    def port(self):
        """Return the TCP port number of the PowerDNS API."""
        return self._port

    @port.setter
    def port(self, value):
        if value is None:
            self._port = self.default_port
            return
        val = int(value)
        err_msg = _(
            "Invalid port number {port!r} for the PowerDNS API, must be greater than zero "
            "and less than {max}."
        ).format(port=value, max=(MAX_PORT_NUMBER + 1))
        if val <= 0 or val >= MAX_PORT_NUMBER:
            raise ValueError(err_msg)
        self._port = val

    # -----------------------------------------------------------
    @property
    def key(self):
        """Return the key used to authenticate against the PowerDNS API."""
        return self._key

    @key.setter
    def key(self, value):
        if value is None:
            self._key = None
            return

        val = str(value)
        if val == "":
            self._key = None
        else:
            self._key = val

    # -----------------------------------------------------------
    @property
    def use_https(self):
        """Return, whether to use HTTPS to communicate with the API."""
        if self.mocked:
            return False
        return self._use_https

    @use_https.setter
    def use_https(self, value):
        self._use_https = to_bool(value)

    # -----------------------------------------------------------
    @property
    def mocked(self):
        """Flag, that a mocked URI should be used."""
        return self._mocked

    @mocked.setter
    def mocked(self, value):
        self._mocked = to_bool(value)

    # -----------------------------------------------------------
    @property
    def path_prefix(self):
        """Return the hostname or address of the PowerDNS master server."""
        return self._path_prefix

    @path_prefix.setter
    def path_prefix(self, value):
        if value is None:
            self._path_prefix = None
            return

        val = str(value).strip()
        if val == "":
            self._path_prefix = None
        else:
            if not os.path.isabs(val):
                msg = _("The path prefix {!r} must be an absolute path.").format(value)
                raise ValueError(msg)
            self._path_prefix = val

    # -----------------------------------------------------------
    @property
    def timeout(self):
        """Return the timeout in seconds for requesting the PowerDNS API."""
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        if value is None:
            self._timeout = self.default_timeout
            return
        val = int(value)
        err_msg = _(
            "Invalid timeout {!r} for requesting the PowerDNS API, must be greater than zero and "
            "less or equal to  3600."
        )
        if val <= 0 or val > 3600:
            msg = err_msg.format(value)
            raise ValueError(msg)
        self._timeout = val

    # -----------------------------------------------------------
    @property
    def user_agent(self):
        """Return the name of the user agent used in API calls."""
        return self._user_agent

    @user_agent.setter
    def user_agent(self, value):
        if value is None or str(value).strip() == "":
            raise PowerDNSHandlerError(_("Invalid user agent {!r} given.").format(value))
        self._user_agent = str(value).strip()

    # -----------------------------------------------------------
    @property
    def api_servername(self):
        """Return the (virtual) name of the PowerDNS server used in API calls."""
        return self._api_servername

    @api_servername.setter
    def api_servername(self, value):
        if value is None or str(value).strip() == "":
            raise PowerDNSHandlerError(_("Invalid API server name {!r} given.").format(value))
        self._api_servername = str(value).strip()

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(BasePowerDNSHandler, self).as_dict(short=short)
        res["default_port"] = self.default_port
        res["default_timeout"] = self.default_timeout
        res["default_api_servername"] = self.default_api_servername
        res["master_server"] = self.master_server
        res["port"] = self.port
        res["mocked"] = self.mocked
        res["use_https"] = self.use_https
        res["path_prefix"] = self.path_prefix
        res["timeout"] = self.timeout
        res["user_agent"] = self.user_agent
        res["api_servername"] = self.api_servername
        res["key"] = None
        if self.key:
            if self.verbose > 4:
                res["key"] = self.key
            else:
                res["key"] = "*******"

        return res

    # -------------------------------------------------------------------------
    @classmethod
    def _request_id(cls, headers):

        if "location" not in headers:
            return None

        loc = headers["location"]
        match = cls.re_request_id.search(loc)
        if match:
            return match.group(1)
        else:
            msg = _("Failed to extract request ID from response header 'location': {!r}").format(
                loc
            )
            raise PowerDNSHandlerError(msg)

    # -------------------------------------------------------------------------
    def _build_url(self, path, no_prefix=False):

        if not os.path.isabs(path):
            msg = _("The path {!r} must be an absolute path.").format(path)
            raise ValueError(msg)

        url = "http://{}".format(self.master_server)
        if self.mocked:
            url = "mock://{}".format(self.master_server)
        elif self.use_https:
            url = "https://{}".format(self.master_server)
            if self.port != 443:
                url += ":{}".format(self.port)
        else:
            if self.port != 80:
                url += ":{}".format(self.port)

        if self.path_prefix and not no_prefix:
            url += self.path_prefix

        url += path

        if self.verbose > 1:
            LOG.debug(_("Used URL: {!r}").format(url))
        return url

    # -------------------------------------------------------------------------
    def perform_request(  # noqa: C901
        self, path, no_prefix=False, method="GET", data=None, headers=None, may_simulate=False
    ):
        """Perform the underlying API request."""
        if headers is None:
            headers = {}
        if self.key:
            headers["X-API-Key"] = self.key

        url = self._build_url(path, no_prefix=no_prefix)
        if self.verbose > 1:
            LOG.debug(_("Request method: {!r}").format(method))
        if data and self.verbose > 1:
            data_out = "{!r}".format(data)
            try:
                data_out = json.loads(data)
            except ValueError:
                pass
            else:
                data_out = pp(data_out)
            LOG.debug("Data:\n{}".format(data_out))
            if self.verbose > 2:
                LOG.debug("RAW data:\n{}".format(data))

        headers.update({"User-Agent": self.user_agent})
        headers.update({"Content-Type": "application/json"})
        if self.verbose > 1:
            head_out = copy.copy(headers)
            if "X-API-Key" in head_out and self.verbose <= 4:
                head_out["X-API-Key"] = "******"
            LOG.debug("Headers:\n{}".format(pp(head_out)))

        if may_simulate and self.simulate:
            LOG.debug(_("Simulation mode, Request will not be sent."))
            return ""

        try:

            session = requests.Session()
            if self.mocked:
                self.start_mocking(session)
            response = session.request(
                method, url, data=data, headers=headers, timeout=self.timeout
            )

        except RequestException as e:
            raise PDNSRequestError(str(e), url, e.request, e.response)

        except (
            socket.timeout,
            urllib3.exceptions.ConnectTimeoutError,
            urllib3.exceptions.MaxRetryError,
            requests.exceptions.ConnectTimeout,
        ) as e:
            msg = _("Got a {c} on connecting to {h!r}: {e}.").format(
                c=e.__class__.__name__, h=self.master_server, e=e
            )
            raise PowerDNSHandlerError(msg)

        try:
            self._eval_response(url, response)

        except ValueError:
            raise PDNSApiError(_("Failed to parse the response"), response.text)

        if self.verbose > 3:
            LOG.debug("RAW response: {!r}.".format(response.text))
        if not response.text:
            return ""

        json_response = response.json()
        if self.verbose > 3:
            LOG.debug("JSON response:\n{}".format(pp(json_response)))

        if "location" in response.headers:
            json_response["requestId"] = self._request_id(response.headers)

        return json_response

    # -------------------------------------------------------------------------
    def _eval_response(self, url, response):

        if response.ok:
            return

        err = response.json()
        code = response.status_code
        msg = err["error"]
        LOG.debug(_("Got an error response code {code}: {msg}").format(code=code, msg=msg))
        if response.status_code == 401:
            raise PDNSApiNotAuthorizedError(code, msg, url)
        if response.status_code == 404:
            raise PDNSApiNotFoundError(code, msg, url)
        if response.status_code == 422:
            raise PDNSApiValidationError(code, msg, url)
        if response.status_code == 429:
            raise PDNSApiRateLimitExceededError(code, msg, url)
        else:
            raise PDNSApiError(code, msg, url)

    # -------------------------------------------------------------------------
    def canon_name(self, name):
        """Canonize the DNS name, that means ensure a dot at the end of the name."""
        ret = RE_DOT_AT_END.sub(".", name, 1)
        return ret

    # -------------------------------------------------------------------------
    def name2fqdn(self, name, is_fqdn=False):
        """
        Transform the given name into a canonized FQDN.

        If an IP address as name is given (and the parameter 'is_fqdn' is False), then
        this name will be transformed into a reverse pointer address
        (e.g. '4.3.2.1..in-addr.arpa.').
        """
        fqdn = name

        if not is_fqdn:
            try:
                address = ipaddress.ip_address(name)
                fqdn = reverse_pointer(address)
                is_fqdn = False
            except ValueError:
                if self.verbose > 3:
                    LOG.debug(_("Name {!r} is not a valid IP address.").format(name))
                is_fqdn = True
                fqdn = name

        if ":" in fqdn:
            LOG.error(_("Invalid FQDN {!r}.").format(fqdn))
            return None

        return self.canon_name(fqdn)

    # -------------------------------------------------------------------------
    def decanon_name(self, name):
        """Decanonize the FQDN - removing possible dots at the end of the name."""
        ret = RE_DOT_AT_END.sub("", name)
        return ret

    # -------------------------------------------------------------------------
    def verify_rrset_type(self, rtype, raise_on_error=True):
        """Verify, that the given name is a valid RRset type name."""
        if not isinstance(rtype, six.string_types):
            msg = _("A rrset type must be a string type, but is {!r} instead.").format(rtype)
            if raise_on_error:
                raise TypeError(msg)
            LOG.error(msg)
            return None

        type_used = to_str(rtype).strip().upper()
        if not type_used:
            msg = _("Invalid, empty rrset type {!r} given.").format(rtype)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        if type_used not in VALID_RRSET_TYPES:
            msg = _("Invalid rrset type {!r} given.").format(rtype)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        return type_used

    # -------------------------------------------------------------------------
    def start_mocking(self, session):
        """Start mocking mode of this class for unit testing."""
        if not self.mocked:
            return

        LOG.debug(_("Preparing mocking ..."))

        import requests_mock

        adapter = requests_mock.Adapter()
        session.mount("mock", adapter)

        for path in self.mocking_paths:

            if not isinstance(path, MutableMapping):
                msg = _(
                    "Mocking path {p!r} is not a dictionary object, but a " "{c} object instead."
                ).format(p=path, c=path.__class__.__name__)
                raise PowerDNSHandlerError(msg)

            for key in ("method", "url"):
                if key not in path:
                    msg = _("Mocking path has no {!r} key defined:").format(key)
                    msg += "\n" + pp(path)
                    raise PowerDNSHandlerError(msg)

            if self.verbose > 2:
                LOG.debug(_("Adding mocking path:") + "\n" + pp(path))
            adapter.register_uri(**path)


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
