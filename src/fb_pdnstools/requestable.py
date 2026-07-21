#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: The module for a base PowerDNS handler object for requestable objects.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
"""

from __future__ import absolute_import

# Standard modules
import copy
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
from fb_tools.common import pp
from fb_tools.common import to_bool

import requests
from requests.exceptions import RequestException

from six import add_metaclass

import urllib3

# Own modules
from . import DEFAULT_API_PREFIX
from . import DEFAULT_PORT
from . import DEFAULT_TIMEOUT
from . import DEFAULT_USE_HTTPS
from . import LIBRARY_NAME
from . import MAX_PORT_NUMBER
from .base import BasePdnsObject
from .base import BooleanField
from .base import IntegerField
from .base import PosixPathField
from .base import StringField
from .errors import PDNSApiError
from .errors import PDNSApiNotAuthorizedError
from .errors import PDNSApiNotFoundError
from .errors import PDNSApiRateLimitExceededError
from .errors import PDNSApiValidationError
from .errors import PDNSRequestError
from .errors import PowerDNSHandlerError
from .xlate import XLATOR

__version__ = "2.0.0"
LOG = logging.getLogger(__name__)

LOGLEVEL_REQUESTS_SET = False

_ = XLATOR.gettext


# =============================================================================
@add_metaclass(ABCMeta)
class BasePdnsRequestableObject(BasePdnsObject):
    """
    Base class for a PowerDNS handler for requestable object.

    Must not be instantiated directly.
    """

    default_port = DEFAULT_PORT
    default_timeout = DEFAULT_TIMEOUT
    default_api_servername = "localhost"

    loglevel_requests_set = False

    re_request_id = re.compile(r"/requests/([-a-f0-9]+)/", re.IGNORECASE)

    master_server = StringField(name="master_server", lowcase=True, stripped=True)
    api_key = StringField(name="api_key")
    use_https = BooleanField(name="use_https")
    mocked = BooleanField(name="mocked")
    path_prefix = PosixPathField(name="path_prefix", must_absolute=True)
    timeout = IntegerField(name="timeout", lower_limit=1, upper_limit=3600)
    user_agent = StringField(name="user_agent", stripped=True)
    api_servername = StringField(name="api_servername", stripped=True)

    port = IntegerField(name="port", lower_limit=1, upper_limit=MAX_PORT_NUMBER)
    port.lower_limit_msg = _(
        "Invalid port number {v} for the PowerDNS API, must be greater than zero."
    )
    port.upper_limit_msg = _(
        "Invalid port number {{v}} for the PowerDNS API, must be less or equal to {m}."
    ).format(m=MAX_PORT_NUMBER)

    # -------------------------------------------------------------------------
    def __init__(
        self,
        version=__version__,
        master_server=None,
        port=DEFAULT_PORT,
        api_key=None,
        use_https=DEFAULT_USE_HTTPS,
        timeout=DEFAULT_TIMEOUT,
        path_prefix=DEFAULT_API_PREFIX,
        *args,
        **kwargs,
    ):
        """Initialize a BasePdnsRequestableObject object."""
        self.master_server = master_server
        self.api_key = api_key
        self.port = port
        self.use_https = use_https
        self.mocked = False
        self.path_prefix = path_prefix
        self.timeout = timeout

        self.user_agent = "{}/{}".format(LIBRARY_NAME, __version__)
        self.api_servername = self.default_api_servername
        self.mocking_paths = []

        super(BasePdnsRequestableObject, self).__init__(*args, **kwargs, version=version)

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

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        res = super(BasePdnsRequestableObject, self).as_dict(short=short)
        res["api_key"] = None
        res["api_servername"] = self.api_servername
        res["default_api_servername"] = self.default_api_servername
        res["default_port"] = self.default_port
        res["default_timeout"] = self.default_timeout
        res["master_server"] = self.master_server
        res["mocked"] = self.mocked
        res["path_prefix"] = self.path_prefix
        res["port"] = self.port
        res["timeout"] = self.timeout
        res["use_https"] = self.use_https
        res["user_agent"] = self.user_agent

        show_secrets = False
        if "SHOW_PDNS_SECRETS" in os.environ and to_bool(os.environ["SHOW_PDNS_SECRETS"]):
            show_secrets = False

        if self.api_key:
            if show_secrets:
                res["api_key"] = self.api_key
            else:
                res["api_key"] = "*******"

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
        if self.api_key:
            headers["X-API-Key"] = self.api_key

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
