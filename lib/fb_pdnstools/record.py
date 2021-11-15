#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2021 Frank Brehm, Berlin
@summary: An encapsulation class for a DNS record object by PowerDNS API
"""
from __future__ import absolute_import

# Standard modules
import logging
import copy
import re
import datetime
import time

try:
    from collections.abc import MutableSequence
except ImportError:
    from collections import MutableSequence

# Third party modules
import six

# Own modules
from fb_tools.common import pp, compare_fqdn, to_utf8, to_str

from fb_tools.obj import FbBaseObject

from .xlate import XLATOR

from . import BasePowerDNSHandler, DEFAULT_PORT, DEFAULT_API_PREFIX

from .errors import PowerDNSWrongRecordTypeError
from .errors import PowerDNSRecordSetError, PowerDNSWrongSoaDataError

__version__ = '0.6.3'

LOG = logging.getLogger(__name__)

TYPE_ORDER = {
    'SOA': 0,
    'NS': 1,
    'MX': 2,
    'A': 3,
    'AAAA': 4,
    'CNAME': 5,
    'SRV': 6,
    'TXT': 7,
    'SPF': 8,
    'PTR': 9,
}

_ = XLATOR.gettext


# =============================================================================
def compare_rrsets(x, y):

    if not isinstance(x, PowerDNSRecordSet):
        raise TypeError(_("Argument {a} {v!r} must be a {o} object.").format(
            a='x', v=x, o='PowerDNSRecordSet'))

    if not isinstance(y, PowerDNSRecordSet):
        raise TypeError(_("Argument {a} {v!r} must be a {o} object.").format(
            a='y', v=x, o='PowerDNSRecordSet'))

    ret = compare_fqdn(x.name, y.name)
    if ret:
        return ret

    xt = 99
    yt = 99
    if x.type.upper() in TYPE_ORDER:
        xt = TYPE_ORDER[x.type.upper()]
    if y.type.upper() in TYPE_ORDER:
        yt = TYPE_ORDER[y.type.upper()]

    if xt < yt:
        return -1
    if xt > yt:
        return 1
    return 0


# =============================================================================
class PowerDNSRecord(FbBaseObject):

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None, initialized=None,
            content=None, disabled=False):

        self._content = None
        if content:
            self._content = to_str(str(content))
        self._disabled = False
        self.disabled = disabled

        super(PowerDNSRecord, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir)

        if initialized is not None:
            self.initialized = initialized

    # -----------------------------------------------------------
    @property
    def content(self):
        "The underlying content of this record."
        return self._content

    # -----------------------------------------------------------
    @property
    def disabled(self):
        "Flag, whether the record is disabled or not."
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._disabled = bool(value)

    # -----------------------------------------------------------
    @property
    def enabled(self):
        "Flag, whether the record is enabled or not."
        if self.disabled:
            return False
        return True

    @enabled.setter
    def enabled(self, value):
        v = bool(value)
        if v:
            self._disabled = False
        else:
            self._disabled = True

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """

        if minimal:
            return {
                'content': self.content,
                'disabled': self.disabled,
            }

        res = super(PowerDNSRecord, self).as_dict(short=short)
        res['content'] = self.content
        res['disabled'] = self.disabled
        res['enabled'] = self.enabled

        return res

    # -------------------------------------------------------------------------
    def __copy__(self):

        return PowerDNSRecord(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            initialized=self.initialized, content=self.content, disabled=self.disabled)

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
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("content={!r}".format(self.content))
        fields.append("disabled={!r}".format(self.disabled))
        fields.append("appname={!r}".format(self.appname))
        fields.append("verbose={!r}".format(self.verbose))
        fields.append("version={!r}".format(self.version))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __eq__(self, other):

        if self.verbose > 4:
            LOG.debug(_("Comparing equality of {} objects ...").format(self.__class__.__name__))

        if not isinstance(other, PowerDNSRecord):
            return False

        if self.content is None:
            if other.content is None:
                return True
            return False

        if other.content is None:
            return False

        if self.content.lower() != other.content.lower():
            return False

        return True

    # -------------------------------------------------------------------------
    def __lt__(self, other):
        """ The '<' operator. """

        if self.verbose > 4:
            LOG.debug(_("Comparing less than of {} objects ...").format(self.__class__.__name__))

        if not isinstance(other, PowerDNSRecord):
            msg = _("Wrong type {cls} of other parameter {other!r} for comparision.").format(
                cls=other.__class__.__name__, other=other)
            raise PowerDNSWrongRecordTypeError(msg)

        if self == other:
            return False

        if self.content is None:
            return True

        if other.content is None:
            return False

        return self.content.lower() < other.content.lower()

    # -------------------------------------------------------------------------
    def __gt__(self, other):
        """ The '>' operator. """

        if self.verbose > 4:
            LOG.debug(_("Comparing greater than of {} objects ...").format(
                self.__class__.__name__))

        if not isinstance(other, PowerDNSRecord):
            msg = _("Wrong type {cls} of other parameter {other!r} for comparision.").format(
                cls=other.__class__.__name__, other=other)
            raise PowerDNSWrongRecordTypeError(msg)

        if self == other:
            return False

        if self.content is None:
            return False

        if other.content is None:
            return True

        return self.content.lower() > other.content.lower()


# =============================================================================
class PowerDnsSOAData(FbBaseObject):

    re_soa_data = re.compile(r'^\s*(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$')
    re_ws = re.compile(r'\s+')

    # -------------------------------------------------------------------------
    def __init__(
        self, primary=None, email=None, serial=None, refresh=None, retry=None, expire=None,
            ttl=None, appname=None, verbose=0, version=__version__,
            base_dir=None):

        self._primary = None
        self._email = None
        self._serial = None
        self._refresh = None
        self._retry = None
        self._expire = None
        self._ttl = None

        super(PowerDnsSOAData, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir,
            initialized=False)

        self.primary = primary
        self.email = email
        self.serial = serial
        self.refresh = refresh
        self.retry = retry
        self.expire = expire
        self.ttl = ttl

        if self.primary and self.email and self.serial is not None and self.refresh and \
                self.retry and self.expire and self.ttl:
            self.initialized = True
        else:
            self.initialized = False

    # -----------------------------------------------------------
    @property
    def primary(self):
        "The primary name server of this SOA"
        return self._primary

    @primary.setter
    def primary(self, value):
        if value is None:
            self._primary = None
            return
        self._primary = str(value).strip().lower()

    # -----------------------------------------------------------
    @property
    def email(self):
        "The E-Mail-address of the hostmaster of this zone."
        return self._email

    @email.setter
    def email(self, value):
        if value is None:
            self._email = None
            return
        self._email = str(value).strip().lower()

    # -----------------------------------------------------------
    @property
    def serial(self):
        "The serial number of this SOA."
        return self._serial

    @serial.setter
    def serial(self, value):
        if value is None:
            self._serial = None
            return
        self._serial = int(value)

    # -----------------------------------------------------------
    @property
    def refresh(self):
        "The time in seconds when slaves should ask master for changes."
        return self._refresh

    @refresh.setter
    def refresh(self, value):
        if value is None:
            self._refresh = None
            return
        self._refresh = int(value)

    # -----------------------------------------------------------
    @property
    def retry(self):
        """The time in seconds when slaves should retry getting changes from master,
            if an attemt to get it was not successful."""
        return self._retry

    @retry.setter
    def retry(self, value):
        if value is None:
            self._retry = None
            return
        self._retry = int(value)

    # -----------------------------------------------------------
    @property
    def expire(self):
        """The time in seconds when slaves should expiring the zone,
            if an attemt to get it was not successful."""
        return self._expire

    @expire.setter
    def expire(self, value):
        if value is None:
            self._expire = None
            return
        self._expire = int(value)

    # -----------------------------------------------------------
    @property
    def ttl(self):
        "The defaul TTL of this zone."
        return self._ttl

    @ttl.setter
    def ttl(self, value):
        if value is None:
            self._ttl = None
            return
        self._ttl = int(value)

    # -----------------------------------------------------------
    @property
    def data(self):
        "String representation of SOA data."
        if self.primary and self.email and self.serial is not None and self.refresh and \
                self.retry and self.expire and self.ttl:
            return "{_primary} {_email} {_serial} {_refresh} {_retry} {_expire} {_ttl}".format(
                **self.__dict__)
        else:
            return None

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(PowerDnsSOAData, self).as_dict(short=short)
        res['primary'] = self.primary
        res['email'] = self.email
        res['serial'] = self.serial
        res['refresh'] = self.refresh
        res['retry'] = self.retry
        res['expire'] = self.expire
        res['ttl'] = self.ttl
        res['data'] = self.data

        return res

    # -------------------------------------------------------------------------
    @classmethod
    def init_from_data(cls, data, appname=None, verbose=0, base_dir=None):

        line = cls.re_ws.sub(' ', to_str(data))
        match = cls.re_soa_data.match(line)
        if not match:
            raise PowerDNSWrongSoaDataError(data)

        soa = cls(
            primary=match.group(1), email=match.group(2), serial=match.group(3),
            refresh=match.group(4), retry=match.group(5), expire=match.group(6),
            ttl=match.group(7), appname=appname, verbose=verbose, base_dir=base_dir)

        return soa

    # -------------------------------------------------------------------------
    def __copy__(self):

        if self.verbose > 4:
            LOG.debug(_("Copying current {}-object in a new one.").format(self.__class__.__name__))

        soa = PowerDnsSOAData(
            primary=self.primary, email=self.email, serial=self.serial, refresh=self.refresh,
            retry=self.retry, expire=self.expire, ttl=self.ttl, appname=self.appname,
            version=self.version, base_dir=self.base_dir)
        return soa

    # -------------------------------------------------------------------------
    def __eq__(self, other):

        if self.verbose > 4:
            LOG.debug(_("Comparing {} objects ...").format(self.__class__.__name__))

        if not isinstance(other, PowerDnsSOAData):
            return False

        if self.primary != other.primary:
            return False
        if self.email != other.email:
            return False
        if self.serial != other.serial:
            return False
        if self.refresh != other.refresh:
            return False
        if self.retry != other.retry:
            return False
        if self.expire != other.expire:
            return False
        if self.ttl != other.ttl:
            return False

        return True

    # -------------------------------------------------------------------------
    def increase_serial(self):

        i = 0
        tpl = '{year:4d}{month:02d}{day:02d}{nr:02d}'
        curdate = datetime.date.today()
        new_serial = 0

        params = {
            'year': curdate.year,
            'month': curdate.month,
            'day': curdate.day,
            'nr': i,
        }

        while new_serial <= self.serial:
            new_serial = int(tpl.format(**params))
            if new_serial > self.serial:
                break
            i += 1
            if i > 99:
                msg = _(
                    "Serial overflow - old serial {o} is in future, new serial {n} "
                    "has reached its maximum value.").format(o=self.serial, n=new_serial)
                raise ValueError(msg)
            params['nr'] = i

        self.serial = new_serial
        return new_serial


# =============================================================================
class PowerDNSRecordList(MutableSequence):
    """
    A list containing Power DNS Records (as parts of a Record Set).
    """

    msg_no_pdns_record = _("Invalid type {t!r} as an item of a {c}, only {o} objects are allowed.")

    # -------------------------------------------------------------------------
    def __init__(self, *records):

        self._list = []

        for record in records:
            self.append(record)

    # -------------------------------------------------------------------------
    def index(self, record, *args):

        i = None
        j = None

        if len(args) > 0:
            if len(args) > 2:
                raise TypeError(_("{m} takes at most {max} arguments ({n} given).").format(
                    m='index()', max=3, n=len(args) + 1))
            i = int(args[0])
            if len(args) > 1:
                j = int(args[1])

        index = 0
        start = 0
        if i is not None:
            start = i
            if i < 0:
                start = len(self._list) + i
        wrap = False
        end = len(self._list)
        if j is not None:
            if j < 0:
                end = len(self._list) + j
                if end < index:
                    wrap = True
            else:
                end = j
        for index in list(range(len(self._list))):
            item = self._list[index]
            if index < start:
                continue
            if index >= end and not wrap:
                break
            if item == record:
                return index

        if wrap:
            for index in list(range(len(self._list))):
                item = self._list[index]
                if index >= end:
                    break
            if item == record:
                return index

        msg = _("Record {!r} is not in Record list.").format(record.content)
        raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __contains__(self, record):

        if not isinstance(record, PowerDNSRecord):
            raise TypeError(self.msg_no_pdns_record.format(
                t=record.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecord'))

        if not self._list:
            return False

        for item in self._list:
            if item == record:
                return True

        return False

    # -------------------------------------------------------------------------
    def count(self, record):

        if not isinstance(record, PowerDNSRecord):
            raise TypeError(self.msg_no_pdns_record.format(
                t=record.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecord'))

        if not self._list:
            return 0

        num = 0
        for item in self._list:
            if item == record:
                num += 1
        return num

    # -------------------------------------------------------------------------
    def __len__(self):
        return len(self._list)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        return self._list.__getitem__(key)

    # -------------------------------------------------------------------------
    def __reversed__(self):

        return reversed(self._list)

    # -------------------------------------------------------------------------
    def __setitem__(self, key, record):

        if not isinstance(record, PowerDNSRecord):
            raise TypeError(self.msg_no_pdns_record.format(
                t=record.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecord'))

        self._list.__setitem__(key, record)

    # -------------------------------------------------------------------------
    def __delitem__(self, key):

        del self._list[key]

    # -------------------------------------------------------------------------
    def append(self, record):

        if not isinstance(record, PowerDNSRecord):
            raise TypeError(self.msg_no_pdns_record.format(
                t=record.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecord'))

        self._list.append(record)

    # -------------------------------------------------------------------------
    def insert(self, index, record):

        if not isinstance(record, PowerDNSRecord):
            raise TypeError(self.msg_no_pdns_record.format(
                t=record.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecord'))

        self._list.insert(index, record)

    # -------------------------------------------------------------------------
    def __copy__(self):

        new_list = self.__class__()
        for record in self._list:
            new_list.append(copy.copy(record))
        return new_list

    # -------------------------------------------------------------------------
    def clear(self):
        "Remove all items from the PowerDNSRecordList."

        self._list = []

    # -------------------------------------------------------------------------
    def clean(self):
        "Wrapper for clear()"

        return self.clear()


# =============================================================================
class PowerDNSRecordSetComment(FbBaseObject):

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None, initialized=None,
            account=None, content='', modified_at=None):

        self._account = None
        self._content = ''
        self._modified_at = int(time.time() + 0.5)

        super(PowerDNSRecordSetComment, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir)

        self.account = account
        self.content = content
        self.modified_at = modified_at

        if initialized is not None:
            self.initialized = initialized

    # -------------------------------------------------------------------------
    @property
    def account(self):
        "The name of the account, who has created this comment"
        return self._account

    @account.setter
    def account(self, value):
        if value is None:
            self._account = None
            return
        v = str(value).strip()
        if v == '':
            self._account = None
            return
        self._account = v

    # -------------------------------------------------------------------------
    @property
    def content(self):
        "The underlying content of this comment"
        return self._content

    @content.setter
    def content(self, value):
        if value is None:
            self._content = ''
            return
        v = str(value).strip()
        self._content = v

    # -------------------------------------------------------------------------
    @property
    def modified_at(self):
        "The UNIX time stamp of the last modification of this comment."
        return self._modified_at

    @modified_at.setter
    def modified_at(self, value):
        if value is None:
            self._modified_at = int(time.time() + 0.5)
            return
        try:
            v = int(value)
        except ValueError as e:
            msg = (_(
                "Invalid value for {w} of a {c} object - ").format(
                w='modified_at', c=self.__class__.__name__) + str(e))
            raise ValueError(msg)
        if v < 0:
            msg = _(
                "Invalid value for {w} {v!r} of a {c} object - "
                "must be greater than or equal to zero.").format(
                w='modified_at', c=self.__class__.__name__, v=value)
            raise ValueError(msg)
        self._modified_at = v

    # -------------------------------------------------------------------------
    @property
    def modified_date(self):
        "The modification of this comment as a datetime object."

        return datetime.datetime.utcfromtimestamp(self.modified_at)

    # -------------------------------------------------------------------------
    @property
    def valid(self):
        "Is this a valid comment or not."
        if self.account is None or self.modified_at is None:
            return False
        return True

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """

        if minimal:
            return {
                'account': self.account,
                'content': self.content,
                'modified_at': self.modified_at,
            }

        res = super(PowerDNSRecordSetComment, self).as_dict(short=short)
        res['account'] = self.account
        res['content'] = self.content
        res['modified_at'] = self.modified_at
        res['modified_date'] = self.modified_date
        res['valid'] = self.valid

        return res

    # -------------------------------------------------------------------------
    def __copy__(self):

        return PowerDNSRecordSetComment(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            initialized=self.initialized,
            account=self.account, content=self.content, modified_at=self.modified_at)

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        """

        return pp(self.as_dict(minimal=True))

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("account={!r}".format(self.account))
        fields.append("content={!r}".format(self.content))
        fields.append("modified_at={!r}".format(self.modified_at))
        fields.append("appname={!r}".format(self.appname))
        fields.append("verbose={!r}".format(self.verbose))
        fields.append("version={!r}".format(self.version))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __eq__(self, other):

        if self.verbose > 4:
            LOG.debug(_("Comparing {} objects ...").format(self.__class__.__name__))

        if not isinstance(other, PowerDNSRecordSetComment):
            return False

        if self.account != other.account:
            return False

        if self.content != other.content:
            return False

        if self.modified_at != other.modified_at:
            return False

        return True


# =============================================================================
class PowerDNSRecordSet(BasePowerDNSHandler):

    default_ttl = 3600

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None,
            master_server=None, port=DEFAULT_PORT, key=None, use_https=False,
            timeout=None, path_prefix=DEFAULT_API_PREFIX, simulate=None, force=None,
            terminal_has_colors=False, initialized=None):

        # {   'comments': [],
        #     'name': 'www.bmwi.tv.',
        #     'records': [{'content': '77.74.236.5', 'disabled': False}],
        #     'ttl': 3600,
        #     'type': 'A'},

        self.comments = []
        self._name = None
        self.ttl = self.default_ttl
        self._type = None
        self.records = PowerDNSRecordList()

        super(PowerDNSRecordSet, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir,
            master_server=master_server, port=port, key=key, use_https=use_https,
            timeout=timeout, path_prefix=path_prefix, simulate=simulate, force=force,
            terminal_has_colors=terminal_has_colors, initialized=False,
        )

        if initialized is not None:
            self.initialized = initialized

    # -----------------------------------------------------------
    @property
    def name(self):
        "The name of this record set."
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, six.string_types):
            msg = _("A {w} must be a string type, but is {v!r} instead.").format(
                w='PowerDNSRecordSet.name', v=value)
            raise TypeError(msg)
        v = to_str(value).strip().lower()
        if v == '':
            msg = _("A {w} may not be empty: {v!r}.").format(
                w='PowerDNSRecordSet.name', v=value)
            raise ValueError(msg)
        self._name = v

    # -----------------------------------------------------------
    @property
    def name_unicode(self):
        """The name of the resource record set in unicode, if it is an IDNA encoded zone."""
        n = getattr(self, '_name', None)
        if n is None:
            return None
        if 'xn--' in n:
            return to_utf8(n).decode('idna')
        return n

    # -----------------------------------------------------------
    @property
    def type(self):
        "The type of this record set."
        return self._type

    @type.setter
    def type(self, value):
        if not isinstance(value, six.string_types):
            msg = _("A {w} must be a string type, but is {v!r} instead.").format(
                w='PowerDNSRecordSet.type', v=value)
            raise TypeError(msg)
        v = to_str(value).strip().upper()
        if v == '':
            msg = _("A {w} may not be empty: {v!r}.").format(
                w='PowerDNSRecordSet.type', v=value)
            raise ValueError(msg)
        v = self.verify_rrset_type(v)
        self._type = v

    # -----------------------------------------------------------
    @property
    def ttl(self):
        "The TTL of this record set."
        return self._ttl

    @ttl.setter
    def ttl(self, value):
        self._ttl = int(value)

    # -------------------------------------------------------------------------
    @classmethod
    def init_from_dict(
        cls, data, appname=None, verbose=0, version=__version__, base_dir=None,
            master_server=None, port=DEFAULT_PORT, key=None, use_https=False, timeout=None,
            path_prefix=DEFAULT_API_PREFIX, simulate=None, force=None,
            terminal_has_colors=False, initialized=None):

        if not isinstance(data, dict):
            raise PowerDNSRecordSetError(_("Given data {!r} is not a dict object.").format(data))

        if verbose > 3:
            LOG.debug(_("Creating {} object from data:").format(cls.__name__) + '\n' + pp(data))

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

        rrset = cls(**params)

        if 'comments' in data and data['comments']:
            for comment_dict in data['comments']:
                acc = None
                cont = ''
                modified_at = None
                if 'account' in comment_dict:
                    acc = comment_dict['account']
                if 'content' in comment_dict:
                    cont = comment_dict['content']
                if 'modified_at' in comment_dict:
                    modified_at = comment_dict['modified_at']
                comment = PowerDNSRecordSetComment(
                    appname=appname, verbose=verbose, base_dir=base_dir,
                    account=acc, content=cont, modified_at=modified_at)
                if comment.valid:
                    comment.initialized = True
                rrset.comments.append(comment)

        rrset._name = to_str(str(data['name']))
        rrset._type = to_str(str(data['type']).upper())
        if 'ttl' in data:
            rrset._ttl = int(data['ttl'])

        if 'records' in data:
            for single_record in data['records']:
                record = PowerDNSRecord(
                    appname=appname, verbose=verbose, base_dir=base_dir,
                    content=to_str(single_record['content']),
                    disabled=single_record['disabled'],
                )
                record.initialized = True
                rrset.records.append(record)

        rrset.initialized = True

        return rrset

    # -------------------------------------------------------------------------
    def name_relative(self, reference):

        # current name must be an absolute name
        if not self.name.endswith('.'):
            return self.name

        # reference name must be an absolute name
        if not reference.endswith('.'):
            return self.name

        ref_escaped = r'\.' + re.escape(reference) + r'$'
        rel_name = re.sub(ref_escaped, '', self.name)
        return rel_name

    # -------------------------------------------------------------------------
    def as_dict(self, short=True, minimal=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool
        @param minimal: Generate a minimal dict, which can be used for the PDNS API
        @type minimal: bool

        @return: structure as dict
        @rtype:  dict
        """

        if minimal:
            ret = {
                "comments": [],
                "name": self.name,
                "records": [],
                "ttl": self.ttl,
                "type": self.type,
            }
            for comment in self.comments:
                ret['comments'].append(comment.as_dict(minimal=True))
            for record in self.records:
                ret['records'].append(record.as_dict(minimal=True))
            return ret

        res = super(PowerDNSRecordSet, self).as_dict(short=short)
        res['name'] = self.name
        res['type'] = self.type
        res['ttl'] = self.ttl
        res['name_unicode'] = self.name_unicode
        res['comments'] = []
        res['records'] = []

        for record in self.records:
            res['records'].append(record.as_dict(short))

        for comment in self.comments:
            res['comments'].append(comment.as_dict(short=short))

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
    def __copy__(self):

        rrset = PowerDNSRecordSet(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            master_server=self.master_server, port=self.port, key=self.key,
            use_https=self.use_https, timeout=self.timeout, path_prefix=self.path_prefix,
            simulate=self.simulate, force=self.force,
            terminal_has_colors=self.terminal_has_colors, initialized=False)

        rrset._name = self.name
        rrset._type = self.type
        rrset._ttl = self.ttl
        rrset.comments = copy.copy(self.comments)
        rrset.records = copy.copy(self.records)

        rrset.initialized = True
        return rrset

    # -------------------------------------------------------------------------
    def __eq__(self, other):

        if self.verbose > 4:
            LOG.debug(_("Comparing {} objects ...").format(self.__class__.__name__))

        if not isinstance(other, PowerDNSRecordSet):
            return False

        if self.name != other.name:
            return False

        if self.type != other.type:
            return False

        return True

    # -------------------------------------------------------------------------
    def get_soa_data(self):

        if self.type != 'SOA':
            msg = (_("Cannot create {o} from record set:") + "\n{rs}").format(
                o='PowerDnsSOAData', rs=pp(self.as_dict()))
            raise PowerDNSRecordSetError(msg)

        if not self.records:
            msg = (_("RecordSet has no records:") + "\n{}").format(
                pp(self.as_dict()))
            raise PowerDNSRecordSetError(msg)

        record = self.records[0]
        soa = PowerDnsSOAData.init_from_data(
            record.content, appname=self.appname, verbose=self.verbose, base_dir=self.base_dir)
        if self.verbose > 3:
            LOG.debug((_("Got SOA:") + "\n{}").format(pp(soa.as_dict())))
        return soa


# =============================================================================
class PowerDNSRecordSetList(MutableSequence):
    """
    A list containing Power DNS Record Sets (of a zone).
    """

    msg_no_pdns_rrset = _("Invalid type {t!r} as an item of a {c}, only {o} objects are allowed.")

    # -------------------------------------------------------------------------
    def __init__(self, *rrsets):

        self._list = []

        for rrset in rrsets:
            self.append(rrset)

    # -------------------------------------------------------------------------
    def index(self, rrset, *args):

        i = None
        j = None

        if len(args) > 0:
            if len(args) > 2:
                raise TypeError(_("{m} takes at most {max} arguments ({n} given).").format(
                    m='index()', max=3, n=len(args) + 1))
            i = int(args[0])
            if len(args) > 1:
                j = int(args[1])

        index = 0
        start = 0
        if i is not None:
            start = i
            if i < 0:
                start = len(self._list) + i
        wrap = False
        end = len(self._list)
        if j is not None:
            if j < 0:
                end = len(self._list) + j
                if end < index:
                    wrap = True
            else:
                end = j
        for index in list(range(len(self._list))):
            item = self._list[index]
            if index < start:
                continue
            if index >= end and not wrap:
                break
            if item == rrset:
                return index

        if wrap:
            for index in list(range(len(self._list))):
                item = self._list[index]
                if index >= end:
                    break
            if item == rrset:
                return index

        msg = _("RecordSet {n!r} ({n}) is not in RecordSet list.").format(
            n=rrset.name, t=rrset.type)
        raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __contains__(self, rrset):

        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(self.msg_no_pdns_record.format(
                t=rrset.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecordSet'))

        if not self._list:
            return False

        for item in self._list:
            if item == rrset:
                return True

        return False

    # -------------------------------------------------------------------------
    def count(self, rrset):

        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(self.msg_no_pdns_record.format(
                t=rrset.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecordSet'))

        if not self._list:
            return 0

        num = 0
        for item in self._list:
            if item == rrset:
                num += 1
        return num

    # -------------------------------------------------------------------------
    def __len__(self):
        return len(self._list)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        return self._list.__getitem__(key)

    # -------------------------------------------------------------------------
    def __reversed__(self):

        return reversed(self._list)

    # -------------------------------------------------------------------------
    def __setitem__(self, key, rrset):

        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(self.msg_no_pdns_record.format(
                t=rrset.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecordSet'))

        self._list.__setitem__(key, rrset)

    # -------------------------------------------------------------------------
    def __delitem__(self, key):

        del self._list[key]

    # -------------------------------------------------------------------------
    def append(self, rrset):

        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(self.msg_no_pdns_record.format(
                t=rrset.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecordSet'))

        self._list.append(rrset)

    # -------------------------------------------------------------------------
    def insert(self, index, rrset):

        if not isinstance(rrset, PowerDNSRecordSet):
            raise TypeError(self.msg_no_pdns_record.format(
                t=rrset.__class__.__name__, c=self.__class__.__name__, o='PowerDNSRecordSet'))

        self._list.insert(index, rrset)

    # -------------------------------------------------------------------------
    def __copy__(self):

        new_list = self.__class__()
        for rrset in self._list:
            new_list.append(copy.copy(rrset))
        return new_list

    # -------------------------------------------------------------------------
    def clear(self):
        "Remove all items from the PowerDNSRecordSetList."

        self._list = []


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
