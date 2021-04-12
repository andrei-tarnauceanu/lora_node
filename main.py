import socket
import time
import binascii
import struct
import pycom
from network import LoRa
from CayenneLPP import CayenneLPP
import config
from pytrack import Pytrack
from LIS2HH12 import LIS2HH12
from L76GNSS import L76GNSS

py = Pytrack()

li = LIS2HH12(py)

# Disable heartbeat LED
pycom.heartbeat(False)

# Initialize LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

# remove all the non-default channels
for i in range(3, 16):
    lora.remove_channel(i)

# set the 3 default channels to the same frequency
lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)

# create an OTAA authentication parameters
dev_addr = struct.unpack(">l", binascii.unhexlify('260138FB'))[0]
nwk_swkey = binascii.unhexlify('84D3B6B7A8D45E963D51EF330852B8FD')
app_swkey = binascii.unhexlify('73931202649A60F3007D1B4B18393B23')

# join a network using ABP
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))

# wait until the module has joined the network
while not lora.has_joined():
    pycom.rgbled(0x140000)
    time.sleep(2.5)
    pycom.rgbled(0x000000)
    time.sleep(1.0)
    print('Not yet joined...')

print('OTAA joined')
pycom.rgbled(0x001400)

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, config.LORA_NODE_DR)

while True:
    s.setblocking(True)
    pycom.rgbled(0x000014)
    lpp = CayenneLPP()
    l76 = L76GNSS(py, timeout=30)

    print('\n\n** 3-Axis Accelerometer (LIS2HH12)')
    print('Acceleration', li.acceleration())
    print('Roll', li.roll())
    print('Pitch', li.pitch())
    lpp.add_accelerometer(1, li.acceleration()[0], li.acceleration()[1], li.acceleration()[2])
    lpp.add_gryrometer(1, li.roll(), li.pitch(), 0)

    print('\n\n** GNSS/GPS module')
    gpsResult = l76.coordinates()
    print('Coordinates', gpsResult)
    # Determine whether we got a valid fix
    if gpsResult == (None, None):
        print("No GPS fix")
    else:
        print("GPS lat: " + str(gpsResult[0]) + "long:" + str(gpsResult[1]))
        lpp.add_gps(1, gpsResult[0], gpsResult[1], -1)

    print('Sending data (uplink)...')
    s.send(bytes(lpp.get_buffer()))
    s.setblocking(False)
    data = s.recv(64)
    print('Received data (downlink)', data)
    pycom.rgbled(0x001400)
    time.sleep(30)
