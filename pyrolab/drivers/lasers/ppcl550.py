# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pure Photonics Tunable Laser 5xx (specifically designed for PPCL550 and PPCL551)
-----------------------------------------------
Driver for the Santec PPCL-5xx Tunable Laser.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/pyrolab/drivers/lasers
Functions
---------
    __init__(self,minWL=1515,maxWL=1570,minPow=7,maxPow=13.5,port="COM4",
            baudrate=9600)
    setPower(self,power)
    setChannel(self,channel=1)
    setMode(self,mode)
    setWavelength(self,wavelength,jump=0)
    on(self,pin=13)
    off(self,pin=13)
    _communicate(self,register,data,rw)
    _send(self,msg)
    _recieve(self)
    _checksum(self,msg)
    _wl_freq(self,unit)
    close(self)
    __del__(self)
"""

import serial
import time
import threading
import array
from Pyro5.errors import PyroError
from Pyro5.api import expose
import pyrolab.api

C_SPEED = 299792458

ITLA_NOERROR=0x00
ITLA_EXERROR=0x01
ITLA_AEERROR=0x02
ITLA_CPERROR=0x03
ITLA_NRERROR=0x04
ITLA_CSERROR=0x05
ITLA_ERROR_SERPORT=0x01
ITLA_ERROR_SERBAUD=0x02

REG_Nop=0x00
REG_Mfgr=0x02
REG_Model=0x03
REG_Serial=0x04
REG_Release=0x06
REG_Gencfg=0x08
REG_AeaEar=0x0B
REG_Iocap=0x0D
REG_Ear=0x10
REG_Dlconfig=0x14
REG_Dlstatus=0x15
REG_Channel=0x30
REG_Power=0x31
REG_Resena=0x32
REG_Grid=0x34
REG_Fcf1=0x35
REG_Fcf2=0x36
REG_Oop=0x42
REG_Opsl=0x50
REG_Opsh=0x51
REG_Lfl1=0x52
REG_Lfl2=0x53
REG_Lfh1=0x54
REG_Lfh2=0x55
REG_Currents=0x57
REG_Temps=0x58
REG_Ftf=0x62
REG_Mode=0x90
REG_PW=0xE0
REG_Csweepsena=0xE5
REG_Csweepamp=0xE4
REG_Cscanamp=0xE4
REG_Cscanon=0xE5
REG_Csweepon=0xE5
REG_Csweepoffset=0xE6
REG_Cscanoffset=0xE6
REG_Cscansled=0xF0
REG_Cscanf1=0xF1
REG_Cscanf2=0xF2
REG_CjumpTHz=0xEA
REG_CjumpGHz=0xEB
REG_CjumpSled=0xEC
REG_Cjumpon=0xED
REG_Cjumpoffset=0xE6

READ=0
WRITE=1

@expose
class PPCL55x:

    def __init__(self,minWL=1515,maxWL=1570,minPow=6,maxPow=13.5,port="COM4",
            baudrate=9600):
        """"
        Initialize limiting values for the laser.

        Parameters
        ----------
        minWL : double
            Minimum wavelength the laser will produce in nanometers.
        maxWL : double
            Maximum wavelength the laser will produce in nanometers.
        minPow : double
            Minimum power level of the laser in dBm
        maxPow : double
            Maximum power level of the laser in dBm
        port : str
            COM port the laser is connected to (e.g. "COM4")
        baudrate : int
            baudrate of the serial connection default is 9600
        """
        self.minWavelength = minWL
        self.maxWavelength = maxWL
        self.minPower = minPow
        self.maxPower = maxPow
        self.port = port
        self._error=ITLA_NOERROR
        self.latestregister = 0
        self.queue = []
        self.maxrowticket = 0
        self.powerState = 0

        try:
            self.lasercom = serial.Serial(self.port,baudrate,timeout=1,
                parity=serial.PARITY_NONE) #attempt connection with given baudrate
        except serial.SerialException:
            raise IOError("Serial Connection Error")
        baudrate2=4800
        #if the initial connection doesn't work try different baudrates
        while baudrate2<115200: 
            back = self._communicate(REG_Nop,0,0)
            if back != ITLA_NOERROR:
                #go to next baudrate
                if baudrate2==4800: baudrate2=9600
                elif baudrate2==9600: baudrate2=19200
                elif baudrate2==19200: baudrate2=38400
                elif baudrate2==38400: baudrate2=57600
                elif baudrate2==57600: baudrate2=115200
                self.lasercom.close()
                self.lasercom = serial.Serial(self.port,baudrate2,timeout=None,
                    parity=serial.PARITY_NONE)            
            else:
                return
        print(baudrate2)
        self.lasercom.close()
        raise IOError("Serial Connection Error")

    def setPower(self,power):
        """"
        Set the power on the laser.

        Parameters
        ----------
        power : double
            Power that the laser will be set to in dBm
        """

        sendPower = int(power*100)  #scale the power inputed
        #on the REG_Power register, send the power
        back = self._communicate(REG_Power,sendPower,1)  
        return back


    def setChannel(self,channel=1):
        """"
        Set the channel (should always be 1)

        Parameters
        ----------
        channel : int
            channel that the laser is on
        """
        #on the REG_Channel register, send the channel
        back = self._communicate(REG_Channel,channel,1)  
        return back

    
    def setMode(self,mode):
        """
        Set the mode of operation for the laser

        Parameters
        ----------
        mode : int
            Mode for the laser:
            0 - regular mode
            1 - no dither mode
            2 - clean mode
        """
        #on the REG_Mode register, send the mode
        back = self._communicate(REG_Mode,mode,1)
        return back


    def setWavelength(self,wavelength):
        """
        Set the wavelength of the laser. Laser must be off in order to set the 
        wavelength. If laser is not off this function will turn it off and then 
        back on.

        Parameters
        ----------
        wavelength : double
            Wavelength of the laser
        """

        init_time = time.time()
        #if the wavelength is not in the allowed range
        if(wavelength < self.minWavelength or wavelength > self.maxWavelength):
                return "wavelength not in range"
        freq = self._wl_freq(wavelength)
        freq_t = int(freq/1000)
        #convert the wavelength to frequency for each register
        freq_g = int(freq*10) - freq_t*10000    
        # print(freq_t)
        # print(freq_g)

        if self.powerState:   #if the laser is currently on
            self.off()
            back = self._communicate(REG_Fcf1,freq_t,1)
            if(back == ITLA_NOERROR):
                #write the new wavelength to the REG_Fcf2 register
                back = self._communicate(REG_Fcf2,freq_g,1)  
            time_diff = time.time() - init_time
            # print(time_diff)
            self.on()
            return back
        else:
            back = self._communicate(REG_Fcf1,freq_t,1)
            if(back == ITLA_NOERROR):
                #write the new wavelength to the REG_Fcf2 register
                back = self._communicate(REG_Fcf2,freq_g,1)
            time_diff = time.time() - init_time
            # print(time_diff)
            return back
    

    def on(self):
        """
        Turn on the laser
        """
        #start communication by sending 8 to REG_Resena register
        back = self._communicate(REG_Resena,8,1) 
        for x in range(10):
            #send 0 to REG_Nop register to wait for a "ready" response
            back = self._communicate(REG_Nop,0,0)   
        self.powerState = 1
        return back
    

    def off(self):
        """
        Turn off the laser
        """
        #stop communication by sending 0 to REG_Resena register
        back = self._communicate(REG_Resena,0,1) 
        self.powerState = 0
        return back


    def _communicate(self,register,data,rw):
        """
        Function that implements the commmunication with the laser. It will 
        first send a message then recieve a response.

        Parameters
        ----------
        register : byte
            Register to which will be written. Each laser function has its own 
            register.
        data : byte
            User-specific data that will be sent to the laser
        rw : int
            Defines if the communication is read-write or only write
            0 : write only
            1 : write then read
        """

        lock = threading.Lock()
        lock.acquire()
        rowticket = self.maxrowticket + 1
        self.maxrowticket = self.maxrowticket + 1
        self.queue.append(rowticket)
        lock.release()
        while self.queue[0] != rowticket:
            rowticket=rowticket
        if rw == 0:     #if write and then read
            byte2 = int(data/256)
            byte3 = int(data - byte2*256)
            self.latestregister = register      #modify bytes for sending
            msg = [rw,register,byte2,byte3]
            msg[0] = msg[0] | int(self._checksum(msg))*16    #calculate checksum
            self._send(msg)  #send the message
            recvmsg = self._recieve()    #recieve the response from the laser
            #print(recvmsg)
            datamsg = recvmsg[2]*256 + recvmsg[3]
            #if the message is larger than 4 bytes, read it using AEA method (not implemented)
            if (recvmsg[0] & 0x03) == 0x02:
                extmsg = self.AEA(datamsg)  #not implemented
                lock.acquire()
                self.queue.pop(0)
                lock.release()
                return extmsg
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)
        else:   #if only write
            byte2=int(data/256)
            byte3=int(data - byte2*256)
            msg = [rw,register,byte2,byte3]
            msg[0] = msg[0] | int(self._checksum(msg))*16    #construct message and send
            self._send(msg)
            recvmsg = self._recieve()    #recieve message
            # print("recieved")
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)

    """
    Function sends message of four bytes to the laser.
    """
    def _send(self,msg):
        """
        Sends message of four bytes to the laser

        Parameters
        ----------
        msg : 4 x 1 bytes
            Message that will be sent to the laser
        """

        self.lasercom.flush()
        #construct the bytes from the inputed message
        sendBytes = array.array('B',msg).tobytes()  
        self.lasercom.write(sendBytes)  #write the bytes on the serial connection


    def _recieve(self):
        """
        Recieves, decifers, and certifies message from the laser
        
        Raises
        ------
        PyroError(f"SerialCommunicationFailure queue[0] = {self.queue[0]}")
            Error to signal that the laser did not respond or the response was 
            not long enough.
        PyroError("ChecksumError")
            Error to signal that the recieved message had an irregular checksum.
        """

        reftime = time.time()
        while self.lasercom.inWaiting()<4:  #wait until 4 bytes are recieved
            if(time.time() > reftime + 0.5): #if it takes longer than 0.25 seconds break
                self._error=ITLA_NRERROR
                return(0xFF,0xFF,0xFF,0xFF)
            time.sleep(0.0001)
        try:
            num = self.lasercom.inWaiting() #get number of bytes for debugging purposes
            msg = []
            bAll = self.lasercom.read(num)  #read the four bytes from serial
            for b in bAll:
                msg.append(b)   #construct array of bytes from the message
            msg = msg[0:4]
        except:
            raise PyroError(f"SerialCommunicationFailure queue[0] = {self.queue[0]}")
            msg = [0xFF,0xFF,0xFF,0xFF]
        if self._checksum(msg) == msg[0] >> 4: # ensure the checksum is correct
            self._error = msg[0] & 0x03
            return(msg) #return the message recieved
        else:
            #if the checksum is wrong, log a CS error
            raise PyroError("ChecksumError")  
            self._error=ITLA_CSERROR
            return(msg)  

    """
    Function calculates the checksum.
    """
    def _checksum(self,msg):     #calculate checksum
        """
        Calculate the checksum of a message

        Parameters
        ----------
        msg : 4 x 1 bytes
            Four-byte message that will be used to produce a checksum
        """

        bip8=(msg[0] & 0x0f) ^ msg[1] ^ msg[2] ^ msg[3]
        bip4=((bip8 & 0xf0) >> 4) ^ (bip8 & 0x0f)
        return bip4

    """
    Convert from wavelength to frequency
    """
    def _wl_freq(self,wl):
        """
        Convert from wavelength to frequency using propagation velocity of c

        Parameters
        ----------
        wl : double
            Wavelength in nanometers
        """

        return C_SPEED/wl
    

    def close(self):
        """
        Disconnect from the laser
        """

        self.lasercom.close()
        return 0

    def __del__(self):
        """"
        Function called when Proxy connection is lost.
        """
        self.close()