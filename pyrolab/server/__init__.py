# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Note that ``srv_profile`` is a global profile object and is intended to be a 
Singleton.
"""

from Pyro5.api import expose, behavior, oneway, serve

from .configure import srv_profile, ServerConfiguration
from .configure import SERVER_CONFIG_DIR, SERVER_DATA_DIR
# from .server import Daemon, LockableDaemon
# from .registry import registry

__all__ = [
    "SERVER_CONFIG_DIR",
    "SERVER_DATA_DIR",
    "srv_profile",
    "ServerConfiguration",
    # "Daemon",
    # "LockableDaemon",
    "expose", 
    "behavior", 
    "oneway", 
    "serve",
    # "registry"
]
