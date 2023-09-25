# Electricity Monitor

How to use a Raspberry Pi for reading a Kamstrup Omnipower Electricity Meter

Realising that the documentation for the different components and packages is very scarce I have made this brief summary of how I managed to pick up readings from my Omnipower Meter with a Raspberry Pi.

For me the interesting electricity data is Meter status (as seen on the display) and actual total power consumption plus consumption for each phase.

I prefer to extract the data as readable raw data so it can be used directly by other applications like Home Assistant. Then data can simply be shared with other devices and web services over UDP or as plain csv files etc.

First of all Push messages needs to be enabled from the meter even though the documentation indicates that this is done by default. So contact your power supplier and request push messages and also two keys as the information is encrypted. You will then get a mail from Kamstrup with the keys. It comes in a tabulated setup which will be probably distorted in the mail.

So a message like this

| Key | Type | Generation Key|
| --- | --- | --- |
| 64 | 1 | 0x34706890A462483973431E01C8914E21 |
| 65 | 1 | 0x946F0B5C495176089391783F32C4E33A |


Should be reformatted to 

| Key | Type |Hex | Generation Key |
| --- | --- | --- | --- |
| 64	| 1	| 0x	| 34706890A462483973431E01C8914E21 |
| 65 | 1	| 0x	| 946F0B5C495176089391783F32C4E33A |


64 = gpk60 = encryption_key

65 = gpk61 = authentication_key

Connect your RPi serial port to the CCC connector at the Meter like this:


| CCC |	RPipin | GPIO | Function (RPi) |
| --- | --- | --- | --- |
| 6 | 6 | 6 | GND | 
| 2 | 8 | 14 | Data from RPi (Tx) |
| 5 | 10 | 15 | Data from Meter (Rx) | 

For a RPi4 the above serial port to use is called ttyS0 when listening to the Meter. GPIO14 is not necessary in this setup but can be used for other applications that makes queries for the Meter.

For listening to the Meter Gurux has a good library that can be installed from https://github.com/Gurux/Gurux.DLMS.Python and they also have an excellent support so sign up at the forum if you have troubles. I didn’t succeed with a RPi3 with Gurux but switching to a RPi4 suddenly made things going.

When ready you can make a test drive in order to see if the Meter is pushing messages which it should do every 10 sec. I prefer connecting to the RPi with SSH and Putty and here at the command prompt first change directory to the Gurux listener script:

cd /home/pi/Gurux.DLMS.Python/Gurux.DLMS.Push.Listener.Example.python

Then run the main.py so you can see the options:

python main.py

Now try main.py with addition of the serial port:

python main.py -S ‘/dev/ttyS0:2400:8None1’

Please notice 2400 bps is important. The above should give some initial readings (encrypted) to confirm that the connection is working.

Finally run the application with the encryption keys (maybe you need to swop A and B).

python main.py -S ‘/dev/ttyS0:2400:8None1’ -B 34706890A462483973431E01C8914E21 -A 946F0B5C495176089391783F32C4E33A

In my case I needed to swop -A and -B as encryption_key and authentication_key was mixed up probably by Kamstrup. You will then see readings presented in different formats. Each Data Object has its own ID as can be seen at page 4 in this list: https://radiuselnet.dk/wp-content/uploads/DLMS-COSEM.pdf

Meter status (as seen on the display) and actual power consumption are all represented by number 14 in the list.

My current python script is developed thanks to Gurux (see installation notes at end of code)

## For those using HOME ASSISTANT

As the RPi (hopefully) now broadcasts messages at the same network as your HA, you can create a sensor that listens to UDP. As UDP is not supported as a standard HA-component, this can be done instead by creating a sensor that calls a python-script every second.
sensor. See configuration.yaml

Then copy content from powernowudp.py to HA and make shure the path is correct in configuration.yaml.
It's a simple version only showing with current power consumption but you can expand for listening to other attributes in the UDP-string.
