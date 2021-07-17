# # -*- coding: utf-8 -*-
# #
# # Copyright © PyroLab Project Contributors
# # Licensed under the terms of the GNU GPLv3+ License
# # (see pyrolab/__init__.py for details)

# """
# Server Resources
# ----------------

# The scripts used for putting up and taking down Daemons and Workers from the
# multiprocessing module. Since child processes need to be able to import the
# script containing the target function, the target functions are contained
# within this module where no new processes are ever spawned. The prevents 
# the recursive creation of new processes as the module is imported.
# """

# from __future__ import annotations
# import importlib
# import multiprocessing
# from typing import TYPE_CHECKING, Any, Dict, Tuple, Type

# from Pyro5.core import locate_ns

# from pyrolab.server.registry import registry
# from pyrolab.server.configure import ServerConfiguration

# if TYPE_CHECKING:
#     from multiprocessing.queues import Queue

#     from Pyro5.core import URI

#     from pyrolab.server.server import Daemon
#     from pyrolab.server.registry import InstrumentInfo


# class ResourceInfo:
#     """
#     Groups information about daemons and nameservers with names of known
#     Instruments.

#     Parameters
#     ----------
#     registered_name : str
#         The name the known Instrument is registered in the nameserver by.
#     srv_cfg : ServerConfiguration, optional
#         A ServerConfiguration object; since each Resource is launched in its
#         own Daemon, each Daemon can have its own server configuration.
#     daemon_module : str
#         The string representation of the module containing the Daemon for this
#         Resource.
#     daemon_class : str
#         The string representation of the class name of the Daemon for this
#         Resource.
#     instance_mode : str, optional
#         A instance mode of the server; "single", "session", or "percall" 
#         (default "single").
#     ns_host : str
#         The nameserver hostname.
#     ns_port : int
#         The nameserver port.
#     active : bool, optional
#         Whether this Resource is automatically hosted by ResourceManager or not
#         (default True).
#     """
#     def __init__(self, registered_name: str="", 
#                  srv_cfg: ServerConfiguration=ServerConfiguration(),
#                  daemon_module: str="", daemon_class: str="", 
#                  instance_mode: str="single", ns_host: str=None, 
#                  ns_port: int=None, active: bool=True) -> None:
#         self.registered_name = registered_name
#         self.srv_cfg = srv_cfg
#         self.daemon_module = daemon_module
#         self.daemon_class = daemon_class
#         self.instance_mode = instance_mode
#         self.ns_host = ns_host
#         self.ns_port = ns_port
#         self.active = active

#     @classmethod
#     def from_dict(cls, d: Dict[str, Any]) -> ResourceInfo:
#         """
#         Constructs a ResourceInfo instance from a dictionary of attributes.

#         Parameters
#         ----------
#         d : Dict[str, Any]
#             The dictionary containing parameters to be passed to ResourceInfo's
#             ``__init__()`` function.

#         Returns
#         -------
#         ResourceInfo
#             The constructed class object.
#         """
#         d["srv_cfg"] = ServerConfiguration.from_dict(d["srv_cfg"])
#         return cls(**d)

#     def to_dict(self) -> Dict[str, Any]:
#         """
#         Serializes a ResourceInfo instance to a dictionary, writeable to a file
#         and parseable by ``from_dict()``.

#         Returns
#         -------
#         Dict[str, Any]
#             The ResourceInfo object as a dictionary.
#         """
#         d = self.__dict__
#         for k, v in d.items():
#             if v.__class__.__module__ != "builtins":
#                 d[k] = v.to_dict()
#         return d

#     @property
#     def daemon(self) -> Type[Daemon]:
#         """
#         Returns the object for the daemon in PyroLab referenced by 
#         ResourceInfo.

#         Returns
#         -------
#         Type[Daemon]
#             The class of the referenced Daemon.
#         """
#         mod = importlib.import_module(self.daemon_module)
#         obj: Daemon = getattr(mod, self.daemon_class)
#         return obj

#     def get_instr_info(self) -> InstrumentInfo:
#         """
#         Since ResourceInfo objects contain the registered_name of an Instrument,
#         it should correspond to an InstrumentInfo object in PyroLab's 
#         ``registry``.

#         Returns
#         -------
#         InstrumentInfo
#             The InstrumentInfo object this ResourceInfo references.
#         """
#         return registry.get(self.registered_name)

#     def activate(self) -> None:
#         """
#         Activates the Resource. When the manager loads all known resources,
#         this instance will be hosted.
#         """
#         self.active = True

#     def deactivate(self) -> None:
#         """
#         Deactivates the Resource. When the manager loads all known resources,
#         this instance will be skipped.
#         """
#         self.active = False


# class ResourceRunner(multiprocessing.Process):
#     """
#     A child process for running servers using Python's ``multiprocessing``.

#     Advantages of using a ResourceRunner include the fact that if a server
#     dies or hangs up, the entire program doesn't stall or need to be restarted,
#     just the process that contained the server. Thus errors can be handled 
#     and servers autonomously restarted and managed.

#     Other advantages should include speed; splitting servers across processors
#     means that resource-heavy instruments won't bog down adjacent instruments.

#     Parameters
#     ----------
#     info : ResourceInfo
#         The ResourceInfo dataclass that holds parameters necessary for 
#         constructing and running a server.
#     msg_queue : multiprocessing.Queue
#         A message queue. ResourceRunner only listens for when "None" is placed
#         in the queue, which is a sentinel value to shutdown the process.
#     """
#     def __init__(self, *args, info: ResourceInfo=None, 
#                  msg_queue: Queue=None, **kwargs) -> None:
#         super().__init__(*args, **kwargs)
#         self.info: ResourceInfo = info
#         self.msg_queue: Queue = msg_queue

#     def setup_daemon(self) -> Tuple[Daemon, URI]:
#         """
#         Locates and loads the Daemon class, adds Pyro's ``behavior``, and 
#         registers the hosted object with the Daemon.

#         Returns
#         -------
#         daemon, uri
#             The Daemon object and the URI for the hosted object, to be 
#             registered with the nameserver.
#         """
#         instr_info = self.info.get_instr_info()
#         cls = instr_info.get_class()
#         # SS = behavior(SS, instance_mode="single")
#         cls._pyroInstancing = (self.info.instance_mode, None)

#         daemon = self.info.daemon()
#         if instr_info.connect_params:
#             uri = daemon.register(cls, connect_params=instr_info.connect_params)
#         else:
#             uri = daemon.register(cls)

#         return daemon, uri

#     def kill_listener(self):
#         """
#         A callback listener; if the sentinel value ``None`` is placed in the
#         message queue, returns True signifying a shutdown signal has been
#         received.

#         This function is called by the Daemon's ``requestLoop()``.

#         Returns
#         -------
#         bool
#             True if shutdown signal received, False otherwise.
#         """
#         if not self.msg_queue.empty():
#             msg = self.msg_queue.get()
#             if msg is None:
#                 return False
#         return True

#     def run(self) -> None:
#         """
#         Creates and runs the child process.

#         When the kill signal is received, gracefully shuts down and removes
#         its registration from the nameserver.
#         """
#         name = multiprocessing.current_process().name
#         instr_info = self.info.get_instr_info()
#         print(f"Starting '{name}'")

#         daemon, uri = self.setup_daemon()

#         ns = locate_ns(self.info.ns_host, self.info.ns_port)
#         ns.register(instr_info.registered_name, uri, metadata=instr_info.metadata)
#         daemon.requestLoop(loopCondition=self.kill_listener)
#         ns.remove(instr_info.registered_name)
