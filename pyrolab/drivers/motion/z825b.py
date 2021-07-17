# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Z825B
-----

Submodule containing drivers for the ThorLabs Z825B linear stage.

Contributors
 * Benjamin Arnesen (https://github.com/BenA8)  
 * Christian Carver (https://github.com/cjcarver)
"""
from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.kdc101 import KDC101, HomingMixin
from pyrolab.api import expose, behavior


@behavior(instance_mode="single")
@expose
class Z825B(Motion, KDC101, HomingMixin):
    """
    A Z825B motorized linear actuator controlled by a KCube DC Servo motor. 

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    """
    def __init__(self, serialno, polling=200, home=False):
        super().__init__(serialno, polling, home)
