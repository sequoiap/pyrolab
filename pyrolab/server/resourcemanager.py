# # -*- coding: utf-8 -*-
# #
# # Copyright © PyroLab Project Contributors
# # Licensed under the terms of the GNU GPLv3+ License
# # (see pyrolab/__init__.py for details)

# """
# Server Resource Manager
# -----------------------

# The server resource manager handles the putting up and taking down of Daemons
# for various instruments. To increase computer speed and processing 
# capabilities in cases where multiple instruments are hosted from the same
# computer, each instrument is created in its own Daemon using the 
# Python ``multiprocessing`` module.
# """

# import atexit
# import multiprocessing
# from multiprocessing.queues import Queue
# import threading
# import logging
# from typing import Dict, Union
# from pathlib import Path

# from yaml import dump, safe_load

# from pyrolab.server.configure import SERVER_DATA_DIR
# from pyrolab.server.resource import ResourceInfo, ResourceRunner


# log = logging.getLogger("pyrolab.server.resourcemanager")


# # TODO: Make this some sort of PyroLab configuration parameter.
# RESOURCE_MANAGER_AUTOSAVE = True
# # TODO: Make this some sort of PyroLab configuration parameter.
# RESOURCE_INFO_FILE = SERVER_DATA_DIR / "resource_manager_info.yaml"

# # TODO: Make this some sort of PyroLab configuration parameter.
# RM_AUTORELAUNCH = 15.0

# class ResourceManager:
#     def __init__(self) -> None:
#         self.infos: Dict[str, ResourceInfo] = {}
#         self.processes: Dict[str, ResourceRunner] = {}
#         self.messengers: Dict[str, Queue] = {}
#         self.AUTORELAUNCH: bool = True
#         self.checkup()

#     def update_host(self, host: str="localhost") -> None:
#         for info in self.infos.values():
#             info.srv_cfg['HOST'] = host
#         self.save()

#     def update_ns(self, ns_host: str="localhost", ns_port: int=9090) -> None:
#         for info in self.infos.values():
#             info.srv_cfg['NS_HOST'] = ns_host
#             info.srv_cfg['NS_PORT'] = ns_port
#         self.save()

#     def checkup(self) -> None:
#         log.debug("Checking up on all child processes.")
#         if self.AUTORELAUNCH:
#             self._timer = threading.Timer(RM_AUTORELAUNCH, self.checkup)
#             self._timer.setDaemon(True)
#             self._timer.start()
#         else:
#             log.info("AUTORELAUNCH deactivated")
#             log.debug("Timer cancelled")
#             self._timer.cancel()
#         for name, runner in self.processes.items():
#             if not runner.is_alive():
#                 log.info(f"Process '{name}' died, relaunching.")
#                 self.launch(name)
#         return True

#     def launch(self, name: str) -> None:
#         info = self.infos[name]
#         if info.active:
#             messenger = multiprocessing.Queue()
#             runner = ResourceRunner(info=info, msg_queue=messenger, daemon=True)
#             self.processes[info.registered_name] = runner
#             self.messengers[info.registered_name] = messenger
#             runner.start()
#         else:
#             log.info(f"Resource '{info.registered_name}' is deactivaed, not launching.")

#     def launch_all(self) -> bool:
#         for name, info in self.infos.items():
#             if info.active:
#                 self.launch(name)
#         log.info("AUTORELAUNCH activated")
#         self.AUTORELAUNCH = True
#         return True

#     def shutdown(self, name: str) -> None:
#         self.messengers[name].put(None)
#         del self.processes[name]
#         del self.messengers[name]

#     def shutdown_all(self) -> None:
#         self.AUTORELAUNCH = False
#         names = list(self.processes.keys())
#         for name in names:
#             self.shutdown(name)

#     def add(self, info: ResourceInfo, force=False) -> None:
#         if info.registered_name in self.infos and not force:
#             raise Exception(f"ResourceInfo '{info.registered_name}' already exists!")
#         else:
#             self.infos[info.registered_name] = info

#     def load(self, path: Union[str, Path]="") -> Union["ResourceManager", bool]:
#         """
#         Loads InstrumentInfo from a yaml file. Default file is the program's
#         internal data file, but a user file can be supplied.

#         Parameters
#         ----------
#         path : Union[str, Path], optional
#             The path to the registry file to use. If not provided, uses the
#             program's default data file.

#         Returns
#         -------
#             The Registry object is loading is successful, else False.
#         """
#         if path:
#             if type(path) is str:
#                 path = Path(path)
#         else:
#             path = RESOURCE_INFO_FILE
#         if path.exists():
#             self.infos = {}
#             with path.open('r') as fin:
#                 infos = safe_load(fin)
#                 for _, info in infos.items():
#                     obj = ResourceInfo.from_dict(info)
#                     self.infos[obj.registered_name] = obj
#             return self
#         return False

#     def save(self, path: Union[str, Path]="", update_file: bool=False) -> None:
#         """
#         Saves the current resources to file for persisting server 
#         configurations.

#         A path can be specified to create a new file with ResourceManager 
#         information. This is for inspection or development purposes. If
#         ``update_file`` is True, PyroLab can reference that file's location
#         each time it is started instead of using its default ProgramData file.
#         (TODO: this is not yet impmlemented.)

#         Parameters
#         ----------
#         path : Union[str, Path], optional
#             The location to save the resource info file to.
#         update_file : bool, optional
#             Force PyroLab to update it's default resource info file 
#             location. TODO: NotYetImplemented
#         """
#         if path:
#             if type(path) is str:
#                 path = Path(path)
#         else:
#             path = RESOURCE_INFO_FILE
#         items = {name: info.to_dict() for name, info in self.infos.items()}
#         with path.open('w') as fout:
#             fout.write(dump(items))
        
#         if update_file:
#             raise NotImplementedError


# manager = ResourceManager()
# manager.load()

# @atexit.register
# def save_registry_on_exit():
#     if RESOURCE_MANAGER_AUTOSAVE:
#         manager.save()
