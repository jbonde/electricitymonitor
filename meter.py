#  METER Listener application by GuruX. Modified by Streamworks/Jesper Bonde Petersen
#
#  --------------------------------------------------------------------------
#   Gurux Ltd
#
#
#
#  Filename: $HeadURL$
#
#  Version: $Revision$,
#                $Date$
#                $Author$
#
#  Copyright (c) Gurux Ltd
#
# ---------------------------------------------------------------------------
#
#   DESCRIPTION
#
#  This file is a part of Gurux Device Framework.
#
#  Gurux Device Framework is Open Source software; you can redistribute it
#  and/or modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; version 2 of the License.
#  Gurux Device Framework is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  More information of Gurux products: http://www.gurux.org
#
#  This code is licensed under the GNU General Public License v2.
#  Full text may be retrieved at http://www.gnu.org/licenses/gpl-2.0.txt
# ---------------------------------------------------------------------------
import time
import sys
import ftplib
import pkg_resources
import os
import socket
from socket import *
from gurux_common.GXCommon import GXCommon
from gurux_common.IGXMediaListener import IGXMediaListener
from gurux_common.enums.TraceLevel import TraceLevel
from gurux_serial.GXSerial import GXSerial
from GXSettings import GXSettings
from gurux_dlms.enums.InterfaceType import InterfaceType
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator
from gurux_dlms.GXReplyData import GXReplyData
from gurux_dlms.GXByteBuffer import GXByteBuffer

SWver=130 # Streamworks software version
current_directory = os.getcwd()
print("current_directory "   current_directory)

#OBIS information as received from the Meter
OBIS="" # general meter data
OBISmeterNow=0 # Current Meter reading: 1.1.1.8.0.255 Active energy A14                      01 01 01 08 00 FF
OBISmeterBef=0 # Meter reading at start of a new cycle/day.
OBISmeterAcc=0 # Accumulated meter readings today: OBISmeterNow - OBISmeterBef
OBISpowerNow=0 # Actual power usage: 1.1.1.7.0.255 Actual power P14                         01 01 01 07 00 FF
OBISpower1=0 # Actual power usage phase 1: 1.1.21.7.0.255 Actual power P14 of phase L1      01 01 15 07 00 FF
OBISpower2=0 # Actual power usage phase 2: 1.1.41.7.0.255 Actual power P14 of phase L2      01 01 29 07 00 FF
OBISpower3=0 # Actual power usage phase 3: 1.1.61.7.0.255 Actual power P14 of phase L3      01 01 3D 07 00 FF
OBISstring="OBISstring" # String with all interesting Meter Data
OBISupdated=False # Used to ensure that all OBIS data is updated before first run after reboot

POWERtoday=0 # Accumulated power usage (Actual Power P14) today
#UDP SETUP
UDPaddress='255.255.255.255'
UDPport="your preferred port number"
UDPtimeout=1
#Timings for updating CSV files
MinNow=None # Current minute
MinBef=None # Checking if a minute has passed since last update
DayNow=None # Current day
DayBef=time.strftime('%d') # Checking if day is over. Default is today so same csv is used after reboot.
# FTP information
FTPhost = 'host'
FTPdomain = 'user'
FTPpass = 'pass'
# General settings
METERpath="/home/pi/Gurux.DLMS.Python/Gurux.DLMS.Push.Listener.Example.python/" # current directory

# ---------------------------------------------------------------------------
# This example wait push notifications from the serial port or TCP/IP port.
# ---------------------------------------------------------------------------
#pylint: disable=no-self-argument

def var_write(var, value):
    try:
        t = open(METERpath   str(var)   '.txt', 'w')
        t.write(str(value))
        t.close()
    except:
        print(" var_write: File write problem ")

def var_read(var):
    try:
        t = open(METERpath   str(var)   '.txt', 'r')
        return float(t.read())
    except:
        print(" var_read: File read problem ")

OBISmeterBef=var_read("OBISmeterBef") # Use stored file at reboot
print("OBISmeterBef loaded: "   str(OBISmeterBef))
POWERtoday=var_read("POWERtoday") # Use stored file at reboot
print("POWERtoday loaded: "   str(POWERtoday))

def Upload(filename):  # Uploads the specified CSV file to the domain
 
    fileup = METERpath   str(filename)
#    print(fileup)
    try:
        session = ftplib.FTP(str(FTPhost), str(FTPdomain), str(FTPpass))
        session.encoding = "utf-8"
        file = open(str(fileup), 'rb')              # file to send
        session.cwd('/directory/')         # change directory
        with open(fileup, "rb") as file:
            # Command for Uploading the file "STOR filename"
            session.storbinary(f"STOR {filename}", file)
            print(time.strftime('%H:%M:%S')   " Updating and uploading CSV: "   str(fileup) )

#        print(session.dir())  # if you want to see content at server

        file.close()                                # close file and FTP
        session.quit()

    except:
        print ("FTP upload failed ")

def UDPsubmit():
        UDPencoded =  str.encode(str(OBISstring)   ","   "METER"   ","    str(OBISmeterNow)   ","   "SWversion"   ","    str(SWver))
        try:
            UDPsocket = socket(AF_INET, SOCK_DGRAM)
            UDPsocket.settimeout(.02)
    #        print("udp.timeout "   str(udp.timeout))
            #print ("IP: "   str(udp.getsockname()[0]))
            UDPsocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            UDPsocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            UDPsocket.sendto(UDPencoded, (UDPaddress, UDPport))
            print("UDP string submitted: "   str(OBISstring))
        except UDPsocket.timeout:
            print("UDP timeout")
            #log_error("UDP timeout")
        except OSError:
            print("OSError")
            #log_error("OSError")
        finally:
            UDPsocket.close

def CSVupdate():
    global MinBef, DayBef, POWERtoday,OBISmeterBef,OBISmeterAcc,OBISstring

    POWERtoday=float(POWERtoday) float(OBISpowerNow)/360 # Accumulated power today. Updated every 10 sec (6*60=360)
    var_write("POWERtoday", POWERtoday) # Update file to use after reboot

    DayNow=time.strftime('%d')
    if DayNow!=DayBef:
        # Open the CSV and write the header instead of old content
        print(time.strftime('%H:%M:%S')   " Creating new CSV in "   METERpath)
        r = open(METERpath   'meter.csv', 'w')
        r.write("Time"   ","   "METER today(Wh)"   ","   "Power today(W)"   ","   "Power Now(W)"   ","    "Phase1(W)"   ","    "Phase2(W)"   ","    "Phase3(W)"   '\r\n')
        r.close()
        POWERtoday=0 # Reset accumulated power at midnight
        OBISmeterBef=OBISmeterNow # Resetting the Meter counter
        var_write("OBISmeterBef", OBISmeterBef) # Update file to use after reboot
        print("OBISmeterBef "   OBISmeterBef)
        DayBef=DayNow

    MinNow=time.strftime('%M')
    if MinNow!=MinBef:
        OBISmeterAcc=float(OBISmeterNow)-float(OBISmeterBef)
        OBISstring=time.strftime('%H:%M:%S')   ","   str(OBISmeterAcc)   ","   str(POWERtoday)   ","   str(OBISpowerNow)   ","   str(OBISpower1)   ","   str(OBISpower2)   ","   str(OBISpower3)   '\r\n'
        r = open(METERpath   'meter.csv', 'a')
        r.write(OBISstring)
        Upload("meter.csv")
        MinBef=MinNow

class sampleclient(IGXMediaListener):
    def __init__(self, args):
        try:
            print("gurux_dlms version: "   pkg_resources.get_distribution("gurux_dlms").version)
            print("gurux_net version: "   pkg_resources.get_distribution("gurux_net").version)
            print("gurux_serial version: "   pkg_resources.get_distribution("gurux_serial").version)
            print("Streamworks software version "   str(SWver))
        except Exception:
            #It's OK if this fails.
            print("pkg_resources not found")
        settings = GXSettings()
        ret = settings.getParameters(args)
        if ret != 0:
            return

        #There might be several notify messages in GBT.
        self.notify = GXReplyData()
        self.client = settings.client
        self.translator = GXDLMSTranslator()
        self.reply = GXByteBuffer()
        settings.media.trace = settings.trace
        print(settings.media)

        #Start to listen events from the media.
        settings.media.addListener(self)
        #Set EOP for the media.
        if settings.client.interfaceType == InterfaceType.HDLC:
            settings.media.eop = 0x7e
        try:
            print("Press any key to close the application.")
            #Open the connection.
            settings.media.open()
            #Wait input.
            input()
            print("Closing")
        except (KeyboardInterrupt, SystemExit, Exception) as ex:
            print(ex)
        settings.media.close()
        settings.media.removeListener(self)

    def onError(self, sender, ex):
        """
        Represents the method that will handle the error event of a Gurux
        component.
        sender :  The source of the event.
        ex : An Exception object that contains the event data.
        """
        print("Error has occured. "   str(ex))

    @classmethod
    def printData(cls, value, offset):
        global OBIS, OBISmeterNow, OBISpowerNow, OBISpower1, OBISpower2, OBISpower3,OBISstring,OBISupdated
        sb = ' ' * 2 * offset
        if isinstance(value, list):
            #print(sb   "{")
            offset = offset   1
            #Print received data.
            for it in value:
                cls.printData(it, offset)
                #print(it)
            #print(sb   "}")
            #print ("OBISmeterNow="   str(OBISmeterNow))            
            #print ("OBISpowerNow="   str(OBISpowerNow))            
            #print ("OBISpower1="   str(OBISpower1))            
            #print ("OBISpower2="   str(OBISpower2))            
            #print ("OBISpower3="   str(OBISpower3))      
            #OBISstring=(OBISmeterNow "," OBISmeterAcc "," OBISpowerNow "," OBISpower1 "," OBISpower2 "," OBISpower3)
            if OBISupdated==True: # Only run this after reboot when OBIS data is updated
                UDPsubmit()
                CSVupdate()      
            offset = offset - 1
        elif isinstance(value, bytearray):
            #Print value.
            OBIS=str(GXCommon.toHex(value))
            #print(sb   str(OBIS))
        else:
            #Print value.
            if OBIS=="01 01 01 08 00 FF ":
                OBISmeterNow=float(str(value))*10 # Need to multiply for converting to Wh 
                OBISupdated=True
            if OBIS=="01 01 01 07 00 FF ":
                OBISpowerNow=str(value)
            if OBIS=="01 01 15 07 00 FF ":
                OBISpower1=str(value)
            if OBIS=="01 01 29 07 00 FF ":
                OBISpower2=str(value)
            if OBIS=="01 01 3D 07 00 FF ":
                OBISpower3=str(value)
            #print(sb   str(value))

    def onReceived(self, sender, e):
        """Media component sends received data through this method.
        sender : The source of the event.
        e : Event arguments.
        """
        #print("New data is received. "   str(e))
        #Data might come in fragments.
        self.reply.set(e.data)
        data = GXReplyData()
        try:
            if not self.client.getData(self.reply, data, self.notify):
                #If all data is received.
                if self.notify.complete:
                    if not self.notify.isMoreData():
                        #Show received data as XML.
                        try:
                            xml = self.translator.dataToXml(self.notify.data)
                            #print(xml)
                            #Print received data.
                            self.printData(self.notify.value, 0)

                            #Example is sending list of push messages in first parameter.
                            if isinstance(self.notify.value, list):
                                objects = self.client.parsePushObjects(self.notify.value[0])
                                #Remove first item because it's not needed anymore.
                                objects.pop(0)
                                Valueindex = 1
                                for obj, index in objects:
                                    self.client.updateValue(obj, index, self.notify.value[Valueindex])
                                    Valueindex  = 1
                                    #Print value
                                    #print(str(obj.objectType)   " "   obj.logicalName   " "   str(index)   ": "   str(obj.getValues()[index - 1]))
                            #print("Server address:"   str(self.notify.serverAddress)   " Client Address:"   str(self.notify.clientAddress))
                        except Exception:
                            self.reply.position = 0
                            xml = self.translator.messageToXml(self.reply)
                            #print(xml)
                        self.notify.clear()
                        self.reply.clear()
        except Exception as ex:
            #print(ex)
            self.notify.clear()
            self.reply.clear()

    def onMediaStateChange(self, sender, e):
        """Media component sends notification, when its state changes.
        sender : The source of the event.
        e : Event arguments.
        """
        print("Media state changed. "   str(e))

    def onTrace(self, sender, e):
        """Called when the Media is sending or receiving data.
        sender : The source of the event.
        e : Event arguments.
        """
        print("trace:"   str(e))

    def onPropertyChanged(self, sender, e):
        """
        Event is raised when a property is changed on a component.
        sender : The source of the event.
        e : Event arguments.
        """
        print("Property {!r} has hanged.".format(str(e)))
        
if __name__ == '__main__':
    sampleclient(sys.argv)

'''
INSTALL GURUX LIBRARY:
pip install gurux-common
pip install gurux-serial
pip install gurux-net
pip install gurux-dlms

COPY THIS PYTHON SCRIPT TO:
Gurux.DLMS.Python/Gurux.DLMS.Push.Listener.Example.python

MAKE THE APP AUTORUN AT BOOT
sudo nano /home/pi/.bashrc
INSERT AS LAST LINE:
python Gurux.DLMS.Python/Gurux.DLMS.Push.Listener.Example.python/meter.py -S '/dev/ttyS0:2400:8None1' -A "YourPersonalKeyA" -B "YourPersonalKeyB"
Ctrl X

'''
