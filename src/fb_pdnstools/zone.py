#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: An encapsulation class for zone objects by PowerDNS API.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules
import copy
import ipaddress
import json
import logging
import os
import re

# Third party modules
from fb_tools.common import RE_DOT
from fb_tools.common import pp
from fb_tools.common import to_bool
from fb_tools.common import to_str
from fb_tools.common import to_unicode
from fb_tools.common import to_utf8
from fb_tools.obj import FbGenericBaseObject

import six

# Own modules
from . import FQDN_REGEX
from .descriptors import BooleanDescriptor
from .descriptors import IntegerDescriptor
from .descriptors import PosixPathDescriptor
from .descriptors import StringArrayDescriptor
from .descriptors import StringDescriptor
from .errors import PDNSNoRecordsToRemove
from .errors import PowerDNSZoneError
from .record import PowerDNSRecord
from .recordset import PowerDNSRecordSet
from .recordset import PowerDNSRecordSetList
from .recordsetcomment import PowerDNSRecordSetComment
from .requestable import BasePdnsRequestableObject
from .soa import PowerDnsSOAData
from .xlate import XLATOR

__version__ = "3.0.3"

LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PowerDNSZone(BasePdnsRequestableObject):
    """An encapsulation class for zone objects by PowerDNS API."""

    re_rev_ipv4 = re.compile(r"^((?:\d+\.)*\d+)\.in-addr\.arpa\.?$", re.IGNORECASE)
    re_rev_ipv6 = re.compile(r"^((?:[0-9a-f]\.)*[0-9a-f])\.ip6.arpa.?$", re.IGNORECASE)

    warn_on_unknown_property = False

    defaults = {
        "account": "",
        "api_rectify": None,
        "catalog": "",
        "dnssec": False,
        "edited_serial": 0,
        "id": "",
        "kind": "",
        "last_check": 0,
        "master_tsig_key_ids": [],
        "masters": [],
        "notified_serial": 0,
        "nsec3narrow": False,
        "nsec3param": "",
        "presigned": None,
        "serial": 0,
        "slave_tsig_key_ids": [],
        "soa_edit": "",
        "soa_edit_api": "",
        "url": None,
    }

    account = StringDescriptor("account", stripped=True)
    api_rectify = BooleanDescriptor("api_rectify", maybe_none=True)
    catalog = StringDescriptor("catalog", stripped=True)
    dnssec = BooleanDescriptor("dnssec")
    edited_serial = IntegerDescriptor("edited_serial", lower_limit=0)
    id = StringDescriptor("id", stripped=True, lowcase=True)  # noqa: A003
    kind = StringDescriptor("kind", stripped=True)
    last_check = IntegerDescriptor("last_check", lower_limit=0)
    master_tsig_key_ids = StringArrayDescriptor("master_tsig_key_ids", stripped=True)
    masters = StringArrayDescriptor("masters", stripped=True)
    name = StringDescriptor("name", lowcase=True, stripped=True, not_empty=True)
    notified_serial = IntegerDescriptor("notified_serial", lower_limit=0)
    nsec3narrow = BooleanDescriptor("nsec3narrow")
    nsec3param = StringDescriptor("nsec3param", stripped=True)
    presigned = StringArrayDescriptor("presigned", stripped=True, maybe_none=True)
    serial = IntegerDescriptor("serial", lower_limit=0)
    slave_tsig_key_ids = StringArrayDescriptor("slave_tsig_key_ids", stripped=True)
    soa_edit = StringDescriptor("soa_edit", stripped=True)
    soa_edit_api = StringDescriptor("soa_edit_api", stripped=True)
    url = PosixPathDescriptor("url", must_absolute=True, maybe_none=True)

    # -------------------------------------------------------------------------
    def __init__(self, name, version=__version__, **kwargs):
        """Initialize a PowerDNSZone record."""
        self.name = name

        for attr in self.defaults.keys():
            setattr(self, attr, self.defaults[attr])

        self.rrsets = PowerDNSRecordSetList()
        self._add_keys = {}

        if kwargs:
            for key in kwargs.keys():
                if key in self.defaults:
                    setattr(self, key, self.defaults[key])

                cls_key = key
                val = kwargs[key]
                if key == "id":
                    cls_key = "zone_id"
                if cls_key in self.defaults:
                    setattr(self, cls_key, val)
                else:
                    self._add_keys[key] = val

        for attr in self.defaults.keys():
            if attr in kwargs:
                del kwargs[attr]

        super(PowerDNSZone, self).__init__(**kwargs)

        if self.verbose > 1:
            LOG.debug("kwargs:" + "\n" + pp(kwargs))

    # -------------------------------------------------------------------------
    def import_data(self, data):
        """Import the given data from PowerDNS API."""
        super(PowerDNSZone, self).import_data(data)

        self.initialized = False

        for attr in self.defaults.keys():
            setattr(self, attr, self.defaults[attr])

        self.rrsets = PowerDNSRecordSetList()

        for key in data:
            val = data[key]
            if key in self.defaults:
                if val != self.defaults[key]:
                    setattr(self, key, val)

        rrsets = None
        if "rrsets" in data:
            if data["rrsets"]:
                rrsets = data["rrsets"]
            del data["rrsets"]

        # Data from API:
        # {   "account": "local",
        #     "api_rectify": False,
        #     "catalog": "",
        #     "dnssec": False,
        #     "edited_serial": 2026070901,
        #     "id": "bla.ai.",
        #     "kind": "Master",
        #     "last_check": 0,
        #     "masters": [],
        #     "master_tsig_key_ids": [
        #         "pp-dns.com."
        #     ],
        #     "name": "bla.ai.",
        #     "notified_serial": 2018080404,
        #     "nsec3narrow": False,
        #     "nsec3param": "",
        #     "rrsets': [   {   "comments": [],
        #                       "name": "59.55.168.192.in-addr.arpa.",
        #                       "records": [   {   "content": "slave009.prometheus.pixelpark.net.",
        #                                          "disabled": False}],
        #                       "ttl": 86400,
        #                       "type": "PTR"},
        #                    ...],
        #     "serial": 2018080404,
        #     "slave_tsig_key_ids": [],
        #     "soa_edit": '',
        #     "soa_edit_api"': 'INCEPTION-INCREMENT',
        #     "url": "api/v1/servers/localhost/zones/bla.ai."},

        if rrsets:
            for rrset_data in rrsets:
                rrset = PowerDNSRecordSet.init_from_dict(rrset_data)
                self.rrsets.append(rrset)

        self.initialized = True

    # -------------------------------------------------------------------------
    @classmethod
    def init_from_dict(cls, data, **kwargs):
        """Create a new PowerDNSZone object based on a given dict."""
        if not isinstance(data, dict):
            raise PowerDNSZoneError(_("Given data {!r} is not a dict object.").format(data))

        init_params = copy.copy(kwargs)

        if "name" not in data:
            msg = _("No name for zo zone in import data given.")
            raise PowerDNSZoneError(msg)
        name = data["name"]

        verbose = int(kwargs.get('verbose', 0))

        show_secrets = False
        if "SHOW_PDNS_SECRETS" in os.environ and to_bool(os.environ["SHOW_PDNS_SECRETS"]):
            show_secrets = False

        if verbose > 1:
            pout = copy.copy(init_params)
            pout["api_key"] = None
            if "api_key" in init_params and init_params["api_key"]:
                if show_secrets:
                    pout["api_key"] = init_params["api_key"]
                else:
                    pout["api_key"] = "******"
            LOG.debug(_("Params initialisation:") + "\n" + pp(pout))

        zone = cls(name=name, **init_params)
        zone.import_data(data)

        return zone

    # -----------------------------------------------------------
    @property
    def reverse_zone(self):
        """Return, whether this is a reverse zone."""
        match = self.re_rev_ipv4.search(self.name)
        if match:
            return True

        match = self.re_rev_ipv6.search(self.name)
        if match:
            return True

        return False

    # -----------------------------------------------------------
    @property
    def reverse_net(self):
        """Give an IP network object for the network, for which this is the reverse zone."""
        match = self.re_rev_ipv4.search(self.name)
        if match:
            return self.ipv4_nw_from_tuples(match.group(1))

        match = self.re_rev_ipv6.search(self.name)
        if match:
            return self.ipv6_nw_from_tuples(match.group(1))

        return ""

    # -----------------------------------------------------------
    @property
    def name_unicode(self):
        """Give name of the zone in unicode, if it is an IDNA encoded zone."""
        if "xn--" in self.name:
            return to_utf8(self.name).decode("idna")
        return self.name

    # -------------------------------------------------------------------------
    def export_data(self):
        """Typecast PDNS relevant data into a dict for reproduction."""
        res = {}

        for key in self.defaults.keys():
            val = getattr(self, key, None)
            if val is not None:
                res[key] = val

        res["rrsets"] = []
        for rrset in self.rrsets:
            res["rrsets"].append(rrset.export_data())

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
        res = super(PowerDNSZone, self).as_dict(short=short)

        for key in self.defaults.keys():
            res[key] = getattr(self, key, None)

        res["name_unicode"] = self.name_unicode
        res["reverse_net"] = self.reverse_net
        res["reverse_zone"] = self.reverse_zone
        res["rrsets"] = []

        for rrset in self.rrsets:
            if isinstance(rrset, FbGenericBaseObject):
                res["rrsets"].append(rrset.as_dict(short))
            else:
                res["rrsets"].append(rrset)

        return res

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecast for translating object structure into a string.

        @return: structure as string
        @rtype:  str
        """
        return pp(self.as_dict(short=True))

    # -------------------------------------------------------------------------
    @classmethod
    def ipv4_nw_from_tuples(cls, tuples):
        """Create ip_network-object from number tuples of the name of a reverse IPv4 zone."""
        bitmask = 0
        tokens = []
        for part in reversed(RE_DOT.split(tuples)):
            tokens.append(part)

        if len(tokens) == 3:
            tokens.append("0")
            bitmask = 24
        elif len(tokens) == 2:
            tokens.append("0")
            tokens.append("0")
            bitmask = 16
        elif len(tokens) == 1:
            tokens.append("0")
            tokens.append("0")
            tokens.append("0")
            bitmask = 8
        else:
            msg = _("Invalid source tuples for detecting IPv4-network: {!r}.").format(tuples)
            raise ValueError(msg)

        ip_str = to_unicode(".".join(tokens) + "/{}".format(bitmask))
        net = ipaddress.ip_network(ip_str)

        return net

    # -------------------------------------------------------------------------
    @classmethod
    def ipv6_nw_from_tuples(cls, tuples):
        """Create ip_network-object from hexnumber tuples of the name of a reverse IPv6 zone."""
        parts = RE_DOT.split(tuples)
        bitmask = 0
        tokens = []
        token = ""
        i = 0

        for part in reversed(parts):
            bitmask += 4
            i += 1
            token += part
            if i >= 4:
                tokens.append(token)
                token = ""
                i = 0

        if token != "":
            tokens.append(token.ljust(4, "0"))

        ip_str = ":".join(tokens)
        if len(tokens) < 8:
            ip_str += ":"
            if len(tokens) < 7:
                ip_str += ":"

        ip_str += to_unicode("/{}".format(bitmask))
        net = ipaddress.ip_network(ip_str)

        return net

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("name={!r}".format(self.name))
        fields.append("url={!r}".format(self.url))
        fields.append("reverse_zone={!r}".format(self.reverse_zone))
        fields.append("reverse_net={!r}".format(self.reverse_net))
        fields.append("kind={!r}".format(self.kind))
        fields.append("serial={!r}".format(self.serial))
        fields.append("dnssec={!r}".format(self.dnssec))
        fields.append("account={!r}".format(self.account))
        fields.append("appname={!r}".format(self.appname))
        fields.append("verbose={!r}".format(self.verbose))
        fields.append("version={!r}".format(self.version))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Return a new PowerDNSZone as a deep copy of the current object."""
        if self.verbose > 3:
            LOG.debug(
                _("Copying current {}-object into a new one.").format(self.__class__.__name__)
            )

        params = {}
        for key in self.defaults.keys():
            val = getattr(self, key, None)
            if val != self.defaults[key]:
                params[key] = val

        params.update(self._add_keys)

        zone = self.__class__(
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            presigned=self.presigned,
            master_server=self.master_server,
            port=self.port,
            api_key=self.api_key,
            use_https=self.use_https,
            timeout=self.timeout,
            path_prefix=self.path_prefix,
            simulate=self.simulate,
            force=self.force,
            initialized=False,
            **params,
        )

        zone.rrsets = copy.copy(self.rrsets)

        zone.initialized = True
        return zone

    # -------------------------------------------------------------------------
    def update(self):
        """Update the records in the zone by requesting the API."""
        if not self.url:
            msg = _("Cannot update zone {!r}, no API URL defined.").format(self.name)
            raise PowerDNSZoneError(msg)

        LOG.debug(
            _("Updating data of zone {n!r} from API path {u!r} ...").format(
                n=self.name, u=str(self.url)
            )
        )
        json_response = self.perform_request(str(self.url))

        for key in self.defaults:
            if key == "id":
                cls_key = "zone_id"
            val = json_response.get(key, self.defaults[cls_key])
            setattr(self, cls_key, val)

        self.rrsets = PowerDNSRecordSetList()
        if "rrsets" in json_response:
            for single_rrset in json_response["rrsets"]:
                rrset = PowerDNSRecordSet.init_from_dict(
                    single_rrset,
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
                self.rrsets.append(rrset)

    # -------------------------------------------------------------------------
    def perform_request(
        self, path, no_prefix=True, method="GET", data=None, headers=None, may_simulate=False
    ):
        """Perform the underlying API request."""
        return super(PowerDNSZone, self).perform_request(
            path=path,
            no_prefix=no_prefix,
            method=method,
            data=data,
            headers=copy.copy(headers),
            may_simulate=may_simulate,
        )

    # -------------------------------------------------------------------------
    def patch(self, payload):
        """Perform a PATCH request with given payload to current zone."""
        if self.verbose > 1:
            LOG.debug(_("Patching zone {!r} ...").format(self.name))

        return self.perform_request(
            str(self.url), method="PATCH", data=json.dumps(payload), may_simulate=True
        )

    # -------------------------------------------------------------------------
    def get_soa(self):
        """Return a PowerDnsSOAData object created from the SOA record of this zone."""
        rrset = self.get_soa_rrset()
        if not rrset:
            return None
        return rrset.get_soa_data()

    # -------------------------------------------------------------------------
    def _generate_comments_list(self, comments=None):

        comment_list_raw = []
        comment_list = []
        if comments:
            if isinstance(comments, list):
                for cmt in comments:
                    comment_list_raw.append(copy.copy(cmt))
            else:
                comment_list_raw.append(copy.copy(comments))
        for cmt in comment_list_raw:
            if not cmt:
                continue
            if isinstance(cmt, PowerDNSRecordSetComment):
                if cmt.valid:
                    comment_list.append(copy.copy(cmt))
                else:
                    LOG.warn(_("Found invalid comment {!r}.").format(str(cmt)))
            else:
                cmt = str(cmt).strip()
                comment = PowerDNSRecordSetComment(
                    appname=self.appname,
                    verbose=self.verbose,
                    base_dir=self.base_dir,
                    account="unknown",
                    content=cmt,
                    initialized=True,
                )
                comment_list.append(comment)

        return comment_list

    # -------------------------------------------------------------------------
    def update_soa(self, new_soa, comments=None, ttl=None):
        """Update the SOA of the zone on the PowerDNS server."""
        if not isinstance(new_soa, PowerDnsSOAData):
            msg = _("New SOA must be of type {e}, given {t}: {s!r}").format(
                e="PowerDnsSOAData", t=new_soa.__class__.__name__, s=new_soa
            )
            raise TypeError(msg)

        if ttl:
            ttl = int(ttl)
        else:
            if not len(self.rrsets):
                self.update()
            cur_soa_rrset = self.get_soa()
            if not cur_soa_rrset:
                raise RuntimeError(_("Got no SOA for zone {!r}.").format(self.name))
            ttl = cur_soa_rrset.ttl

        comment_list = []
        for comment in new_soa.comments:
            if comment.content:
                comment_list.append(comment)

        for comment in self._generate_comments_list(comments):
            if comment.content:
                comment_list.append(comment)

        rrset = new_soa.as_dict(minimal=True)
        rrset["comments"] = comment_list
        rrset["changetype"] = "REPLACE"
        for record in rrset["records"]:
            record["set-ptr"] = False

        payload = {"rrsets": [rrset]}

        if self.verbose > 1:
            LOG.debug(
                _("Setting new SOA {s!r} for zone {z!r}, TTL {t} ...").format(
                    s=new_soa.data, z=self.name, t=ttl
                )
            )

        self.patch(payload)

    # -------------------------------------------------------------------------
    def increase_serial(self):
        """Increase the serial number of current zone."""
        self.update()

        soa_rrset = self.get_soa_rrset()
        soa = soa_rrset.get_soa_data()

        old_serial = soa.serial
        new_serial = soa.increase_serial()

        LOG.debug(
            _("Increasing serial of zone {z!r} from {o} => {n}.").format(
                z=self.name, o=old_serial, n=new_serial
            )
        )

        new_soa_record = PowerDNSRecord(
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            content=soa.data,
            disabled=False,
            initialized=True,
        )

        soa_rrset.records.clear()
        soa_rrset.records.append(new_soa_record)
        self.replace_rrset(soa_rrset)

        # self.update_soa(soa)

    # -------------------------------------------------------------------------
    def generate_new_comment_list(self, rrset, comment=None, account=None, append_comments=True):
        """Create a list of rrset comments from given PowerDNSRecordSet object and update it."""
        if not isinstance(rrset, PowerDNSRecordSet):
            msg = _("Parameter {w!r} {a!r} is not a {e} object, but a {c} object instead.").format(
                w="rrset", a=rrset, e="PowerDNSRecordSet", c=rrset.__class__.__name__
            )
            raise TypeError(msg)

        comment_list = []
        if append_comments:
            for cmt in rrset.comments:
                if cmt.valid and cmt.content:
                    comment_list.append(cmt)
        if comment:
            comment = str(comment).strip()
        if comment:
            used_account = ""
            if account:
                used_account = str(account).strip()
            if not used_account:
                used_account = "unknown"
            cmt = PowerDNSRecordSetComment(
                appname=self.appname,
                verbose=self.verbose,
                base_dir=self.base_dir,
                account=used_account,
                content=comment,
            )
            comment_list.append(cmt)

        return comment_list

    # -------------------------------------------------------------------------
    def replace_rrset(
        self, rrset, set_ptr=False, comment=None, account=None, append_comments=True
    ):
        """Replace the recordset on the PDNS server."""
        if not isinstance(rrset, PowerDNSRecordSet):
            msg = _("Parameter {w!r} {a!r} is not a {e} object, but a {c} object instead.").format(
                w="rrset", a=rrset, e="PowerDNSRecordSet", c=rrset.__class__.__name__
            )
            raise TypeError(msg)

        comment_list = self.generate_new_comment_list(
            rrset, comment=comment, account=account, append_comments=append_comments
        )
        rrset.comments = comment_list

        rrset_dict = rrset.as_dict(minimal=True)
        rrset_dict["changetype"] = "REPLACE"
        for record in rrset_dict["records"]:
            record["set-ptr"] = bool(set_ptr)

        payload = {"rrsets": [rrset_dict]}
        LOG.debug(_("Replacing record set in zone {!r}.").format(self.name))

        self.patch(payload)

    # -------------------------------------------------------------------------
    def delete_rrset(self, rrset):
        """Delete the given recordset on the PDNS server."""
        if not isinstance(rrset, PowerDNSRecordSet):
            msg = _("Parameter {w!r} {a!r} is not a {e} object, but a {c} object instead.").format(
                w="rrset", a=rrset, e="PowerDNSRecordSet", c=rrset.__class__.__name__
            )
            raise TypeError(msg)

        rrset_dict = {
            "name": rrset.name,
            "type": rrset.type,
            "changetype": "DELETE",
            "records": [],
            "comments": [],
        }

        payload = {"rrsets": [rrset_dict]}
        LOG.debug(_("Deleting record set in zone {!r}.").format(self.name))

        self.patch(payload)

    # -------------------------------------------------------------------------
    def add_record_to_recordset(
        self,
        fqdn,
        rrset_type,
        content,
        ttl=None,
        disabled=False,
        set_ptr=False,
        comment=None,
        account=None,
        append_comments=True,
    ):
        """Add a record to the given recordset on the PDNS server."""
        fqdn_used = self.verify_fqdn(fqdn)
        if not fqdn_used:
            return None
        rtype = self.verify_rrset_type(rrset_type)
        if not rtype:
            return None
        if self.verbose > 2:
            msg = _("Adding FQDN: {f!r}, type {t!r}, content: {c!r}.").format(
                f=fqdn_used, t=rtype, c=content
            )
            LOG.debug(msg)

        if ttl:
            ttl = int(ttl)

        rrset = self.get_rrset(fqdn, rrset_type)
        if rrset:
            if self.verbose > 1:
                msg = _("Got an existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype
                )
                LOG.debug(msg)
            if ttl:
                rrset.ttl = ttl
        else:
            if self.verbose > 1:
                msg = _("Got no existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype
                )
                LOG.debug(msg)
            rrset = PowerDNSRecordSet(
                appname=self.appname,
                verbose=self.verbose,
                base_dir=self.base_dir,
                initialized=False,
            )
            rrset.name = fqdn_used
            rrset.type = rrset_type
            if ttl:
                rrset.ttl = ttl
            else:
                soa = self.get_soa()
                rrset.ttl = soa.ttl

        record = PowerDNSRecord(
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            content=content,
            disabled=bool(disabled),
            initialized=True,
        )
        if record in rrset.records:
            msg = _("Record {c!r} already contained in record set {f!r} type {t}.").format(
                c=content, f=rrset.name, t=rrset.type
            )
            LOG.warn(msg)
            return
        rrset.records.append(record)

        self.replace_rrset(
            rrset,
            set_ptr=set_ptr,
            comment=comment,
            account=account,
            append_comments=bool(append_comments),
        )

    # -------------------------------------------------------------------------
    def replace_record_in_recordset(
        self,
        fqdn,
        rrset_type,
        content,
        ttl=None,
        disabled=False,
        set_ptr=False,
        comment=None,
        account=None,
        append_comments=True,
    ):
        """Replace a record in the given recordset on the PDNS server."""
        fqdn_used = self.verify_fqdn(fqdn)
        if not fqdn_used:
            return None
        rtype = self.verify_rrset_type(rrset_type)
        if not rtype:
            return None
        if self.verbose > 2:
            msg = _("Replacing FQDN: {f!r}, type {t!r} by content: {c!r}.").format(
                f=fqdn_used, t=rtype, c=content
            )
            LOG.debug(msg)

        if ttl:
            ttl = int(ttl)

        rrset = self.get_rrset(fqdn, rrset_type)
        if rrset:
            if self.verbose > 1:
                msg = _("Got an existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype
                )
                LOG.debug(msg)
            rrset.records.clear()
            if ttl:
                rrset.ttl = ttl
        else:
            if self.verbose > 1:
                msg = _("Got no existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype
                )
                LOG.debug(msg)
            rrset = PowerDNSRecordSet(
                appname=self.appname,
                verbose=self.verbose,
                base_dir=self.base_dir,
                initialized=False,
            )
            rrset.name = fqdn_used
            rrset.type = rrset_type
            if ttl:
                rrset.ttl = ttl
            else:
                soa = self.get_soa()
                rrset.ttl = soa.ttl

        record = PowerDNSRecord(
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            content=content,
            disabled=bool(disabled),
            initialized=True,
        )

        rrset.records.append(record)

        self.replace_rrset(
            rrset,
            set_ptr=set_ptr,
            comment=comment,
            account=account,
            append_comments=bool(append_comments),
        )

    # -------------------------------------------------------------------------
    def add_address_record(
        self,
        fqdn,
        address,
        ttl=None,
        disabled=False,
        set_ptr=True,
        comment=None,
        account=None,
        append_comments=False,
    ):
        """Add a PTR record to the current (revertse) zone on the PDNS server."""
        if not isinstance(address, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            msg = _(
                "Parameter address {a!r} is not an IPv4Address or IPv6Address object, "
                "but a {c} object instead."
            ).format(a=address, c=address.__class__.__name__)
            raise TypeError(msg)

        record_type = "A"
        if address.version == 6:
            record_type = "AAAA"
        LOG.debug(
            _("Trying to create {t}-record {f!r} => {a!r}.").format(
                t=record_type, f=fqdn, a=str(address)
            )
        )

        canon_fqdn = self.canon_name(fqdn)

        self.add_record_to_recordset(
            fqdn=canon_fqdn,
            rrset_type=record_type,
            content=str(address),
            ttl=ttl,
            disabled=disabled,
            set_ptr=set_ptr,
            comment=comment,
            account=account,
            append_comments=append_comments,
        )

        return True

    # -------------------------------------------------------------------------
    def set_address_record(
        self,
        fqdn,
        address,
        ttl=None,
        disabled=False,
        set_ptr=True,
        comment=None,
        account=None,
        append_comments=False,
    ):
        """Replace a PTR record on the current (revertse) zone on the PDNS server."""
        if not isinstance(address, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            msg = _(
                "Parameter address {a!r} is not an IPv4Address or IPv6Address object, "
                "but a {c} object instead."
            ).format(a=address, c=address.__class__.__name__)
            raise TypeError(msg)

        record_type = "A"
        if address.version == 6:
            record_type = "AAAA"
        LOG.debug(
            _("Trying to create {t}-record {f!r} => {a!r}.").format(
                t=record_type, f=fqdn, a=str(address)
            )
        )

        canon_fqdn = self.canon_name(fqdn)

        self.replace_record_in_recordset(
            fqdn=canon_fqdn,
            rrset_type=record_type,
            content=str(address),
            ttl=ttl,
            disabled=disabled,
            set_ptr=set_ptr,
            comment=comment,
            account=account,
            append_comments=append_comments,
        )

        return True

    # -------------------------------------------------------------------------
    def add_ptr_record(
        self,
        pointer,
        fqdn,
        ttl=None,
        disabled=False,
        comment=None,
        account=None,
        append_comments=False,
    ):
        """Add a PTR record to the current (revertse) zone on the PDNS server."""
        canon_fqdn = self.canon_name(fqdn)
        LOG.debug(
            _("Trying to create {t}-record {f!r} => {a!r}.").format(
                t="PTR", f=pointer, a=canon_fqdn
            )
        )

        self.replace_record_in_recordset(
            fqdn=pointer,
            rrset_type="PTR",
            content=canon_fqdn,
            ttl=ttl,
            disabled=disabled,
            set_ptr=False,
            comment=comment,
            account=account,
            append_comments=append_comments,
        )

        return True

    # -------------------------------------------------------------------------
    def add_rrset_for_remove(self, fqdn, rr_type, rrsets=None):
        """Append a dict for removing a recordset to a list."""
        if rrsets is None:
            rrsets = []

        rrset = {
            "name": self.canon_name(fqdn),
            "type": rr_type.upper(),
            "records": [],
            "comments": [],
            "changetype": "DELETE",
        }
        rrsets.append(rrset)
        return rrsets

    # -------------------------------------------------------------------------
    def del_rrsets(self, rrsets):
        """Remove the recordsets in the given list fron PDNS server´."""
        if not rrsets:
            raise PDNSNoRecordsToRemove(self.name_unicode)

        self.update()
        if self.verbose > 3:
            LOG.debug(_("Current zone:") + "\n" + pp(self.as_dict()))

        rrsets_rm = []

        for rrset in rrsets:
            found = False
            for item in self.rrsets:
                if item.name == rrset["name"] and item.type == rrset["type"]:
                    found = True
                    break
            if not found:
                msg = _("DNS {t!r}-record {n!r} is already deleted.").format(
                    t=rrset["type"], n=rrset["name"]
                )
                LOG.warning(msg)
                continue
            rrsets_rm.append(rrset)
        if not rrsets_rm:
            raise PDNSNoRecordsToRemove(self.name_unicode)

        payload = {"rrsets": rrsets_rm}
        count = len(rrsets_rm)
        msg = ngettext(
            "Removing one resource record set from zone {z!r}.",
            "Removing {c} resource record sets from zone {z!r}.",
            count,
        ).format(c=count, z=self.name_unicode)
        LOG.info(msg)
        if self.verbose > 1:
            LOG.debug(_("Resorce record sets:") + "\n" + pp(payload))

        self.patch(payload)
        LOG.info(_("Done."))

        return True

    # -------------------------------------------------------------------------
    def notify(self):
        """Initiate a notify of all secondary servers of current zone."""
        LOG.info(_("Notifying slave servers of zone {!r} ...").format(self.name))
        path = str(self.url) + "/notify"
        return self.perform_request(path, method="PUT", may_simulate=True)

    # -------------------------------------------------------------------------
    def verify_fqdn(self, fqdn, raise_on_error=True):
        """Verify syntax of the given FQDN, and whether it fits into current zone."""
        if not isinstance(fqdn, six.string_types):
            msg = _("A {w} must be a string type, but is {v!r} instead.").format(w="FQDN", v=fqdn)
            if raise_on_error:
                raise TypeError(msg)
            LOG.error(msg)
            return None

        fqdn_used = to_str(fqdn).strip().lower()
        if not fqdn_used:
            msg = _("Invalid, empty FQDN {!r} given.").format(fqdn)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        if fqdn_used == "@":
            return self.name

        if fqdn_used == self.name:
            return self.name

        tail = "." + self.name
        if self.verbose > 2:
            LOG.debug(_("Checking FQDN {f!r} for ending on {t!r}.").format(f=fqdn_used, t=tail))
        if not fqdn_used.endswith(tail):
            msg = _("Invalid FQDN {f!r}, it must end up with {t!r}.").format(f=fqdn, t=tail)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        idx = fqdn_used.rfind(tail)
        head = fqdn_used[:idx]
        if self.verbose > 2:
            LOG.debug(_("Basename of FQDN {f!r} is {h!r}.").format(f=fqdn_used, h=head))

        if not FQDN_REGEX.match(fqdn_used):
            msg = _("Invalid FQDN {!r}.").format(fqdn)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        return fqdn_used

    # -------------------------------------------------------------------------
    def get_rrset(self, fqdn, rrset_type, raise_on_error=True):
        """Search a record set by given name and type."""
        fqdn_used = self.verify_fqdn(fqdn, raise_on_error=raise_on_error)
        if not fqdn_used:
            return None
        rtype = self.verify_rrset_type(rrset_type, raise_on_error=raise_on_error)
        if not rtype:
            return None

        LOG.debug(
            _("Searching for RecordSet {f!r} of type {t!r} in zone {z!r}.").format(
                f=fqdn_used, t=rtype, z=self.name
            )
        )

        if not len(self.rrsets):
            self.update()

        for rrset in self.rrsets:
            if rrset.name == fqdn_used and rrset.type == rtype:
                if self.verbose > 2:
                    msg = _("Found {} RecordSet:").format(rtype)
                    msg += "\n" + pp(rrset.as_dict(minimal=True))
                    LOG.debug(msg)
                return rrset

        LOG.debug(_("Did not found RecordSet {f!r} of type {t!r}.".format(f=fqdn_used, t=rtype)))
        return None

    # -------------------------------------------------------------------------
    def get_soa_rrset(self, raise_on_error=True):
        """Search for the SOA record set of current zone."""
        rrset = self.get_rrset(fqdn=self.name, rrset_type="SOA", raise_on_error=raise_on_error)
        if not rrset:
            LOG.warning(_("Did not get SOA for zone {!r}.").format(self.name))
        return rrset


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
