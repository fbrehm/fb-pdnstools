#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@summary: An encapsulation class for zone objects by PowerDNS API
"""
from __future__ import absolute_import

# Standard modules
import logging
import copy
import re
import ipaddress
import json

from functools import cmp_to_key

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

# Third party modules
import six

# Own modules
from fb_tools.common import pp, to_utf8, to_bool, compare_fqdn, RE_DOT, to_str
from fb_tools.common import to_unicode, is_sequence

from fb_tools.obj import FbBaseObject

from .xlate import XLATOR

from . import BasePowerDNSHandler, DEFAULT_PORT, DEFAULT_API_PREFIX, FQDN_REGEX

from .errors import PowerDNSZoneError

from .record import PowerDnsSOAData, PowerDNSRecord
from .record import PowerDNSRecordSetComment
from .record import PowerDNSRecordSet, PowerDNSRecordSetList

__version__ = '0.11.2'

LOG = logging.getLogger(__name__)

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class PDNSNoRecordsToRemove(PowerDNSZoneError):

    # -------------------------------------------------------------------------
    def __init__(self, zone_name):
        self.zone_name = zone_name

    # -------------------------------------------------------------------------
    def __str__(self):

        msg = _("No Resource Record Sets found to remove from zone {!r}.").format(
            self.zone_name)
        return msg


# =============================================================================
class PowerDNSZone(BasePowerDNSHandler):
    """An encapsulation class for zone objects by PowerDNS API"""

    re_rev_ipv4 = re.compile(r'^((?:\d+\.)*\d+)\.in-addr\.arpa\.?$', re.IGNORECASE)
    re_rev_ipv6 = re.compile(r'^((?:[0-9a-f]\.)*[0-9a-f])\.ip6.arpa.?$', re.IGNORECASE)

    warn_on_unknown_property = False

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None,
            account=None, dnssec=False, edited_serial=None, id=None, kind=None,
            last_check=None, master_tsig_key_ids=None, slave_tsig_key_ids=None,
            masters=None, name=None, notified_serial=None, serial=None, url=None,
            soa_edit=None, soa_edit_api=None, nsec3narrow=None, nsec3param=None,
            presigned=None, api_rectify=None, master_server=None, port=DEFAULT_PORT,
            key=None, use_https=False, timeout=None, path_prefix=DEFAULT_API_PREFIX,
            simulate=None, force=None, terminal_has_colors=False, initialized=None,
            **kwargs):

        self._account = account
        self._dnssec = dnssec
        self._id = id
        self._kind = kind
        self._last_check = last_check
        self.masters = []
        if masters:
            self.masters = copy.copy(masters)
        self._name = None
        self._notified_serial = notified_serial
        self._serial = serial
        self._edited_serial = edited_serial
        self._url = url
        self._nsec3narrow = None
        if nsec3narrow is not None:
            self._nsec3narrow = to_bool(nsec3narrow)
        self._nsec3param = None
        if nsec3param is not None and str(nsec3param).strip() != '':
            self._nsec3param = str(nsec3param).strip()
        self._presigned = None
        if presigned is not None:
            self._presigned = to_bool(presigned)
        self._api_rectify = None
        if api_rectify is not None:
            self._api_rectify = to_bool(api_rectify)

        self._master_tsig_key_ids = []
        if master_tsig_key_ids:
            self.master_tsig_key_ids = master_tsig_key_ids

        self._slave_tsig_key_ids = []
        if slave_tsig_key_ids:
            self.slave_tsig_key_ids = slave_tsig_key_ids

        self._reverse_zone = False
        self._reverse_net = None

        self.rrsets = PowerDNSRecordSetList()

        self._soa_edit = soa_edit
        self._soa_edit_api = soa_edit_api

        self._add_keys = {}
        if kwargs:
            self._add_keys = copy.copy(kwargs)
            msg = _("Got unknown init parameters:") + '\n' + pp(self._add_keys)
            if self.warn_on_unknown_property:
                LOG.warn(msg)
            else:
                LOG.debug(msg)

        super(PowerDNSZone, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir,
            master_server=master_server, port=port, key=key, use_https=use_https,
            timeout=timeout, path_prefix=path_prefix, simulate=simulate, force=force,
            terminal_has_colors=terminal_has_colors, initialized=False)

        self.name = name

        if initialized is not None:
            self.initialized = initialized

    # -----------------------------------------------------------
    @classmethod
    def init_from_dict(
        cls, data,
            appname=None, verbose=0, version=__version__, base_dir=None,
            master_server=None, port=DEFAULT_PORT, key=None, use_https=False,
            timeout=None, path_prefix=DEFAULT_API_PREFIX,
            simulate=None, force=None, terminal_has_colors=False, initialized=None):

        if not isinstance(data, dict):
            raise PowerDNSZoneError(_("Given data {!r} is not a dict object.").format(data))

        # {   'account': 'local',
        #     'api_rectify': False,
        #     'dnssec': False,
        #     'id': 'bla.ai.',
        #     'kind': 'Master',
        #     'last_check': 0,
        #     'masters': [],
        #     'name': 'bla.ai.',
        #     'nsec3narrow': False,
        #     'nsec3param': '',
        #     'notified_serial': 2018080404,
        #     'rrsets': [   {   'comments': [],
        #                       'name': '59.55.168.192.in-addr.arpa.',
        #                       'records': [   {   'content': 'slave009.prometheus.pixelpark.net.',
        #                                          'disabled': False}],
        #                       'ttl': 86400,
        #                       'type': 'PTR'},
        #                    ...],
        #     'serial': 2018080404,
        #     'soa_edit': '',
        #     'soa_edit_api': 'INCEPTION-INCREMENT',
        #     'url': 'api/v1/servers/localhost/zones/bla.ai.'},

        params = {
            'appname': appname,
            'verbose': verbose,
            'version': version,
            'base_dir': base_dir,
            'master_server': master_server,
            'port': port,
            'key': key,
            'use_https': use_https,
            'timeout': timeout,
            'path_prefix': path_prefix,
            'simulate': simulate,
            'force': force,
            'terminal_has_colors': terminal_has_colors,
        }
        if initialized is not None:
            params['initialized'] = initialized

        rrsets = None
        if 'rrsets' in data:
            if data['rrsets']:
                rrsets = data['rrsets']
            del data['rrsets']

        new_data = {}
        for key in data:
            val = data[key]
            if isinstance(key, six.string_types):
                key = to_str(key)
            if isinstance(val, six.string_types):
                val = to_str(val)
            new_data[key] = val

        params.update(new_data)

        if verbose > 3:
            pout = copy.copy(params)
            pout['key'] = None
            if key:
                pout['key'] = '******'
            LOG.debug(_("Params initialisation:") + '\n' + pp(pout))

        zone = cls(**params)

        if rrsets:
            for single_rrset in rrsets:
                rrset = PowerDNSRecordSet.init_from_dict(
                    single_rrset, appname=appname, verbose=verbose, base_dir=base_dir,
                    master_server=master_server, port=port, key=key, use_https=use_https,
                    timeout=timeout, path_prefix=path_prefix, simulate=simulate,
                    force=force, terminal_has_colors=terminal_has_colors, initialized=True)
                zone.rrsets.append(rrset)

        zone.initialized = True

        return zone

    # -----------------------------------------------------------
    @property
    def account(self):
        """The name of the owning account of the zone, internal used
            to differ local visible zones from all other zones."""
        return getattr(self, '_account', None)

    @account.setter
    def account(self, value):
        if value:
            v = to_str(str(value).strip())
            if v:
                self._account = v
            else:
                self._account = None
        else:
            self._account = None

    # -----------------------------------------------------------
    @property
    def dnssec(self):
        """Is the zone under control of DNSSEC."""
        return getattr(self, '_dnssec', False)

    @dnssec.setter
    def dnssec(self, value):
        self._dnssec = bool(value)

    # -----------------------------------------------------------
    @property
    def id(self):
        """The unique idendity of the zone."""
        return getattr(self, '_id', None)

    @id.setter
    def id(self, value):
        if value:
            v = to_str(str(value).strip())
            if v:
                self._id = v
            else:
                self._id = None
        else:
            self._id = None

    # -----------------------------------------------------------
    @property
    def kind(self):
        """The kind or type of the zone."""
        return getattr(self, '_kind', None)

    @kind.setter
    def kind(self, value):
        if value:
            v = to_str(str(value).strip())
            if v:
                self._kind = v
            else:
                self._kind = None
        else:
            self._kind = None

    # -----------------------------------------------------------
    @property
    def last_check(self):
        """The timestamp of the last check of the zone"""
        return getattr(self, '_last_check', None)

    # -----------------------------------------------------------
    @property
    def name(self):
        """The name of the zone."""
        return getattr(self, '_name', None)

    @name.setter
    def name(self, value):
        if value:
            v = to_str(str(value).strip())
            if v:
                self._name = v
                match = self.re_rev_ipv4.search(v)
                if match:
                    self._reverse_zone = True
                    self._reverse_net = self.ipv4_nw_from_tuples(match.group(1))
                else:
                    match = self.re_rev_ipv6.search(v)
                    if match:
                        self._reverse_zone = True
                        self._reverse_net = self.ipv6_nw_from_tuples(match.group(1))
                    else:
                        self._reverse_zone = False
                        self._reverse_net = None
            else:
                self._name = None
                self._reverse_zone = False
                self._reverse_net = None
        else:
            self._name = None
            self._reverse_zone = False
            self._reverse_net = None

    # -----------------------------------------------------------
    @property
    def reverse_zone(self):
        """Is this a reverse zone?"""
        return self._reverse_zone

    # -----------------------------------------------------------
    @property
    def reverse_net(self):
        """An IP network object representing the network, for which
            this is the reverse zone."""
        return self._reverse_net

    # -----------------------------------------------------------
    @property
    def name_unicode(self):
        """The name of the zone in unicode, if it is an IDNA encoded zone."""
        n = getattr(self, '_name', None)
        if n is None:
            return None
        if 'xn--' in n:
            return to_utf8(n).decode('idna')
        return n

    # -----------------------------------------------------------
    @property
    def notified_serial(self):
        """The notified serial number of the zone"""
        return getattr(self, '_notified_serial', None)

    # -----------------------------------------------------------
    @property
    def serial(self):
        """The serial number of the zone"""
        return getattr(self, '_serial', None)

    # -----------------------------------------------------------
    @property
    def edited_serial(self):
        """The SOA serial as seen in query responses.
        Calculated using the SOA-EDIT metadata, default-soa-edit and
        default-soa-edit-signed settings."""
        return getattr(self, '_edited_serial', None)

    # -----------------------------------------------------------
    @property
    def url(self):
        """The URL in the API to get the zone object."""
        return getattr(self, '_url', None)

    # -----------------------------------------------------------
    @property
    def soa_edit(self):
        """The SOA edit property of the zone object."""
        return getattr(self, '_soa_edit', None)

    # -----------------------------------------------------------
    @property
    def soa_edit_api(self):
        """The SOA edit property (API) of the zone object."""
        return getattr(self, '_soa_edit_api', None)

    # -----------------------------------------------------------
    @property
    def nsec3narrow(self):
        """Some stuff belonging to DNSSEC."""
        return getattr(self, '_nsec3narrow', None)

    # -----------------------------------------------------------
    @property
    def nsec3param(self):
        """Some stuff belonging to DNSSEC."""
        return getattr(self, '_nsec3param', None)

    # -----------------------------------------------------------
    @property
    def presigned(self):
        """Some stuff belonging to PowerDNS >= 4.1."""
        return getattr(self, '_presigned', None)

    # -----------------------------------------------------------
    @property
    def api_rectify(self):
        """Some stuff belonging to PowerDNS >= 4.1."""
        return getattr(self, '_api_rectify', None)

    # -----------------------------------------------------------
    @property
    def add_keys(self):
        """Additional, unexpected keys on initialisation."""
        return copy.copy(self._add_keys)

    # -----------------------------------------------------------
    @property
    def master_tsig_key_ids(self):
        """The id of the TSIG keys used for master operation in this zone."""
        return copy.copy(self._master_tsig_key_ids)

    @master_tsig_key_ids.setter
    def master_tsig_key_ids(self, key_ids):
        self._master_tsig_key_ids = []
        if key_ids:
            if is_sequence(key_ids):
                for key_id in key_ids:
                    self._master_tsig_key_ids.append(key_id)
            else:
                self._master_tsig_key_ids.append(key_ids)

    # -----------------------------------------------------------
    @property
    def slave_tsig_key_ids(self):
        """The id of the TSIG keys used for slave operation in this zone."""
        return copy.copy(self._slave_tsig_key_ids)

    @slave_tsig_key_ids.setter
    def slave_tsig_key_ids(self, key_ids):
        self._slave_tsig_key_ids = []
        if key_ids:
            if is_sequence(key_ids):
                for key_id in key_ids:
                    self._slave_tsig_key_ids.append(key_id)
            else:
                self._slave_tsig_key_ids.append(key_ids)

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(PowerDNSZone, self).as_dict(short=short)
        res['account'] = self.account
        res['dnssec'] = copy.copy(self.dnssec)
        res['id'] = self.id
        res['kind'] = self.kind
        res['last_check'] = self.last_check
        res['masters'] = copy.copy(self.masters)
        res['name'] = self.name
        res['name_unicode'] = self.name_unicode
        res['notified_serial'] = self.notified_serial
        res['edited_serial'] = self.edited_serial
        res['serial'] = self.serial
        res['url'] = self.url
        res['rrsets'] = []
        res['soa_edit'] = self.soa_edit
        res['soa_edit_api'] = self.soa_edit_api
        res['nsec3narrow'] = self.nsec3narrow
        res['nsec3param'] = self.nsec3param
        res['presigned'] = self.presigned
        res['api_rectify'] = self.api_rectify
        res['reverse_zone'] = self.reverse_zone
        res['reverse_net'] = self.reverse_net
        res['add_keys'] = self.add_keys
        res['master_tsig_key_ids'] = self.master_tsig_key_ids
        res['slave_tsig_key_ids'] = self.slave_tsig_key_ids

        for rrset in self.rrsets:
            if isinstance(rrset, FbBaseObject):
                res['rrsets'].append(rrset.as_dict(short))
            else:
                res['rrsets'].append(rrset)

        return res

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        """

        return pp(self.as_dict(short=True))

    # -------------------------------------------------------------------------
    @classmethod
    def ipv4_nw_from_tuples(cls, tuples):

        bitmask = 0
        tokens = []
        for part in reversed(RE_DOT.split(tuples)):
            tokens.append(part)

        if len(tokens) == 3:
            tokens.append('0')
            bitmask = 24
        elif len(tokens) == 2:
            tokens.append('0')
            tokens.append('0')
            bitmask = 16
        elif len(tokens) == 1:
            tokens.append('0')
            tokens.append('0')
            tokens.append('0')
            bitmask = 8
        else:
            msg = _("Invalid source tuples for detecting IPv4-network: {!r}.").format(tuples)
            raise ValueError(msg)

        ip_str = to_unicode('.'.join(tokens) + '/{}'.format(bitmask))
        net = ipaddress.ip_network(ip_str)

        return net

    # -------------------------------------------------------------------------
    @classmethod
    def ipv6_nw_from_tuples(cls, tuples):

        parts = RE_DOT.split(tuples)
        bitmask = 0
        tokens = []
        token = ''
        i = 0

        for part in reversed(parts):
            bitmask += 4
            i += 1
            token += part
            if i >= 4:
                tokens.append(token)
                token = ''
                i = 0

        if token != '':
            tokens.append(token.ljust(4, '0'))

        ip_str = ':'.join(tokens)
        if len(tokens) < 8:
            ip_str += ':'
            if len(tokens) < 7:
                ip_str += ':'

        ip_str += to_unicode('/{}'.format(bitmask))
        net = ipaddress.ip_network(ip_str)

        return net

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

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

        if self.verbose > 3:
            LOG.debug(_("Copying current {}-object into a new one.").format(
                self.__class__.__name__))

        zone = self.__class__(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            account=self.account, dnssec=self.dnssec, edited_serial=self.edited_serial,
            id=self.id, kind=self.kind, last_check=self.last_check, masters=self.masters,
            name=self.name, notified_serial=self.notified_serial, serial=self.serial,
            url=self.url, presigned=self.presigned, api_rectify=self.api_rectify,
            master_tsig_key_ids=self.master_tsig_key_ids,
            slave_tsig_key_ids=self.slave_tsig_key_ids,
            master_server=self.master_server, port=self.port, key=self.key,
            use_https=self.use_https, timeout=self.timeout, path_prefix=self.path_prefix,
            simulate=self.simulate, force=self.force, initialized=False, **self._add_keys)

        zone.rrsets = copy.copy(self.rrsets)

        zone.initialized = True
        return zone

    # -------------------------------------------------------------------------
    def update(self):

        if not self.url:
            msg = _("Cannot update zone {!r}, no API URL defined.").format(self.name)
            raise PowerDNSZoneError(msg)

        LOG.debug(_("Updating data of zone {n!r} from API path {u!r} ...").format(
            n=self.name, u=self.url))
        json_response = self.perform_request(self.url)

        if 'account' in json_response:
            self.account = json_response['account']
        else:
            self.account = None

        if 'dnssec' in json_response:
            self.dnssec = json_response['dnssec']
        else:
            self.dnssec = False

        if 'id' in json_response:
            self.id = json_response['id']
        else:
            self.id = None

        if 'kind' in json_response:
            self.kind = json_response['kind']
        else:
            self.kind = None

        if 'last_check' in json_response:
            self._last_check = json_response['last_check']
        else:
            self._last_check = None

        if 'notified_serial' in json_response:
            self._notified_serial = json_response['notified_serial']
        else:
            self._notified_serial = None

        if 'serial' in json_response:
            self._serial = json_response['serial']
        else:
            self._serial = None

        if 'edited_serial' in json_response:
            self._edited_serial = json_response['edited_serial']
        else:
            self._edited_serial = None

        if 'nsec3narrow' in json_response:
            self._nsec3narrow = json_response['nsec3narrow']
        else:
            self._nsec3narrow = None

        if 'nsec3param' in json_response:
            self._nsec3param = json_response['nsec3param']
        else:
            self._nsec3param = None

        if 'soa_edit' in json_response:
            self._soa_edit = json_response['soa_edit']
        else:
            self._soa_edit = None

        if 'soa_edit_api' in json_response:
            self._soa_edit_api = json_response['soa_edit_api']
        else:
            self._soa_edit_api = None

        self.masters = []
        if 'masters' in json_response:
            self.masters = copy.copy(json_response['masters'])

        self._master_tsig_key_ids = []
        if 'master_tsig_key_ids' in json_response:
            self.master_tsig_key_ids = copy.copy(json_response['master_tsig_key_ids'])

        self._slave_tsig_key_ids = []
        if 'slave_tsig_key_ids' in json_response:
            self.slave_tsig_key_ids = copy.copy(json_response['slave_tsig_key_ids'])

        self.rrsets = PowerDNSRecordSetList()
        if 'rrsets' in json_response:
            for single_rrset in json_response['rrsets']:
                rrset = PowerDNSRecordSet.init_from_dict(
                    single_rrset, appname=self.appname, verbose=self.verbose,
                    base_dir=self.base_dir, master_server=self.master_server, port=self.port,
                    key=self.key, use_https=self.use_https, timeout=self.timeout,
                    path_prefix=self.path_prefix, simulate=self.simulate, force=self.force,
                    initialized=True)
                self.rrsets.append(rrset)

    # -------------------------------------------------------------------------
    def perform_request(
            self, path, no_prefix=True, method='GET', data=None, headers=None, may_simulate=False):
        """Performing the underlying API request."""

        return super(PowerDNSZone, self).perform_request(
            path=path, no_prefix=no_prefix, method=method, data=data,
            headers=copy.copy(headers), may_simulate=may_simulate)

    # -------------------------------------------------------------------------
    def patch(self, payload):

        if self.verbose > 1:
            LOG.debug(_("Patching zone {!r} ...").format(self.name))

        return self.perform_request(
            self.url, method='PATCH',
            data=json.dumps(payload), may_simulate=True)

    # -------------------------------------------------------------------------
    def get_soa(self):

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
                    appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
                    account='unknown', content=cmt, initialized=True)
                comment_list.append(comment)

        return comment_list

    # -------------------------------------------------------------------------
    def update_soa(self, new_soa, comments=None, ttl=None):

        if not isinstance(new_soa, PowerDnsSOAData):
            msg = _("New SOA must be of type {e}, given {t}: {s!r}").format(
                e='PowerDnsSOAData', t=new_soa.__class__.__name__, s=new_soa)
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
        rrset["changetype"] = 'REPLACE'
        for record in rrset["records"]:
            record["set-ptr"] = False

        payload = {"rrsets": [rrset]}

        if self.verbose > 1:
            LOG.debug(_("Setting new SOA {s!r} for zone {z!r}, TTL {t} ...").format(
                s=new_soa.data, z=self.name, t=ttl))

        self.patch(payload)

    # -------------------------------------------------------------------------
    def increase_serial(self):
        "Increasing the serial number of current zone."

        self.update()

        soa_rrset = self.get_soa_rrset()
        soa = soa_rrset.get_soa_data()

        old_serial = soa.serial
        new_serial = soa.increase_serial()

        LOG.debug(_("Increasing serial of zone {z!r} from {o} => {n}.").format(
            z=self.name, o=old_serial, n=new_serial))

        new_soa_record = PowerDNSRecord(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            content=soa.data, disabled=False, initialized=True)

        soa_rrset.records.clear()
        soa_rrset.records.append(new_soa_record)
        self.replace_rrset(soa_rrset)

        # self.update_soa(soa)

    # -------------------------------------------------------------------------
    def generate_new_comment_list(self, rrset, comment=None, account=None, append_comments=True):

        if not isinstance(rrset, PowerDNSRecordSet):
            msg = _("Parameter {w!r} {a!r} is not a {e} object, but a {c} object instead.").format(
                w='rrset', a=rrset, e='PowerDNSRecordSet', c=rrset.__class__.__name__)
            raise TypeError(msg)

        comment_list = []
        if append_comments:
            for cmt in rrset.comments:
                if cmt.valid and cmt.content:
                    comment_list.append(cmt)
        if comment:
            comment = str(comment).strip()
        if comment:
            used_account = ''
            if account:
                used_account = str(account).strip()
            if not used_account:
                used_account = 'unknown'
            cmt = PowerDNSRecordSetComment(
                appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
                account=used_account, content=comment)
            comment_list.append(cmt)

        return comment_list

    # -------------------------------------------------------------------------
    def replace_rrset(
            self, rrset, set_ptr=False, comment=None, account=None, append_comments=True):

        if not isinstance(rrset, PowerDNSRecordSet):
            msg = _("Parameter {w!r} {a!r} is not a {e} object, but a {c} object instead.").format(
                w='rrset', a=rrset, e='PowerDNSRecordSet', c=rrset.__class__.__name__)
            raise TypeError(msg)

        comment_list = self.generate_new_comment_list(
            rrset, comment=comment, account=account, append_comments=append_comments)
        rrset.comments = comment_list

        rrset_dict = rrset.as_dict(minimal=True)
        rrset_dict["changetype"] = 'REPLACE'
        for record in rrset_dict["records"]:
            record["set-ptr"] = bool(set_ptr)

        payload = {"rrsets": [rrset_dict]}
        LOG.debug(_("Replacing record set in zone {!r}.").format(self.name))

        self.patch(payload)

    # -------------------------------------------------------------------------
    def delete_rrset(self, rrset):

        if not isinstance(rrset, PowerDNSRecordSet):
            msg = _("Parameter {w!r} {a!r} is not a {e} object, but a {c} object instead.").format(
                w='rrset', a=rrset, e='PowerDNSRecordSet', c=rrset.__class__.__name__)
            raise TypeError(msg)

        rrset_dict = {
            'name': rrset.name,
            "type": rrset.type,
            "changetype": 'DELETE',
            "records": [],
            "comments": [],
        }

        payload = {"rrsets": [rrset_dict]}
        LOG.debug(_("Deleting record set in zone {!r}.").format(self.name))

        self.patch(payload)

    # -------------------------------------------------------------------------
    def add_record_to_recordset(
        self, fqdn, rrset_type, content, ttl=None, disabled=False, set_ptr=False,
            comment=None, account=None, append_comments=True):

        fqdn_used = self.verify_fqdn(fqdn)
        if not fqdn_used:
            return None
        rtype = self.verify_rrset_type(rrset_type)
        if not rtype:
            return None
        if self.verbose > 2:
            msg = _("Adding FQDN: {f!r}, type {t!r}, content: {c!r}.").format(
                f=fqdn_used, t=rtype, c=content)
            LOG.debug(msg)

        if ttl:
            ttl = int(ttl)

        rrset = self.get_rrset(fqdn, rrset_type)
        if rrset:
            if self.verbose > 1:
                msg = _("Got an existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype)
                LOG.debug(msg)
            if ttl:
                rrset.ttl = ttl
        else:
            if self.verbose > 1:
                msg = _("Got no existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype)
                LOG.debug(msg)
            rrset = PowerDNSRecordSet(
                appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
                initialized=False)
            rrset.name = fqdn_used
            rrset.type = rrset_type
            if ttl:
                rrset.ttl = ttl
            else:
                soa = self.get_soa()
                rrset.ttl = soa.ttl

        record = PowerDNSRecord(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            content=content, disabled=bool(disabled), initialized=True)
        if record in rrset.records:
            msg = _("Record {c!r} already contained in record set {f!r} type {t}.").format(
                c=content, f=rrset.name, t=rrset.type)
            LOG.warn(msg)
            return
        rrset.records.append(record)

        self.replace_rrset(
            rrset, set_ptr=set_ptr, comment=comment, account=account,
            append_comments=bool(append_comments))

    # -------------------------------------------------------------------------
    def replace_record_in_recordset(
        self, fqdn, rrset_type, content, ttl=None, disabled=False, set_ptr=False,
            comment=None, account=None, append_comments=True):

        fqdn_used = self.verify_fqdn(fqdn)
        if not fqdn_used:
            return None
        rtype = self.verify_rrset_type(rrset_type)
        if not rtype:
            return None
        if self.verbose > 2:
            msg = _("Replacing FQDN: {f!r}, type {t!r} by content: {c!r}.").format(
                f=fqdn_used, t=rtype, c=content)
            LOG.debug(msg)

        if ttl:
            ttl = int(ttl)

        rrset = self.get_rrset(fqdn, rrset_type)
        if rrset:
            if self.verbose > 1:
                msg = _("Got an existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype)
                LOG.debug(msg)
            rrset.records.clear()
            if ttl:
                rrset.ttl = ttl
        else:
            if self.verbose > 1:
                msg = _("Got no existing rrset for FQDN {f!r}, type {t!r}.").format(
                    f=fqdn_used, t=rtype)
                LOG.debug(msg)
            rrset = PowerDNSRecordSet(
                appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
                initialized=False)
            rrset.name = fqdn_used
            rrset.type = rrset_type
            if ttl:
                rrset.ttl = ttl
            else:
                soa = self.get_soa()
                rrset.ttl = soa.ttl

        record = PowerDNSRecord(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            content=content, disabled=bool(disabled), initialized=True)

        rrset.records.append(record)

        self.replace_rrset(
            rrset, set_ptr=set_ptr, comment=comment, account=account,
            append_comments=bool(append_comments))

    # -------------------------------------------------------------------------
    def add_address_record(
        self, fqdn, address, ttl=None, disabled=False, set_ptr=True,
            comment=None, account=None, append_comments=False):

        if not isinstance(address, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            msg = _(
                "Parameter address {a!r} is not an IPv4Address or IPv6Address object, "
                "but a {c} object instead.").format(a=address, c=address.__class__.__name__)
            raise TypeError(msg)

        record_type = 'A'
        if address.version == 6:
            record_type = 'AAAA'
        LOG.debug(_("Trying to create {t}-record {f!r} => {a!r}.").format(
            t=record_type, f=fqdn, a=str(address)))

        canon_fqdn = self.canon_name(fqdn)

        self.add_record_to_recordset(
            fqdn=canon_fqdn, rrset_type=record_type, content=str(address),
            ttl=ttl, disabled=disabled, set_ptr=set_ptr,
            comment=comment, account=account, append_comments=append_comments)

        return True

    # -------------------------------------------------------------------------
    def set_address_record(
        self, fqdn, address, ttl=None, disabled=False, set_ptr=True,
            comment=None, account=None, append_comments=False):

        if not isinstance(address, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            msg = _(
                "Parameter address {a!r} is not an IPv4Address or IPv6Address object, "
                "but a {c} object instead.").format(a=address, c=address.__class__.__name__)
            raise TypeError(msg)

        record_type = 'A'
        if address.version == 6:
            record_type = 'AAAA'
        LOG.debug(_("Trying to create {t}-record {f!r} => {a!r}.").format(
            t=record_type, f=fqdn, a=str(address)))

        canon_fqdn = self.canon_name(fqdn)

        self.replace_record_in_recordset(
            fqdn=canon_fqdn, rrset_type=record_type, content=str(address),
            ttl=ttl, disabled=disabled, set_ptr=set_ptr,
            comment=comment, account=account, append_comments=append_comments)

        return True

    # -------------------------------------------------------------------------
    def add_ptr_record(
        self, pointer, fqdn, ttl=None, disabled=False,
            comment=None, account=None, append_comments=False):

        canon_fqdn = self.canon_name(fqdn)
        LOG.debug(_("Trying to create {t}-record {f!r} => {a!r}.").format(
            t='PTR', f=pointer, a=canon_fqdn))

        self.replace_record_in_recordset(
            fqdn=pointer, rrset_type='PTR', content=canon_fqdn, ttl=ttl, disabled=disabled,
            set_ptr=False, comment=comment, account=account, append_comments=append_comments)

        return True

    # -------------------------------------------------------------------------
    def add_rrset_for_remove(self, fqdn, rr_type, rrsets=None):

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

        if not rrsets:
            raise PDNSNoRecordsToRemove(self.name_unicode)

        self.update()
        if self.verbose > 3:
            LOG.debug(_("Current zone:") + '\n' + pp(self.as_dict()))

        rrsets_rm = []

        for rrset in rrsets:
            found = False
            for item in self.rrsets:
                if item.name == rrset["name"] and item.type == rrset["type"]:
                    found = True
                    break
            if not found:
                msg = _("DNS {t!r}-record {n!r} is already deleted.").format(
                    t=rrset["type"], n=rrset["name"])
                LOG.warning(msg)
                continue
            rrsets_rm.append(rrset)
        if not rrsets_rm:
            raise PDNSNoRecordsToRemove(self.name_unicode)

        payload = {"rrsets": rrsets_rm}
        count = len(rrsets_rm)
        msg = ngettext(
            "Removing one resource record set from zone {z!r}.",
            "Removing {c} resource record sets from zone {z!r}.", count).format(
            c=count, z=self.name_unicode)
        LOG.info(msg)
        if self.verbose > 1:
            LOG.debug(_("Resorce record sets:") + '\n' + pp(payload))

        self.patch(payload)
        LOG.info(_("Done."))

        return True

    # -------------------------------------------------------------------------
    def notify(self):

        LOG.info(_("Notifying slave servers of zone {!r} ...").format(self.name))
        path = self.url + '/notify'
        return self.perform_request(path, method='PUT', may_simulate=True)

    # -------------------------------------------------------------------------
    def verify_fqdn(self, fqdn, raise_on_error=True):

        if not isinstance(fqdn, six.string_types):
            msg = _("A {w} must be a string type, but is {v!r} instead.").format(
                w='FQDN', v=fqdn)
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

        if fqdn_used == '@':
            return self.name

        if fqdn_used == self.name:
            return self.name

        tail = '.' + self.name
        if self.verbose > 2:
            LOG.debug(_("Checking FQDN {f!r} for ending on {t!r}.").format(
                f=fqdn_used, t=tail))
        if not fqdn_used.endswith(tail):
            msg = _("Invalid FQDN {f!r}, it must end up with {t!r}.").format(
                f=fqdn, t=tail)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        idx = fqdn_used.rfind(tail)
        head = fqdn_used[:idx]
        if self.verbose > 2:
            LOG.debug(_("Basename of FQDN {f!r} is {h!r}.").format(
                f=fqdn_used, h=head))

        if not FQDN_REGEX.match(fqdn_used):
            msg = _("Invalid FQDN {!r}.").format(fqdn)
            if raise_on_error:
                raise ValueError(msg)
            LOG.error(msg)
            return None

        return fqdn_used

    # -------------------------------------------------------------------------
    def get_rrset(self, fqdn, rrset_type, raise_on_error=True):

        fqdn_used = self.verify_fqdn(fqdn, raise_on_error=raise_on_error)
        if not fqdn_used:
            return None
        rtype = self.verify_rrset_type(rrset_type, raise_on_error=raise_on_error)
        if not rtype:
            return None

        LOG.debug(_("Searching for RecordSet {f!r} of type {t!r} in zone {z!r}.").format(
            f=fqdn_used, t=rtype, z=self.name))

        if not len(self.rrsets):
            self.update()

        for rrset in self.rrsets:
            if rrset.name == fqdn_used and rrset.type == rtype:
                if self.verbose > 2:
                    msg = _("Found {} RecordSet:").format(rtype)
                    msg += '\n' + pp(rrset.as_dict(minimal=True))
                    LOG.debug(msg)
                return rrset

        LOG.debug(_("Did not found RecordSet {f!r} of type {t!r}.".format(
            f=fqdn_used, t=rtype)))
        return None

    # -------------------------------------------------------------------------
    def get_soa_rrset(self, raise_on_error=True):

        rrset = self.get_rrset(fqdn=self.name, rrset_type='SOA', raise_on_error=raise_on_error)
        if not rrset:
            LOG.warning(_("Did not get SOA for zone {!r}.").format(self.name))
        return rrset


# =============================================================================
class PowerDNSZoneDict(MutableMapping):
    """
    A dictionary containing PDNS Zone objects.
    It works like a dict.
    i.e.:
    zones = PowerDNSZoneDict(PowerDNSZone(name='pp.com', ...))
    and
    zones['pp.com'] returns a PowerDNSZone object for zone 'pp.com'
    """

    msg_invalid_zone_type = _("Invalid item type {{!r}} to set, only {} allowed.").format(
        'PowerDNSZone')
    msg_key_not_name = _("The key {k!r} must be equal to the zone name {n!r}.")
    msg_none_type_error = _("None type as key is not allowed.")
    msg_empty_key_error = _("Empty key {!r} is not allowed.")
    msg_no_zone_dict = _("Object {o!r} is not a {e} object.")

    # -------------------------------------------------------------------------
    # __init__() method required to create instance from class.
    def __init__(self, *args, **kwargs):
        '''Use the object dict'''
        self._map = dict()

        for arg in args:
            self.append(arg)

    # -------------------------------------------------------------------------
    def _set_item(self, key, zone):

        if not isinstance(zone, PowerDNSZone):
            raise TypeError(self.msg_invalid_zone_type.format(zone.__class__.__name__))

        zone_name = zone.name
        if zone_name != key.lower():
            raise KeyError(self.msg_key_not_name.format(k=key, n=zone_name))

        self._map[zone_name] = zone

    # -------------------------------------------------------------------------
    def append(self, zone):

        if not isinstance(zone, PowerDNSZone):
            raise TypeError(self.msg_invalid_zone_type.format(zone.__class__.__name__))
        self._set_item(zone.name, zone)

    # -------------------------------------------------------------------------
    def _get_item(self, key):

        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == '':
            raise ValueError(self.msg_empty_key_error.format(key))

        return self._map[zone_name]

    # -------------------------------------------------------------------------
    def get(self, key):
        return self._get_item(key)

    # -------------------------------------------------------------------------
    def _del_item(self, key, strict=True):

        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == '':
            raise ValueError(self.msg_empty_key_error.format(key))

        if not strict and zone_name not in self._map:
            return

        del self._map[zone_name]

    # -------------------------------------------------------------------------
    # The next five methods are requirements of the ABC.
    def __setitem__(self, key, value):
        self._set_item(key, value)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        return self._get_item(key)

    # -------------------------------------------------------------------------
    def __delitem__(self, key):
        self._del_item(key)

    # -------------------------------------------------------------------------
    def __iter__(self):

        for zone_name in self.keys():
            yield zone_name

    # -------------------------------------------------------------------------
    def __len__(self):
        return len(self._map)

    # -------------------------------------------------------------------------
    # The next methods aren't required, but nice for different purposes:
    def __str__(self):
        '''returns simple dict representation of the mapping'''
        return str(self._map)

    # -------------------------------------------------------------------------
    def __repr__(self):
        '''echoes class, id, & reproducible representation in the REPL'''
        return '{}, {}({})'.format(
            super(PowerDNSZoneDict, self).__repr__(),
            self.__class__.__name__,
            self._map)

    # -------------------------------------------------------------------------
    def __contains__(self, key):
        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == '':
            raise ValueError(self.msg_empty_key_error.format(key))

        return zone_name in self._map

    # -------------------------------------------------------------------------
    def keys(self):

        return sorted(
            self._map.keys(),
            key=lambda x: cmp_to_key(compare_fqdn)(self._map[x].name_unicode))

    # -------------------------------------------------------------------------
    def items(self):

        item_list = []

        for zone_name in self.keys():
            item_list.append((zone_name, self._map[zone_name]))

        return item_list

    # -------------------------------------------------------------------------
    def values(self):

        value_list = []
        for zone_name in self.keys():
            value_list.append(self._map[zone_name])
        return value_list

    # -------------------------------------------------------------------------
    def __eq__(self, other):

        if not isinstance(other, PowerDNSZoneDict):
            raise TypeError(self.msg_no_zone_dict.format(o=other, e='PowerDNSZoneDict'))

        return self._map == other._map

    # -------------------------------------------------------------------------
    def __ne__(self, other):

        if not isinstance(other, PowerDNSZoneDict):
            raise TypeError(self.msg_no_zone_dict.format(o=other, e='PowerDNSZoneDict'))

        return self._map != other._map

    # -------------------------------------------------------------------------
    def pop(self, key, *args):

        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == '':
            raise ValueError(self.msg_empty_key_error.format(key))

        return self._map.pop(zone_name, *args)

    # -------------------------------------------------------------------------
    def popitem(self):

        if not len(self._map):
            return None

        zone_name = self.keys()[0]
        zone = self._map[zone_name]
        del self._map[zone_name]
        return (zone_name, zone)

    # -------------------------------------------------------------------------
    def clear(self):
        self._map = dict()

    # -------------------------------------------------------------------------
    def setdefault(self, key, default):

        if key is None:
            raise TypeError(self.msg_none_type_error)

        zone_name = str(key).lower().strip()
        if zone_name == '':
            raise ValueError(self.msg_empty_key_error.format(key))

        if not isinstance(default, PowerDNSZone):
            raise TypeError(self.msg_invalid_zone_type.format(default.__class__.__name__))

        if zone_name in self._map:
            return self._map[zone_name]

        self._set_item(zone_name, default)
        return default

    # -------------------------------------------------------------------------
    def update(self, other):

        if isinstance(other, PowerDNSZoneDict) or isinstance(other, dict):
            for zone_name in other.keys():
                self._set_item(zone_name, other[zone_name])
            return

        for tokens in other:
            key = tokens[0]
            value = tokens[1]
            self._set_item(key, value)

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):

        res = {}
        for zone_name in self._map:
            res[zone_name] = self._map[zone_name].as_dict(short)
        return res

    # -------------------------------------------------------------------------
    def as_list(self, short=True):

        res = []
        for zone_name in self.keys():
            res.append(self._map[zone_name].as_dict(short))
        return res


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
