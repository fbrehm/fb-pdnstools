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
from pathlib import PosixPath

# Third party modules
from fb_tools.common import is_sequence
from fb_tools.common import to_bool

# Own modules
from .xlate import XLATOR

__version__ = "0.1.0"
LOG = logging.getLogger(__name__)

_ = XLATOR.gettext


# =============================================================================
class IntegerDescriptor:
    """Descriptor for an integer field."""

    # -------------------------------------------------------------------------
    def __init__(self, name=None, lower_limit=None, upper_limit=None):
        """Initialize the IntegerDescriptor descriptor."""
        if name:
            self.public_name = name
            self.private_name = "_" + name

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
            setattr(instance, self.private_name, 0)
            return

        val = int(value)

        if self.lower_limit is not None and val < self.lower_limit:
            msg = self.lower_limit_msg.format(v=val)
            raise ValueError(msg)

        if self.upper_limit is not None and val > self.upper_limit:
            msg = self.upper_limit_msg.format(v=value)
            raise ValueError(msg)

        # LOG.debug(f"Setting {self.public_name!r} to {val}.")
        setattr(instance, self.private_name, val)


# =============================================================================
class BooleanDescriptor:
    """Descriptor for a boolean field."""

    # -------------------------------------------------------------------------
    def __init__(self, name=None, maybe_none=False):
        """Initialize the BooleanDescriptor descriptor."""
        if name:
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
    def __init__(self, name=None, must_absolute=False):
        """Initialize the PosixPathDescriptor descriptor."""
        if name:
            self.public_name = name
            self.private_name = "_" + name

        self.must_absolute = to_bool(must_absolute)

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, "")

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as a string value."""
        path = PosixPath(value)

        if self.must_absolute:
            if not path.is_absolute():
                mdg = _("The attribute {a!r} must be an absolute Unix path, given {p!r}.").format(
                    a=self.public_name, p=str(path)
                )
                raise ValueError(mdg)

        setattr(instance, self.private_name, path)


# =============================================================================
class StringDescriptor:
    """Descriptor for a string field."""

    # -------------------------------------------------------------------------
    def __init__(self, name=None, lowcase=False, stripped=False):
        """Initialize the StringDescriptor descriptor."""
        if name:
            self.public_name = name
            self.private_name = "_" + name

        self.lowcase = lowcase
        self.stripped = stripped

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
            setattr(instance, self.private_name, "")
            return

        val = str(value)
        if self.lowcase:
            val = val.lower()
        if self.stripped:
            val = val.strip()
        # LOG.debug(f"Setting {self.public_name!r} to {val!r}.")
        setattr(instance, self.private_name, val)


# =============================================================================
class StringArrayDescriptor:
    """Descriptor for an field of an array of strings."""

    # -------------------------------------------------------------------------
    def __set_name__(self, owner, name):
        """Keep the name of teh descriptor."""
        self.public_name = name
        self.private_name = "_" + name
        self.lowcase = False
        self.stripped = False

    # -------------------------------------------------------------------------
    def __get__(self, instance, owner):
        """Get the data from instance object by the private name."""
        return getattr(instance, self.private_name, [])

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        """Set the data in the instance object by the private name as an array of strings."""
        if value is None:
            setattr(instance, self.private_name, [])
            return

        array = []
        if is_sequence(value):
            for val in value:
                if self.lowcase:
                    val = val.lower()
                if self.stripped:
                    val = val.strip()
                array.append(str(val))
        else:
            if self.lowcase:
                value = value.lower()
            if self.stripped:
                value = value.strip()
            array.append(str(value))

        # LOG.debug(f"Setting {self.public_name!r} to {array!r}.")
        setattr(instance, self.private_name, array)


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
