# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pyrolab Locker Class
--------------------

Utility for allowing classes to be locked and used by only one connection
at a time.
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from pyrolab.server import expose

if TYPE_CHECKING:
    from pyrolab.drivers import Instrument


log = logging.getLogger("pyrolab.server.locker")


@expose
class Lockable:
    """
    The Lockable instrument. Rejects new connections at the Daemon level when
    locked. Stores the user who locked the device for reference.
    """
    _RESOURCE_LOCK: bool = False

    def __init__(self) -> None:
        self._RESOURCE_LOCK: bool = False
        self.user: str = ""

    def lock(self, user: str="") -> bool:
        """
        Locks access to the object's attributes.

        Parameters
        ----------
        user : str, optional
            The user who has locked the device. Useful when a device is locked
            and another user wants to know who is using it.
        """
        self._RESOURCE_LOCK = True
        self.user = user

        daemon = getattr(self, "_pyroDaemon", None)
        if daemon:
            return daemon._lock(self._pyroId, daemon._last_requestor)

        return True


    def release(self) -> bool:
        """
        Releases the lock on the object.
        """
        self._RESOURCE_LOCK = False
        self.user = ""

        daemon = getattr(self, "_pyroDaemon", None)
        if daemon:
            return daemon._release(self._pyroId)

        return True

    def islocked(self) -> bool:
        """
        Returns the status of the lock.

        Returns
        -------
        bool
            True if the lock is engaged, False otherwise.
        """
        return self._RESOURCE_LOCK


def create_lockable(cls) -> Instrument:
    """
    Dynamically create a new class that is also based on Lockable.

    Parameters
    ----------
    cls : class
        The class to be used as a template while dynamically creating a new
        class.
    
    Returns
    -------
    class
        A subclass that inherits from the original class and ``Lockable``.
    """
    DynamicLockable = type(
        cls.__name__ + "Locker",
        (cls, Lockable, ),
        {}
    )
    return DynamicLockable
