# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
API
---

A single module that centralizes the most frequently used objects from PyroLab.
"""

from Pyro5.core import locate_ns
from Pyro5.client import Proxy

from pyrolab.nameserver import start_ns_loop, start_ns, ns_profile, NameserverConfiguration
from pyrolab.server.server import Daemon, LockableDaemon
from pyrolab.server import srv_profile, ServerConfiguration
from pyrolab.server import expose, behavior, oneway, serve


__all__ = [
    "locate_ns", 
    "Proxy",
    "Daemon",
    "LockableDaemon",
    "expose",
    "behavior",
    "oneway",
    "serve",
    "start_ns_loop",
    "start_ns",
]
