# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server
------

Wrapped server functions that references PyroLab configuration settings.
"""

from __future__ import annotations
import logging
from pathlib import Path
from pyrolab.server.configure import SERVER_DATA_DIR
from pyrolab.server.registry import create_unique_resource
from typing import Dict, List, TYPE_CHECKING, Union

import Pyro5
from Pyro5.core import URI
from Pyro5.api import expose
from yaml import dump, safe_load

from pyrolab.server.locker import Lockable

if TYPE_CHECKING:
    from Pyro5.socketutil import SocketConnection


log = logging.getLogger("pyrolab.server")


class Daemon(Pyro5.server.Daemon):
    pass


class LockableDaemon(Daemon):
    """
    A LockableDaemon supports lockable resources.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.locked_instances = {}

    def _lock(self, pyroId: str, conn: SocketConnection) -> bool:
        """
        Logs a "lock" action on a Pyro object.
        
        LockableDaemon tracks which connection owns the lock over a given Pyro
        object.

        Parameters
        ----------
        pyroId : str
            The pyroId of the Pyro object.
        conn : SocketConnection
            The socket connection with the client that owns the lock.

        Returns
        -------
        bool
            A success status flag.
        """
        if pyroId not in self.locked_instances:
            self.locked_instances[pyroId] = conn
        return True

    def _release(self, pyroId: str) -> bool:
        """
        Logs a "lock release" action on a Pyro object.

        LockableDaemon tracks which connection owns the lock over a given Pyro
        object. In the case of a release action, it does not matter which
        connection makes the release; only lock owners can even access the 
        release attribute.

        Parameters
        ----------
        pyroId : str
            The object to be released.

        Returns
        -------
        bool
            A success status flag. False if the instance wasn't locked to begin
            with.
        """
        removed = self.locked_instances.pop(pyroId, None)
        return True if removed else False

    @expose
    def release(self, uri: str) -> str:
        """
        Provides a way to force unlock a resource if the Daemon itself
        is registered with the nameserver.

        Parameters
        ----------
        uri : str
            The Pyro URI of the object to be unlocked.

        Returns
        -------
        result : bool
            True if the resource was successfully released, False otherwise.
        """
        objId = URI(uri).object
        obj = self.objectsById[objId]

        # Only matters when instance mode is "single".
        instance = self._pyroInstances.get(obj)
        if instance:
            return instance.release()
        else:
            return True

    def _getInstance(self, clazz, conn):
        """
        Find or create a new instance of the class.
        
        If an instance already exists, but is locked, an exception is raised.
        
        Parameters
        ----------
        clazz
            The Pyro object being accessed.
        conn
            The connection object the request is being made from.
        
        Returns
        -------
        instance : clazz
            The instance of the Pyro object being accessed.
        
        Raises
        ------
        Exception
            If an instance exists but is locked by a different connection.
        """
        self._last_requestor = conn
        obj = super()._getInstance(clazz, conn)
        if issubclass(obj.__class__, Lockable):
            if obj.islocked():
                lock_owner = self.locked_instances[obj._pyroId]
                if lock_owner != conn:
                    raise Exception(f"Pyro object is locked (by '{obj.user or lock_owner}').")
        return obj

    def clientDisconnect(self, conn):
        """
        Automatically releases any locked resources in the event of a client 
        disconnect.

        Parameters
        ----------
        conn : SocketConnection
            The SocketConnection object that was disconnected.
        """
        print("Client connection closed, releasing locks.")
        for objId, connection in self.locked_instances.items():
            if conn == connection:
                del self.locked_instances[objId]


# TODO: Make this some sort of PyroLab configuration parameter.
DAEMON_GROUP_DIR = SERVER_DATA_DIR / "DaemonGroups"
DAEMON_GROUP_DIR.mkdir(parents=True, exist_ok=True)

class DaemonGroup:
    """
    Parameters
    ----------
    name : str
        A human-readable name of the DaemonGroup.
    daemon_class : str
        The class name of the Daemon to use.
    server_config : str
        The name of an existing Pyrolab server profile to use.
    resources : list of str
        The names of resources, known to PyroLab's registry, that
        will be run together under one Daemon.
    registered_names : Dict[str, str]
        A mapping of resources names to nameserver registration names.
    """
    def __init__(self, name: str, daemon_class: str="LockableDaemon", 
                 server_config: str="default", resources: List[str]=[],
                 registered_names: Dict[str, str]={}):
        self.name = name
        self.daemon_class = daemon_class
        self.server_config = server_config
        self.resources = resources
        self.registered_names = registered_names

    @staticmethod
    def available() -> List[str]:
        groups = DAEMON_GROUP_DIR.glob('*.yaml')
        valid = [str(x.name)[:-5] for x in groups if x.is_file()]
        return valid

    @staticmethod
    def open(name) -> DaemonGroup:
        dg = DaemonGroup(name)
        dg.load(name=name)
        return dg

    def add(self, resource_name: str, registered_name: str) -> None:
        """
        Adds a known resource to the DaemonManager.

        Parameters
        ----------
        resource_name : str
            The name of the resource to be included in the group, as listed
            in the registry.
        registered_name : str
            The name used to register the resource with the nameserver.
        """
        self.resources.append(resource_name)
        self.registered_names[resource_name] = registered_name

    def remove(self, resource_name: str) -> None:
        """
        Removes a resource from the DaemonManager.
        
        Parameters
        ----------
        resource_name : str
            The name of the resource to be removed, as listed in the registry.
        """
        self.resources.remove(resource_name)
        self.registered_names.pop(resource_name)

    def load(self, path: Union[str, Path]="", name: str="") -> Union[DaemonGroup, bool]:
        """
        Loads DaemonGroup from a yaml file. Default file is the program's
        internal data file, but a user file can be supplied.

        Parameters
        ----------
        path : Union[str, Path], optional
            The path to the registry file to use. If not provided, uses the
            program's default data file.
        name : str, optional
            If a path is specified, it takes precedence. Otherwise, loads the
            DaemonGroup configuration with the given name.

        Returns
        -------
            The DaemonGroup object if loading is successful, else False.
        """
        if path:
            if type(path) is str:
                path = Path(path)
        else:
            path = DAEMON_GROUP_DIR / (name + ".yaml")
        if path.exists():
            with path.open('r') as fin:
                attrs = safe_load(fin)
                self.__dict__ = attrs
            return self
        return False
    
    def save(self, path: Union[str, Path]="", update_file: bool=False) -> None:
        """
        Saves the current resources to file for persisting server 
        configurations.

        A path can be specified to create a new file with DaemonGroup 
        information. This is for inspection or development purposes. If
        ``update_file`` is True, PyroLab can reference that file's location
        each time it is started instead of using its default ProgramData 
        location. (TODO: this is not yet impmlemented.)

        Parameters
        ----------
        path : Union[str, Path], optional
            The location to save the resource info file to.
        update_file : bool, optional
            Force PyroLab to update it's default resource info file 
            location. TODO: NotYetImplemented
        """
        if path:
            if type(path) is str:
                path = Path(path)
        else:
            path = DAEMON_GROUP_DIR / (self.name + ".yaml")
        with path.open('w') as fout:
            fout.write(dump(self.__dict__))
        
        if update_file:
            raise NotImplementedError

    def get_daemon(self):
        pass

    def get_pyro_objects(self):
        pass
