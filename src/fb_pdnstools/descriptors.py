#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: A module for a collection of descriptors.

These descriptors may be used fo rdata properties in classes.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2019 - 2026 Frank Brehm, Berlin
"""

from __future__ import absolute_import

# Standard modules
import logging
from pathlib import Path
from pathlib import PosixPath

# Third party modules
from fb_tools.common import is_sequence
from fb_tools.common import to_bool

# Own modules
from . import VALID_RRSET_TYPES
from .xlate import XLATOR

__version__ = "0.4.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
class IntegerDescriptor:
    """Descriptor for an integer field."""

    # -------------------------------------------------------------------------
    def __init__(self, name, lower_limit=None, upper_limit=None, maybe_none=False):
        """Initialize the IntegerDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.maybe_none = to_bool(maybe_none)

        if lower_limit is None:
            self.lower_limit = None
        else:
            self.lower_limit = int(lower_limit)

        if upper_limit is None:
            self.upper_limit = None
        else:
            self.upper_limit = int(upper_limit)

        if (
            self.lower_limit is not None
            and self.upper_limit is not None
            and self.upper_limit < self.lower_limit
        ):
            msg = _(
                "The upper limit of an IntegerField must be greater or equal to its lower_limit."
            )
            raise ValueError(msg)

        self.lower_limit_msg = _(
            "Invalid value {{v}} of attribute {a}, must be greater or equal to {m}."
        ).format(a=self.public_name, m=self.lower_limit)
        self.upper_limit_msg = _(
            "Invalid value {{v}} of attribute {a}, must be less or equal to {m}."
        ).format(a=self.public_name, m=self.lower_limit)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, 0)

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as an integer value."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        val = int(value)

        if self.lower_limit is not None and val < self.lower_limit:
            msg = self.lower_limit_msg.format(v=val)
            raise ValueError(msg)

        if self.upper_limit is not None and val > self.upper_limit:
            msg = self.upper_limit_msg.format(v=value)
            raise ValueError(msg)

        setattr(instance, self.private_name, val)


# =============================================================================
class BooleanDescriptor:
    """Descriptor for a boolean field."""

    # -------------------------------------------------------------------------
    def __init__(self, name, maybe_none=False):
        """Initialize the BooleanDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.maybe_none = to_bool(maybe_none)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, "")

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as a string value."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        setattr(instance, self.private_name, to_bool(value))


# =============================================================================
class PosixPathDescriptor:
    """Descriptor for a field containing a Posix file path."""

    # -------------------------------------------------------------------------
    def __init__(self, name, must_absolute=False, maybe_none=False):
        """Initialize the PosixPathDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.must_absolute = to_bool(must_absolute)
        self.maybe_none = to_bool(maybe_none)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, "")

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as a string value."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        path = PosixPath(value)

        if self.must_absolute:
            if not path.is_absolute():
                mdg = _("The attribute {a!r} must be an absolute Posix path, given {p!r}.").format(
                    a=self.public_name, p=str(path)
                )
                raise ValueError(mdg)

        setattr(instance, self.private_name, path)


# =============================================================================
class PathDescriptor:
    """Descriptor for a field containing a common file path."""

    # -------------------------------------------------------------------------
    def __init__(self, name, must_absolute=False, maybe_none=False):
        """Initialize the PathDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.must_absolute = to_bool(must_absolute)
        self.maybe_none = to_bool(maybe_none)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, "")

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as a string value."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        path = Path(value)

        if self.must_absolute:
            if not path.is_absolute():
                mdg = _("The attribute {a!r} must be an absolute path, given {p!r}.").format(
                    a=self.public_name, p=str(path)
                )
                raise ValueError(mdg)

        setattr(instance, self.private_name, path)


# =============================================================================
class StringDescriptor:
    """Descriptor for a string field."""

    # -------------------------------------------------------------------------
    def __init__(
        self,
        name,
        lowcase=False,
        upcase=False,
        stripped=False,
        maybe_none=False,
        not_empty=False,
    ):
        """Initialize the StringDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.lowcase = to_bool(lowcase)
        self.upcase = to_bool(upcase)
        self.stripped = to_bool(stripped)
        self.maybe_none = to_bool(maybe_none)
        self.not_empty = to_bool(not_empty)

        if self.lowcase and self.upcase:
            msg = _(
                "The properties {lc!r} and {uc!r} of attribute {a!r} may not be set to {w} "
                "at the same time."
            ).format(lc="lowcase", uc="upcase", a=self.public_name, r="True")
            raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, "")

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as a string value."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        val = str(value)
        if self.lowcase:
            val = val.lower()
        elif self.upcase:
            val = val.upper()
        if self.stripped:
            val = val.strip()
        if self.not_empty and val == "":
            msg = _("The attribute {a!r} must not be empty.").format(a=self.public_name)
            raise ValueError(msg)
        setattr(instance, self.private_name, val)


# =============================================================================
class RrsetTypeDescriptor:
    """Descriptor for a string field for the 'type' field of a Resource record set."""

    # -------------------------------------------------------------------------
    def __init__(
        self,
        name,
        maybe_none=False,
    ):
        """Initialize the StringDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.maybe_none = to_bool(maybe_none)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, "")

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as a string value."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        val = str(value).strip().upper()
        if val == "":
            msg = _("The attribute {a!r} must not be empty.").format(a=self.public_name)
            raise ValueError(msg)

        if val not in VALID_RRSET_TYPES:
            msg = _("Invalid resource record set typ {t!r} for attribute {a!r} given.").format(
                t=value, a=self.public_name
            )
            raise ValueError(msg)
        setattr(instance, self.private_name, val)


# =============================================================================
class StringArrayDescriptor:
    """Descriptor for an field of an array of strings."""

    # -------------------------------------------------------------------------
    def __init__(
        self,
        name,
        lowcase=False,
        upcase=False,
        stripped=False,
        not_empty=False,
        maybe_none=False,
    ):
        """Initialize the StringDescriptor descriptor."""
        self.public_name = name
        self.private_name = "_" + name

        self.lowcase = to_bool(lowcase)
        self.upcase = to_bool(upcase)
        self.stripped = to_bool(stripped)
        self.not_empty = to_bool(not_empty)
        self.maybe_none = to_bool(maybe_none)

        if self.lowcase and self.upcase:
            msg = _(
                "The properties {lc!r} and {uc!r} of attribute {a!r} may not be set to {w} "
                "at the same time."
            ).format(lc="lowcase", uc="upcase", a=self.public_name, r="True")
            raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, [])

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as an array of strings."""
        if value is None:
            if self.maybe_none:
                setattr(instance, self.private_name, None)
                return
            msg = _("The attribute {a!r} must not be None.").format(a=self.public_name)
            raise TypeError(msg)

        array = []
        if is_sequence(value):
            for val in value:
                if self.lowcase:
                    val = val.lower()
                elif self.upcase:
                    val = val.upper()
                if self.stripped:
                    val = val.strip()
                if self.not_empty and val == "":
                    msg = _("The attribute {a!r} must not contain empty strings.").format(
                        a=self.public_name
                    )
                    raise ValueError(msg)
                array.append(str(val))
        else:
            if self.lowcase:
                value = value.lower()
            elif self.upcase:
                value = value.upper()
            if self.stripped:
                value = value.strip()
            if self.not_empty and value == "":
                msg = _("The attribute {a!r} must not contain empty strings.").format(
                    a=self.public_name
                )
                raise ValueError(msg)
            array.append(str(value))

        setattr(instance, self.private_name, array)


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
