# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Rohde & Schwarz Digital Oscilloscopes
-------------------------------------

Submodule containing drivers for each supported laser type.

As stated in the manual (see docs/RTO_UserManaul_en_11.pdf), the following
scopes should be supported:

This manual describes the following R&S®RTO models with firmware version 3.70:
   - R&S®RTO2002 (1329.7002K02)
   - R&S®RTO2004 (1329.7002K04)
   - R&S®RTO2012 (1329.7002K12)
   - R&S®RTO2014 (1329.7002K14)
   - R&S®RTO1024 (1316.1000K24)
   - R&S®RTO2022 (1329.7002K22)
   - R&S®RTO2024 (1329.7002K24)
   - R&S®RTO2032 (1329.7002K32)
   - R&S®RTO2034 (1329.7002K34)
   - R&S®RTO2044 (1329.7002K44)
   - R&S®RTO2064 (1329.7002K64)
   - R&S®RTO1002 (1316.1000K02)
   - R&S®RTO1004 (1316.1000K04)
   - R&S®RTO1012 (1316.1000K12)
   - R&S®RTO1014 (1316.1000K14)
   - R&S®RTO1022 (1316.1000K22)
   - R&S®RTO1044 (1316.1000K44)

If you don't have the NI VISA implementation installed on your computer, be 
sure to install the separate dependency ``pyvisa-py``, which is not included
with PyroLab. NI VISA is available for Mac, Windows, and Linux.

Common Issues
=============
1. Note that if a trigger is set and you try to acquire data but end up with
a timeout warning, it's possible that the acquisition never began because the
trigger level was never reached. The scope will still be waiting to begin
acquisition, but you'll be left without data and with a bad connection.
"""

import time

import deprecation #should we take this out too?
import pyvisa as visa

from pyrolab import __version__
from pyrolab.drivers.scopes import Scope, VISAResourceExtentions


class RTO(Scope):
    """
    Simple network controller class for R&S RTO oscilloscopes.


    """
    
    @staticmethod #How is this function supposed to be implemented? How are we supposed to know what the addresses are?
    def detect_devices(addresses):
        """
        Takes a list of IP addreses and returns them in the formate required
        to connect to the device.

        Parameters
        ----------
        addresses : list of str
            Any IP addresses to the scopes to be connected to

        Returns
        -------
        List[Dict[str, Any]]
            Each item in the list contains a dictionary for a unique laser.
            A dictionary from the list can be passed to ``connect()`` to
            connect to the laser. If no device is detected, an empty list 
            is returned.
        """
        device_info = []
        for address in addresses:
            device_info.append({"address": address})
        
        return device_info

        
    
    def connect(self, address="", interface="TCPIP", protocol="hislip", timeout=1e3) -> bool:
        """
        Connects to and initializes the R&S RTO oscilloscope.
        All parameters are keyword arguments.

        Parameters
        ----------
        address : str, optional
            The IP address of the instrument. Default is "".
        interface : str, optional
            The interface to use to connect to the instrument. May be one
            of "TCPIP", "GPIB", "ASRL", etc. Default is "TCPIP".
        protocol : str, optional
            The protocol to use for the LAN connection. Can be "INSTR"
            or "hislip". Default is "hislip".
        timeout : int, optional
            The device response timeout in milliseconds. 
            Default is 1 millisecond. Pass `None` for infinite timeout.
        """
        
        rm = visa.ResourceManager()
        self.device = rm.open_resource("{}::{}::{}".format(interface, address, protocol))
        self.device.timeout = timeout
        self.write_termination = ''
        self.device.ext_clear_status()
        
        self.write('*RST;*CLS')
        self.write('SYST:DISP:UPD ON')
        self.device.ext_error_checking()

        return True

    #not entirely sure if this is what should be happening. Should this function just do nothing?
    def close(self):
        #should only need to call this on two channels, becuase the filter applies to two channels at a time
        for channel in range(1,5):
            self.deact_filter(channel)
        
        self.device.before_close()
        self.device.close()

    @property
    def timeout(self):
        return self.device.timeout

    @timeout.setter
    def timeout(self, ms):
        self.device.timeout = ms

    def query(self, message, delay=None):
        """
        A combination of :py:func:`write(message)` and :py:func:`read()`.

        Parameters
        ----------
        message : str
            The message to send.
        delay : float, optional
            Delay in seconds between write and read operations. If None,
            defaults to `self.device.query_delay`.
        """
        return self.device.query(message, delay)

    def write(self, message, termination=None, encoding=None):
        """
        Writes a message to the scope.

        Parameters
        ----------
        message : str
            The message to send.
        termination : str, optional
            Alternative character termination to use. If None, the value 
            of write_termination is used. Defaults to None.
        encoding : str, optional
            Alternative encoding to use to turn str into bytes. If None, 
            the value of encoding is used. Defaults to None.
        """
        self.device.write(message, termination, encoding)

    def write_block(self, message):
        """
        Writes a message to the scope, waits for it to complete, and checks for errors.

        Parameters
        ----------
        message : str
            The message to send.

        Notes
        -----
        This function is blocking.
        """
        self.write(message)
        self.wait_for_device()
        self.device.ext_error_checking()

    #Removed depricated function; I think it was supposed to be removed

    def wait_for_device(self):
        """
        Waits for the device until last action is complete.

        Notes
        -----
        This function is blocking.
        """
        res = self.device.query('*OPC?')
        time.sleep(0.1)
        return res

    def acquisition_settings(self, sample_rate, duration, force_realtime=False):
        """
        Sets the scope acquisition settings.

        The exact command this executes is:
        `'ACQ:POIN:AUTO RES;:ACQ:SRAT {};:TIM:RANG {}'`

        Parameters
        ----------
        sample_rate : float
            Sample rate of device.
        duration : float
            Length of acquisition in seconds.
        force_realtime : bool, optional
            Defaults to False.
        """
        short_command = 'ACQ:POIN:AUTO RES;:TIM:RANG {}'.format(duration)
        if force_realtime:
            self.write_block('ACQ:MODE RTIM')
        self.write_block(short_command)

    def set_channel(self, channel: int, state: str="ON", 
                    coupling: str="DCLimit", range: float=0.5, 
                    position: float=0, offset: float=0, invert: str="OFF"):
        """
        Configures a channel.

        Parameters
        ----------
        channel : int
            The channel number to be added.
        state : str, optional
            Switches the channel signal on or off. Acceptable values are ``ON``
            and ``OFF``. Default is ``ON`` (see ``CHANnel<m>:STATe``).
        coupling : str, optional
            Selects the connection of the indicated channel signal. Valid values are
            "DC" (direct connection with 50 ohm termination), "DCLimit" (direct connection 
            with 1M ohm termination), or "AC" (connection through DC capacitor).
            Default is DCLimit (see ``CHANnel<m>:COUPling``).
        range : float, optional
            Sets the voltage range across the 10 vertical divisions of the diagram
            in V/div. Default is 0.5 (see ``CHANnel<m>:RANGe``).
        position : float, optional
            Sets the vertical position of the indicated channel as a graphical value.
            Valid range is [-5, 5] in increments of 0.01 (units is "divisions").
            Default is 0 (see ``CHANnel<m>:POSition``).
        offset : float, optional
            The offset voltage is subtracted to correct an offset-affected signal. 
            The offset of a signal is determined and set by the autoset procedure.
            Default value is 0 (see ``CHANnel<m>:OFFSet``).
        invert : str, optional
            Turns the inversion of the signal amplitude on or off. To invert means 
            to reflect the voltage values of all signal components against the ground 
            level. If the inverted channel is the trigger source, the instrument 
            triggers on the inverted signal. Acceptable values are "ON" or "OFF".
            Default is "OFF" (see ``CHANnel<m>:INVert``).
        """
        cmd = 'CHAN{}:STAT {}; COUP {};RANG {};POS {};OFFS {}; INV {}'.format(
            channel, state, coupling, range, position, offset, invert
        )
        self.write_block(cmd)

    #Removed depricated function; I think it was supposed to be removed

    def __add_trigger(self,
        type,
        source,
        source_num,
        level,
        trigger_num = 1,
        mode = "NORM",
        settings: str = ""
    ):
        short_command = 'TRIG{}:MODE {};SOUR {};TYPE {};LEV{} {};'.format(
        trigger_num, mode, source, type, source_num, level
    )
        #Add a trigger.
        self.write_block(short_command + settings)

    def edge_trigger(self, channel: int, voltage: float) -> None:
        """
        Add an edge trigger to the specified channel.

        Parameters
        ----------
        channel : int
            The channel to configure as a trigger.
        voltage : float
            Voltage threshold for positive slope edge trigger.
        """
        #Todo: Edit to allow other trigger sources (ex. External Trigger).
        self.__add_trigger(
            type = "EDGE",
            source = "CHAN{}".format(channel),
            source_num = channel,
            level = voltage,
            settings = "EDGE:SLOP POS"
        )

    def acquire(self, timeout: int=-1, run: str='single') -> None:
        """
        Asynchronous command that starts acquisition.

        Parameters
        ----------
        timeout : int
            The timeout to use for the given acquisition in milliseconds. The 
            default timeout is used if no timeout is given. The timeout is not
            permanently set; once the acquisition is complete, the original 
            timeout is kept for any other query/write command. For an infinite
            timeout, pass in None. If not specified, default timeout is the 
            default for `acquire()`.
        run : str
            Specifies the type of run. Allowable values are ``continuous`` 
            (starts the continuous acquisition), ``single`` (starts a defined
            number of acquisition cycles as set by 
            :py:func:``acquisition_settings()``), or ``stop`` (stops a 
            running acquisition). Default is ``single``.
        """        
        if run == "single":
            cmd = "SING"
        elif run == "continuous":
            cmd = "RUN"
        elif run == "stop":
            cmd = "STOP"
        else:
            raise ValueError("%s is not a valid argument" % run)

        if timeout != -1:
            default_timeout = self.timeout
            self.timeout = timeout
        
        self.write(cmd)

        if timeout != -1:
            self.timeout = default_timeout

    #Removed depricated function; I think it was supposed to be removed
    def set_timescale(self, time: float) -> None:
        """
        Sets the horizontal scale--the time per division on the x-axis--for all 
        channel and math waveforms.

        Parameters
        ----------
        time : float
            The time (in seconds) per division. Valid range is from 25e-12 to 
            10000 (RTO) | 5000 (RTE) in increments of 1e-12. (`*RST` value is 
            10e-9).
        """
        self.write(f'TIM:SCAL {str(time)}')

    def set_auto_measurement(self, measurement: int=1, source: str='C1W1', 
                             meastype: str='MAX') -> None:
        """
        Convenience function for setting default measurements. 
        
        Use if you haven't configured any of your own measurements.

        Parameters
        ----------
        measurement : int
            The oscope supports storing up to 8 measurements. Default is 1.
        channel : str
            The source to setup the measurement on. See page 1377 of the User
            Manual for valid sources. Common ones are of the format "C<m>W<n>",
            where <m> is the channel and <n> is the waveform (e.g., "C1W1", 
            which is the default).
        meastype : str
            The measurement type to associate with the measurement. See page 
            1381 of the User Manual for valid measurement types. Common ones
            are 'HIGH', 'LOW', 'AMPLitude', 'MAXimum', 'MINimum', 'MEAN'. 
            Default is 'MAX'.
        """
        self.write(f'MEAS{measurement}:SOUR {source}')
        # "MAX" will measure the max value in the current view window (Based on time base)
        self.write(f'MEAS{measurement}:MAIN {meastype}')
        self.write(f'MEAS{measurement} ON')

    def measure(self, measurement: int=1) -> float:
        """
        Takes the result of an automatic measurement as setup using 
        `set_auto_measurement()`.

        Parameters
        ----------
        channel : int
            The channel to take a single measurement on.
        measurement : int
            The measurement to take. Default is 1.

        Returns
        -------
        float
            The result of the automatic measurement.
        """
        return float(self.query(f'MEAS{measurement}:RES:ACT?'))

    def get_data(self, channel, form="ascii"):
        """
        Retrieves waveform data from the specified channel in the specified 
        data type.

        Parameters
        ----------
        channel : int
            The channel to retrieve data for.
        form : str, optional
            The data format used for the transmission of waveform data. 
            Allowable values are ``ascii``, ``real``, ``int8``, and ``int16``.
            Default is ``ascii``.

        See Also
        --------
        RTO User Manual, commands for ``FORMat[:DATA]`` and 
        ``CHANnel<m>[:WAVeform<n>]:DATA[:VALues]?``
        """
        if form == "ascii":
            fmt = "ASC"
        elif form == "real":
            fmt = "REAL,32"
        elif form == "int8":
            fmt = "INT,8"
        elif form == "int16":
            fmt = "INT,16"
        else:
            raise ValueError("unexpected value '%s' for argument 'form'." % form)

        cmd = 'FORM {};:CHAN{}:DATA?'.format(fmt, channel)
        
        if form == "ascii":
            return self.device.query_ascii_values(cmd)
        elif form == "real":
            return self.device.query_binary_values(cmd)
        else:
            return self.query(cmd)

    #Removed depricated function; I think it was supposed to be removed

    #Removed depricated function; I think it was supposed to be removed

    def screenshot(self, path):
        """
        Takes a screenshot of the scope and saves it to the specified path.

        Image format is PNG.

        Parameters
        ----------
        path : str
            The local path, including filename and extension, of where
            to save the file.
        """
        instrument_save_path = "'C:\\temp\\Last_Screenshot.png\'"
        self.write('HCOP:DEV:LANG PNG')
        self.write('MMEM:NAME {}'.format(instrument_save_path))
        self.write('HCOP:IMM')
        self.wait_for_device()
        self.device.ext_error_checking()
        self.device.ext_query_bin_data_to_file(
            'MMEM:DATA? {}'.format(instrument_save_path),
            str(path)
        )
        self.device.ext_error_checking()

    #Removed depricated function; I think it was supposed to be removed

    #what does 1..4 mean?
    def set_filter(self, channel, cutoff_freq):
        #descrbe
        self.write(f"CHAN{channel}:DIGF:STAT ON")
        if cutoff_freq > 1e4 and cutoff_freq < 1e9:
            self.write(f"CHAN{channel}:DIGFilter:CUT {cutoff_freq}")
        else:
            pass #riase an error or something?

    def deact_filter(self, channel):
        self.write(f"CHAN{channel}:DIGF:STAT OFF")
    
    def set_cutoff_freq(self, channel, cutoff_freq):
        if cutoff_freq > 1e4 and cutoff_freq < 4e9:
            self.write(f"CHAN{channel}:DIGF:CUT {cutoff_freq}")
        else:
            pass #riase an error or something?




        

class RemoteDisplay:
    def __init__(self, scope: RTO):
        self.scope = scope
        