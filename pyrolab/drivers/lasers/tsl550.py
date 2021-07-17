# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Santec Tunable Semiconductor Laser 550 (TSL550)
-----------------------------------------------

Driver for the Santec TSL-550 Tunable Laser.

Contributors
 * Wesley Cassidy (https://github.com/wecassidy)
 * Sequoia Ploeg (https://github.com/sequoiap)

Original repo: https://github.com/wecassidy/TSL550

Note
----
The Santec TSL-550 drivers, which among
other things make the USB connection appear as a serial port, must be
installed.

Warning
-------
An unidentifiable bug results in the return value of some functions being the setting of the laser
BEFORE the update (instead of the commanded setting). To verify some value has been set to 
the commanded value, simply call its respective function a second time without any arguments.
"""

import sys
import time
import struct

import serial
from serial.tools import list_ports
from pyrolab.api import expose, behavior

from typing import Any, Dict, List

from pyrolab.drivers.lasers import Laser


@behavior(instance_mode="single")
@expose
class TSL550(Laser):
    """ A Santec TSL-550 laser.

    Lasers can only be accessed by their serial port address.

    Attributes
    ----------
    MINIMUM_WAVELENGTH : int
        The minimum wavelength of the TSL550, 1500, in nanometers.
    MAXIMUM_WAVELENGTH : int
        The maximum wavelength of the TSL550, 1630, in nanometers.
    """

    # continuous, two-way, external trigger, constant frequency interval
    SWEEP_MODE_MAP = {
        (True, False, False, False): 1,
        (True, True, False, False): 2,
        (False, False, False, False): 3,
        (False, True, False, False): 4,
        (False, False, False, True): 5,
        (False, True, False, True): 6,
        (True, False, True, False): 7,
        (True, True, True, False): 8,
        (False, False, True, False): 9,
        (False, True, True, False): 10,
        (False, False, True, True): 11,
        (False, True, True, True): 12
    }
    SWEEP_MODE_MAP_REV = {num: settings for settings, num in SWEEP_MODE_MAP.items()}

    # Sweep mode statuses
    SWEEP_OFF = 0
    SWEEP_RUNNING = 1
    SWEEP_PAUSED = 2
    SWEEP_TRIGGER_WAIT = 3
    SWEEP_JUMP = 4

    MINIMUM_WAVELENGTH = 1500
    MAXIMUM_WAVELENGTH = 1630

    activated = False

    @staticmethod
    def detect_devices(self) -> List[Dict[str, Any]]:
        """
        Finds and returns all information needed to connect to the device.

        Returns
        -------
        List[Dict[str, Any]]
            Each item in the list contains a dictionary for a unique laser.
            A dictionary from the list can be passed to ``connect()`` to
            connect to the laser. If no device is detected, an empty list 
            is returned.
        """
        device_info = []
        for port in list_ports.comports():
            if port.manufacturer == "Santec Corp.":
                location = port.device
                device_info.append({"address": location})

        return device_info


    def connect(self, address="", baudrate=9600, terminator="\r", timeout=100, query_delay=0.05) -> bool:
        """
        Connects to and initializes the laser. All parameters are keyword arguments.

        Parameters
        ----------
        address : str
            Address is the serial port the laser is connected to (default "").
        baudrate : int, optional
            Baudrate can be set on the device (default 9600).
        terminator : str, optional
            The string that marks the end of a command (default "\\\\r").
        timeout : int, optional
            The number of seconds to timeout after no response (default 100).

        Returns
        -------
        bool
            True if the device has been successfuly connected to. False otherwise.
        """
        self.activated = True
        self.device = serial.Serial(address, baudrate=baudrate, timeout=timeout)
        self.device.flushInput()
        self.device.flushOutput()
        self.query_delay = query_delay

        # Python 3: convert to bytes
        self.terminator = terminator.encode("ASCII")

        # Make sure the shutter is on
        #self.is_on = True
        self.query("SU")
        shutter = self.close_shutter()

        # Set power management to auto
        self.power_control = "auto"
        self.power_auto()

        # Set sweep mode to continuous, two-way, trigger off
        self.sweep_set_mode()

        return self.device.is_open

    def close(self):
        """
        Closes the serial connection to the laser.
        """
        if(self.activated == False):
            raise Exception("Device is locked")

        self.device.close()

    def write(self, command):
        """
        Write a command to the TSL550.

        Parameters
        ----------
        command : str
            The command to be written as a string. This function automatically
            encodes it using the ASCII standard.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        # Convert to bytes (Python 3)
        command = command.encode("ASCII")

        # Write the command
        self.device.write(command + self.terminator)

    def read(self):
        """
        Reads a response from the TSL550.

        Returns
        -------
        str
            The response from the laser as a string.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        # Read response
        response = ""
        in_byte = self.device.read()
        while in_byte != self.terminator:
            response += in_byte.decode("ASCII")
            in_byte = self.device.read()

        return response

    def query(self, command, query_delay=None):
        """
        Write a command to the TSL550. Returns the response (if any).

        Parameters
        ----------
        command : str
            The VISA command to send to the device.
        query_delay : float, optional
            The query delay to use between write and read operations. If None, 
            defaults to ``self.query_delay`` (can be set in ``__init__``). 
            Default is None.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.write(command)
        time.sleep(query_delay if query_delay is not None else self.query_delay)
        response = self.read()

        return response

    def _set_var(self, name, precision, val):
        """
        Generic function to set a floating-point variable on the
        laser, or return the current value.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        if val is not None:
            command = ("{}{:."+str(precision)+"f}").format(name, val)
        else:
            command = name

        response = self.query(command)
        return float(response)

    def ident(self):
        """
        Query the device to identify itself.

        Returns
        -------
        str
            SANTEC,TSL-550,########,****.****
            # field = serial number of the device
            * field = firmware version

        Examples
        --------
        >>> laser.ident()
        'SANTEC,TSL-550,06020001,0001.0000'
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self.query('*IDN?')

    def on(self):
        """
        Turns on the laser diode.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.is_on = True
        self.query("LO")

    def off(self):
        """
        Turns off the laser diode.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.is_on = False
        self.query("LF")

    def wavelength(self, val=None):
        """
        Sets the output wavelength, and returns nothing. If a value is not 
        specified, returns the currently set wavelength.

        Parameters
        ----------
        val : float, optional
            The wavelength the laser will be set to in nanometers.
            Step: 0.0001 (nm)

        Returns
        -------
        float
            The currently set wavelength, in nanometers.

        Examples
        --------
        You can get the current wavelength by calling without arguments.

        >>> laser.wavelength()
        1630.0

        The following sets the output wavelength to 1560.123 nanometers.

        >>> laser.wavelength(1560.123)
        """
        if(self.activated == False):
            raise Exception("Device is locked")

        if val is not None:
            self._set_var("WA", 4, val)
            return
        else:
            return self._set_var("WA", 4, val)

    def frequency(self, val=None):
        """
        Tune the laser to a new frequency, and will not return a value. 
        If a value is not specified, returns the currently set frequency.

        Parameters
        ----------
        val : float, optional
            The frequency to set the laser to in terahertz.
            Step: 0.00001 (THz)

        Returns
        -------
        float
            The currently set frequency, in terahertz.

        Examples
        --------
        >>> laser.frequency()
        183.92175
        >>> laser.frequency(192.0000)
        """
        if(self.activated == False):
            raise Exception("Device is locked")

        if val is not None:
            self._set_var("FQ", 5, val)
            return
        else:
            return self._set_var("FQ", 5, val)

    def power_mW(self, val=None):
        """
        Set the output optical power in milliwatts. If a value is not
        specified, returns the current output power.

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in milliwatts.
            Range: 0.02 - 20 (mW, typical)
            Minimum step: 0.01 (mW)

        Returns
        -------
        float
            The currently set power, in milliwatts.

        Examples
        --------
        >>> laser.power_mW()
        2e-05
        >>> laser.power_mW(10)
        2e-05 # Bug returns the last set power
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("LP", 2, val)

    def power_dBm(self, val=None):
        """
        Set the output optical power in decibel-milliwatts (dBm). If a value
        is not specified, returns the current power.

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in decibel-milliwatts.
            Range: -17 to +13 (dBm, typical)
            Minimum step: 0.01 (dB)

        Returns
        -------
        float
            The currently set power in decibel-milliwatts.

        Examples
        --------
        You can get the current power by calling without arguments.
        The below code indicates the currently output power is -40 dBm.

        >>> laser.power_dBm()
        -040.000

        The following sets the output optical power to +3 dBm.

        >>> laser.power_dBm(3)
        -040.000 # Bug returns the last set power
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("OP", 2, val)

    def power_att(self, val=None):
        """

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in decibels.
            Range: 0 to +30 (dB)
            Minimum step: 0.01 (dB)

        Returns
        -------
        float
            The currently set power in decibel-milliwatts.

        Examples
        --------
        You can get the current power by calling without arguments.
        The below code indicates the currently output power is -40 dBm.

        >>> laser.power_dBm()
        -040.000

        The following sets the output optical power to +3 dBm.

        >>> laser.power_dBm(3)
        -040.000 # Bug returns the last set power
        """
        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("AT", 2, val)

    def power_auto(self):
        """
        Turn on automatic power control.

        Warning
        -------
        Shutter must be open to switch power modes.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.power_control = "auto"
        self.query("AF")

    def power_manual(self):
        """
        Turn on manual power control.
        
        Warning
        -------
        Shutter must be open to switch power modes.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.power_control = "manual"
        return self.query("AO")

    def sweep_wavelength(self, start, stop, duration, number=1,
                         delay=0, continuous=True, step_size=1,
                         twoway=False, trigger=False):
        # TODO: Test and document.
        r"""
        Conduct a sweep between two wavelengths. This method goes from
        the start wavelength to the stop wavelength (units:
        manometres). The sweep is then repeated the number of times
        set in the number parameter.

        If delay (units: seconds) is specified, there is a pause of
        that duration between each sweep.

        If the parameter continuous is False, then the sweep will be
        conducted in steps of fixed size as set by the step_size
        parameter (units: nanometres).

        In continuous mode, the duration is interpreted as the time
        for one sweep. In stepwise mode, it is used as the dwell time
        for each step. In both cases it has units of seconds and
        should be specified in 100 microsecond intervals.

        If the twoway parameter is True then one sweep is considered
        to be going from the start wavelength to the stop wavelength
        and then back to the start; if it is False then one sweep
        consists only of going from the start to the top, and the
        laser will simply jump back to the start wavelength at the
        start of the next sweep.

        If the trigger parameter is False then the sweep will execute
        immediately. If it is true, the laser will wait for an
        external trigger before starting.

        To illustrate the different sweep modes:

            Continuous, one-way    Continuous, two-way
                /   /                  /\    /\      <-- stop frequency
               /   /                  /  \  /  \
              /   /                  /    \/    \    <-- start frequency
              <-> duration           <----> duration

            Stepwise, one-way      Stepwise, two-way
                    __|      __|              _||_        _||_      <-- stop frequency
                 __|      __|               _|    |_    _|    |_ } step size
              __|      __|               _|        |__|        |_  <-- start frequency
              <-> duration               <> duration

            Continuous, one-way, delay    Continuous, two-way, delay
                /     /                       /\       /\
               /     /                       /  \     /  \
              /  ___/                       /    \___/    \
                 <-> delay                        <-> delay
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        # Set start and end wavelengths
        self.sweep_start_wavelength(start)
        self.sweep_end_wavelength(stop)

        # Set timing
        self.sweep_delay(delay)
        if continuous: # Calculate speed
            speed = abs(stop - start) / duration

            if twoway: # Need to go twice as fast to go up then down in the same time
                speed *= 2

            self.sweep_speed(speed)
        else: # Interpret as time per step
            self.sweep_step_time(duration)

        self.sweep_set_mode(continuous=continuous, twoway=twoway,
                            trigger=trigger, const_freq_step=False)

        if not self.is_on: # Make sure the laser is on
            self.on()

        self.sweep_start(number)

    def sweep_frequency(self, start, stop, duration, number=1,
                        delay=0, continuous=True, step_size=1,
                        twoway=False, trigger=False):
        # TODO: Test and document.
        r"""
        Conduct a sweep between two frequencies. This method goes from
        the start frequency to the stop frequency (units: terahertz).
        The sweep is then repeated the number of times set in the
        number parameter.

        If delay (units: seconds) is specified, there is a pause of
        that duration between each sweep.

        If the parameter continuous is False, then the sweep will be
        conducted in steps of fixed size as set by the step_size
        parameter (units: terahertz).

        In continuous mode, the duration is interpreted as the time
        for one sweep. In stepwise mode, it is used as the dwell time
        for each step. In both cases it has units of seconds and
        should be specified in 100 microsecond intervals.

        If the twoway parameter is True then one sweep is considered
        to be going from the start frequency to the stop frequency and
        then back to the start; if it is False then one sweep consists
        only of going from the start to the top, and the laser will
        simply jump back to the start frequency at the start of the
        next sweep.

        If the trigger parameter is False then the sweep will execute
        immediately. If it is true, the laser will wait for an
        external trigger before starting.

        To illustrate the different sweep modes:

            Continuous, one-way    Continuous, two-way
                /   /                  /\    /\      <-- stop frequency
               /   /                  /  \  /  \
              /   /                  /    \/    \    <-- start frequency
              <-> duration           <----> duration

            Stepwise, one-way      Stepwise, two-way
                    __|      __|              _||_        _||_      <-- stop frequency
                 __|      __|               _|    |_    _|    |_ } step size
              __|      __|               _|        |__|        |_  <-- start frequency
              <-> duration               <> duration

            Continuous, one-way, delay    Continuous, two-way, delay
                /     /                       /\       /\
               /     /                       /  \     /  \
              /  ___/                       /    \___/    \
                 <-> delay                        <-> delay
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        # Set start and end frequencies
        self.sweep_start_frequency(start)
        self.sweep_end_frequency(stop)

        # Set timing
        self.sweep_delay(delay)
        if continuous: # Calculate speed
            speed = abs(3e8/stop - 3e8/start) / duration # Convert to wavelength

            if twoway: # Need to go twice as fast to go up then down in the same time
                speed *= 2

            self.sweep_speed(speed)
        else: # Interpret as time per step
            self.sweep_step_time(duration)

        self.sweep_set_mode(continuous=continuous, twoway=twoway,
                            trigger=trigger, const_freq_step=not continuous)

        if not self.is_on: # Make sure the laser is on
            self.on()

        self.sweep_start(number)

    def sweep_start(self, num=1):
        """
        Sweep between two wavelengths one or more times. Set the start
        and end wavelengths with
        sweep_(start|end)_(wavelength|frequency), and the sweep
        operation mode with sweep_set_mode.

        Parameters
        ----------
        num : int, optional
            The number of times to perform the sweep (default is 1).
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.query("SZ{:d}".format(num)) # Set number of sweeps
        self.query("SG") # Start sweeping

    def sweep_pause(self):
        """
        Pause the sweep.  When a fast sweep speed is set, pause will 
        not function. Use `sweep_resume()` to resume.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.query("SP")

    def sweep_resume(self):
        """
        Resume a paused sweep.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.query("SR")

    def sweep_stop(self, immediate=True):
        """
        Prematurely quit a sweep. 

        Parameters
        ----------
        immediate : bool
            If `True`, the sweep will stop at once. If `False` and the
            sweep is continuous, the sweep will stop once it reaches
            the end wavelength of its current sweep (the default is `True`).
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        if immediate:
            self.sweep_pause()

        self.query("SQ")

    def sweep_status(self):
        """
        Gets the current condition of the sweeping function. 
        
        Returns
        -------
        status : int
            The status code correspond to the following:
            0: Stop (`TSL550.SWEEP_OFF`)
            1: Executing (`TSL550.SWEEP_RUNNING`)
            2: Pause (`TSL550.SWEEP_PAUSED`)
            3: Awaiting Trigger (`TSL550.SWEEP_TRIGGER_WAIT`)
                This means that the sweep has been set to start on 
                an external trigger and that trigger has not yet 
                been received.
            4: Setting to sweep start wavelength (`TSL550.SWEEP_JUMP`)
                This means that the laser is transitioning between 
                the end of one sweep and the start of the next in 
                one-way sweep mode.

        Examples
        --------
        >>> laser.sweep_status()
        0
        >>> laser.sweep_status() == laser.SWEEP_OFF
        True
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return int(self.query("SK"))

    def sweep_set_mode(self, continuous=True, twoway=True, trigger=False, const_freq_step=False):
        r"""
        Set the mode of the sweep. Options:

        Parameters
        ----------
        continuous : bool, optional
            Continuous (`True`, default) or stepwise (`False`).
                /        _|
               /  vs   _|
              /      _|
        twoway : bool, optional
            Two-way (`True`, default) or one-directional with reset (`False`).
                /\        /   /
               /  \  vs  /   /
              /    \    /   /
        trigger : bool, optional
            Start on external trigger (defaults to `False`).
        const_freq_step : bool, optional
            Constant frequency interval, requires stepwise mode (defaults to `False`).

        Raises
        ------
        AttributeError
            If the sweep configuration is invalid.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        try:
            mode = TSL550.SWEEP_MODE_MAP[(continuous, twoway, trigger, const_freq_step)]
        except KeyError:
            raise AttributeError("Invalid sweep configuration.")

        self.query("SM{}".format(mode))

    def sweep_get_mode(self):
        """
        Return the current sweep configuration as a dictionary. See
        sweep_set_mode for what the parameters mean.

        Returns
        -------
        mode : dict
            A dictionary containing boolean values for the keys `continuous`,
            `twoway`, `trigger`, and `const_freq_step`.

        Examples
        --------
        >>> laser.sweep_get_mode()
        {'continuous': True, 'twoway': True, 'trigger': False, 'const_freq_step': False}
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        mode_num = int(self.query("SM"))
        mode_settings = TSL550.SWEEP_MODE_MAP_REV[mode_num]

        return {
            "continuous": mode_settings[0],
            "twoway": mode_settings[1],
            "trigger": mode_settings[2],
            "const_freq_step": mode_settings[3]
        }

    def sweep_speed(self, val=None):
        """
        Set the speed of the continuous sweep, in nm/s. If a new value
        is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The sweep speed of the laser, in nm/s.
            Range: 1.0 - 100 (nm/s)
            Step: 0.1 (nm/s)

        Returns
        -------
        float
            The sweep speed of the laser in nm/s.

        Examples
        --------
        >>> laser.sweep_speed()
        26.0
        >>> laser.sweep_speed(25)
        25.0
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("SN", 1, val)

    def sweep_step_wavelength(self, val=None):
        """
        Set the size of each step in the stepwise sweep. If a new
        value is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The step size in the stepwise sweep in nanometers.
            Range: 0.0001 - 160 (nm)
            Step: 0.0001 (nm)

        Returns
        -------
        float
            The set step size in a stepwise sweep in nm.

        Examples
        --------
        >>> laser.sweep_step_wavelength()
        1.0
        >>> laser.sweep_step_wavelength(2.2)
        2.2
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("WW", 4, val)

    def sweep_step_frequency(self, val=None):
        """
        Set the size of each step in the stepwise sweep when constant
        frequency intervals are enabled. If a new value is not
        provided, the current one will be returned. Units: THz

        Parameters
        ----------
        val : float, optional
            The step size of each step in the stepwise sweep in terahertz.
            Range: 0.00002 - 19.76219 (THz)
            Step: 0.00001 (THz)

        Returns
        -------
        float
            The set step size in THz.

        Examples
        --------
        >>> laser.sweep_step_frequency()
        0.1
        >>> laser.sweep_step_frequency(0.24)
        0.24
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("WF", 5, val)

    def sweep_step_time(self, val=None):
        """
        Set the duration of each step in the stepwise sweep. If a new
        value is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The duration of each step in seconds.
            Range: 0 - 999.9 (s)
            Step: 0.1 (s)

        Returns
        -------
        float
            The set duration of each step in seconds.

        Examples
        --------
        >>> laser.sweep_step_time()
        0.5
        >>> laser.sweep_step_time(0.8)
        0.8
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("SB", 1, val)

    def sweep_delay(self, val=None):
        """
        Set the time between consecutive sweeps in continuous mode. If
        a new value is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The delay between sweeps in seconds.
            Range: 0 - 999.9 (s)
            Step: 0.1 (s)

        Returns
        -------
        float
            The set delay between sweeps in seconds.

        Examples
        --------
        >>> laser.sweep_delay()
        0.0
        >>> laser.sweep_delay(1.5)
        1.5
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("SA", 1, val)

    def sweep_start_wavelength(self, val=None):
        """
        Sets the start wavelength of a sweep.

        Sets the starting wavelength for subsequent sweeps. If no value
        is specified, the current starting wavelength setting is returned.

        Parameters
        ----------
        val : float, optional
            The starting value of the wavelength sweep in nanometers.
            Step: 0.0001 (nm)

        Returns
        -------
        float
            The current sweep start wavelength in nm.

        Examples
        --------
        >>> laser.sweep_start_wavelength()
        1500.0
        >>> laser.sweep_start_wavelength(1545)
        1545.0
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("SS", 4, val)

    def sweep_start_frequency(self, val=None):
        """
        Sets the start frequency of a sweep.

        Sets the starting frequency for subsequent sweeps. If no value
        is specified, the current starting frequency setting is returned.

        Parameters
        ----------
        val : float, optional
            The starting value of the frequency sweep in terahertz.
            Step: 0.00001 (THz)

        Returns
        -------
        float
            The current sweep start frequency in THz.

        Examples
        --------
        >>> laser.sweep_start_frequency()
        199.86164
        >>> laser.sweep_start_frequency(196)
        195.99999
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("FS", 5, val)

    def sweep_end_wavelength(self, val=None):
        """
        Sets the end wavelength of a sweep.

        Sets the ending wavelength for subsequent sweeps. If no value
        is specified, the current ending wavelength setting is returned.

        Parameters
        ----------
        val : float, optional
            The ending value of the wavelength sweep in nanometers.
            Step: 0.0001 (nm)

        Returns
        -------
        float
            The current sweep end wavelength in nm.

        Examples
        --------
        >>> laser.sweep_end_wavelength()
        1630.0
        >>> laser.sweep_end_wavelength(1618)
        1618.0
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("SE", 4, val)

    def sweep_end_frequency(self, val=None):
        """
        Sets the end frequency of a sweep.

        Sets the ending frequency for subsequent sweeps. If no value
        is specified, the current ending frequency setting is returned.

        Parameters
        ----------
        val : float, optional
            The ending value of the frequency sweep in THz.
            Step: 0.00001 (THz)

        Returns
        -------
        float
            The current sweep end frequency in THz.

        Examples
        --------
        >>> laser.sweep_end_frequency()
        183.92175
        >>> laser.sweep_end_frequency(185.5447)
        185.5447
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("FF", 5, val)

    def open_shutter(self):
        """
        Opens the laser's shutter.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self.query("SO")

    def close_shutter(self):
        """
        Closes the laser's shutter.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self.query("SC")

    def trigger_enable_output(self):
        """
        Enables the external trigger signal input.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.query("TRE")

    def trigger_disable_output(self):
        """
        Disables the external trigger signal input.
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        self.query("TRD")

    def trigger_get_mode(self):
        """
        Reads out the currently set value for the timing of the 
        trigger signal output.

        Returns
        -------
        mode : str
            A string representing the mode for the trigger signal 
            output timing.
            0: "None"
            1: "Stop"
            2: "Start"
            3: "Step"
        """

        if(self.activated == False):
            raise Exception("Device is locked")
        
        current_state = self.query("TM")
        if current_state == 0:
            return "None"
        elif current_state == 1:
            return "Stop"
        elif current_state == 2:
            return "Start"
        elif current_state == 3:
            return "Step"

    def trigger_set_mode(self,val=None):
        """
        Sets the trigger mode.

        Parameters
        ----------
        val : str, opt
            One of: "None", "Stop", "Start", "Step".
        
        Returns
        -------
        str
            The final mode. "Stop", "Start", or "Step"
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        mode = 0
        if val == "None" or val == None:
            mode = 0
        elif val == "Stop":
            mode = 1
        elif val == "Start":
            mode = 2
        elif val == "Step":
            mode = 3
        else:
            raise ValueError("Invalide output trigger mode supplied. Choose from None, Stop, Start, and Step.")
        current_state = int(self.query("TM{}".format(mode)))
        if current_state == 1:
            return "Stop"
        elif current_state == 2:
            return "Start"
        elif current_state == 3:
            return "Step"

    def trigger_set_step(self, step=None):
        """
        Sets (or returns) the interval of the trigger signal output.

        Parameters
        ----------
        step : float
            The interval of the trigger signal output, in nanometers.
            Range: 0.0001 - 160 (nm)
            Step: 0.0001 (nm)

        Returns
        -------
        val : float
            The currently set value (returned both on set and on read).

        Examples
        --------
        >>> laser.trigger_set_step()
        0.012
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return self._set_var("TW", 4, val=step)


    def wavelength_logging_number(self):
        """
        Returns the number of wavelength points stored in the wavelength
        logging feature.

        Returns
        -------
        int
            A value between 0 and 65535, the number of recorded data points.

        Examples
        --------
        >>> laser.wavelength_logging_number()
        5001
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        return int(self.query("TN"))

    def wavelength_logging(self):
        """
        Creates a list of all the wavelength points logged into the laser's
        buffer. Assumes that all the correct sweep and triggering protocol
        are met (see manual page 6-5).

        Returns
        -------
        points : list
            A Python list of length `laser.wavelength_logging_number()`. Each
            item in the list is represented in nanometers.

        Examples
        --------
        >>> laser.wavelength_logging_number()
        417
        >>> wl = laser.wavelength_logging()
        >>> len(wl)
        417
        >>> type(wl)
        <class 'list'>
        >>> wl[0]
        1675.0276
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        # stop laser from outputting
        self.query("SU")

        # First, get the number of wavelength points
        num_points = self.wavelength_logging_number()

        # Preallocate arrays
        wavelength_points = []

        # Now petition the laser for the wavelength points
        self.write("TA")
        time.sleep(0.1)

        # Iterate through wavelength points
        for nWave in range(int(num_points)):
            while True:
                try:
                    in_byte = self.device.read(4)
                    current_wavelength = float(struct.unpack(">I", in_byte)[0]) / 1e4
                    break
                except:
                    print('Failed to read in wavelength data.')
                    pass

            wavelength_points.append(current_wavelength)

        # stop laser from outputting
        self.query("SU")
        return wavelength_points

    def status(self):
        """
        Query the status of the laser and print its results.

        Returns
        -------
        code : str
            A status code for the status of the laser. It is a 7-character 
            string status comprising a code and 6 digits (with positions represented
            as '-654321'), interpreted as follows:

            Code [-/none]: Laser diode (LD) status
                '-': ON
                none: OFF
            6th digit [0/1]: Coherence control
                0: OFF
                1: ON
            5th digit [0/1]: Fine-tuning
                0: OFF
                1: ON
            4th digit [0-5]: Control mode of output power, attenuator, and power
                monitor range, according to the following table:
                Value | Power control | Attenuator control | Power monitor range control
                0 | Auto | Hold | Auto
                1 | Manual | Hold (Manual) | Auto
                2 | Auto | Auto | Auto
                4 | Auto | Hold | Hold
                5 | Manual | Hold (Manual) | Hold
            3rd digit [0/1]: Laser diode temperature error
                0: No error
                1: Error occurred
            2nd digit [0/1]: Laser diode current limit error
                0: No error
                1: Error occurred
            1st digit [0-7]: Operation status
                0: Operation is completed
                1: Wavelength is tuning
                2: Laser diode current is setting (LD is on state and power control is Auto)
                3: Wavelength is tuning and LD current is setting
                4: Attenuator is setting
                5: Wavelength is setting and attenuator is setting
                6: LD current is setting and attenuator is setting
                7: Wavelength is tuning, LD current is setting, and attenuator is setting

        The following example shows the laser as on and all operations as complete.

        Examples
        --------
        >>> laser.print_status()
        '-011000'
        """

        if(self.activated == False):
            raise Exception("Device is locked")

        status = self.query("SU")

        # Check if LD is on
        self.is_on = True if int(status) < 0 else False

        code = {    '-' : "'-': ON\n",
                    ' ' : "none: OFF\n"
        }
        digit_6 = { '0' : "Coherence control: OFF\n",
                    '1' : "Coherence control: ON\n"
        }
        digit_5 = { '0' : "Fine-tuning: OFF\n",
                    '1' : "Fine-tuning: ON\n"
        }
        digit_4 = { '0' : "Power Control: Auto\nAttenuator Control: Hold\nPower Monitor Range Control: Auto\n",
                    '1' : "Power Control: Manual\nAttenuator Control: Hold (Manual)\nPower Monitor Range Control: Auto\n",
                    '2' : "Power Control: Auto\nAttenuator Control: Auto\nPower Monitor Range Control: Auto\n",
                    '3' : "4th digit is not specified for a value of 3\n",
                    '4' : "Power Control: Auto\nAttenuator Control: Hold\nPower Monitor Range Control: Hold\n",
                    '5' : "Power Control: Manual\nAttenuator Control: Hold (Manual)\nPower Monitor Range Control: Hold\n",
        }
        digit_3 = { '0' : "Laser diode temperature error: No error\n",
                    '1' : "Laser diode temperature error: Error occurred\n",
        }
        digit_2 = { '0' : "Laser diode current limit error: No error\n",
                    '1' : "Laser diode current limit error: Error occurred\n"
        }
        digit_1 = { '0' : "Operation status: Operation is completed\n",
                    '1' : "Operation status: Wavelength is tuning\n",
                    '2' : "Operation status: Laser diode current is setting (LD is on state and power control is Auto)\n",
                    '3' : "Operation status: Wavelength is tuning and LD current is setting\n",
                    '4' : "Operation status: Attenuator is setting\n",
                    '5' : "Operation status: Wavelength is setting and attenuator is setting\n",
                    '6' : "Operation status: LD current is setting and attenuator is setting\n",
                    '7' : "Operation status: Wavelength is tuning, LD current is setting, and attenuator is setting\n"
        }
        output = status + code[status[0]] + digit_6[status[1]] \
            + digit_5[status[2]] + digit_4[status[3]] + digit_3[status[4]] \
            + digit_2[status[5]] + digit_1[status[6]]
        return output
