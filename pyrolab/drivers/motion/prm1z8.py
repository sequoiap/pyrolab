# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PRM1Z8
------

Submodule containing drivers for the ThorLabs PRM1Z8 rotational stage.

Contributors
 * Benjamin Arnesen (https://github.com/BenA8)  
 * Christian Carver (https://github.com/cjcarver)
"""

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.kdc101 import KDC101, HomingMixin
from pyrolab.api import expose, behavior


@behavior(instance_mode="single")
@expose
class PRM1Z8(Motion, KDC101, HomingMixin):
    """
    A PRM1Z8 precision motorized rotation stage controlled by a KCube DC Servo 
    motor.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    home : bool
        True tells the device to home when initializing
    """
    def __init__(self, serialno: str, polling=200, home=False):
        super().__init__(serialno, polling, home)


    