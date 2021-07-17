# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Sample Service
--------------

This file implements some simple, sample services for testing whether a server
is working properly.
"""

import time
from typing import Union

from pyrolab.api import expose, behavior
from pyrolab.drivers import Instrument


Number = Union[int, float]


@expose
class SampleService:
    def __init__(self):
        pass

    def close(self):
        pass

    def echo(self, message: str) -> str:
        """
        Echoes back as the response the exact message as received with
        "SERVER RECEIVED: " prepended to the message.

        Parameters
        ----------
        message : str
            The message to be echoed by the server.
        
        Returns
        -------
        resp : str
            The message to be echoed, prepended with "SERVER RECEIVED: ".
        """
        return "SERVER RECEIVED: " + message

    def delayed_echo(self, message: str, seconds: int) -> str:
        """
        Echoes back as the response the exact message as received with
        "SERVER RECEIVED: " prepended to the message after delaying by the
        specified number of seconds. 

        This function demonstrates that the connection does not die out even
        for long running requests.

        Parameters
        ----------
        message : str
            The message to be echoed by the server.
        seconds : int
            The number of seconds the server should wait before responding.
        
        Returns
        -------
        resp : str
            The message to be echoed, prepended with "SERVER RECEIVED: ".
        """
        time.sleep(seconds)
        return "SERVER RECEIVED: " + message

    def whoami(self):
        """
        Returns the object id of the instance that handled the request.

        Returns
        -------
        resp : str
            The object id of the handling instance.
        """
        return "OBJECT ID: " + str(id(self))

    def add(self, *a: Number) -> Number:
        """
        Adds an unconstrained number of arguments together.
        """
        return sum(a)

    def subtract(self, a: Number, b: Number) -> Number:
        """
        Subtracts the second parameter from the first.
        """
        return a - b

    def multiply(self, *vals: Number) -> Number:
        """
        Multiplies an unconstrained number of arguments together.
        """
        final = 1
        for val in vals:
            final = final * val
        return final

    def divide(self, num: Number, den: Number) -> Number:
        """
        Divides the first argument by the second.
        """
        return num / den


@behavior(instance_mode="single")
@expose
class SampleAutoconnectInstrument(Instrument):
    def __init__(self) -> None:
        self.connected = False

    def close(self):
        pass

    def connect(self, address="localhost", port=9090):
        if address != "0.0.0.0":
            raise Exception("This test method requires address to be '0.0.0.0'.")
        if port == 9090:
            raise Exception("This test method requires the port to not be the default of 9090.")
        self.connected = True
        return True

    def do_something(self):
        if not self.connected:
            raise Exception("This object cannot do work until connection is made.")
        return True

    def whoami(self):
        """
        Returns the object id of the instance that handled the request.

        Returns
        -------
        resp : str
            The object id of the handling instance.
        """
        return "OBJECT ID: " + str(id(self))
