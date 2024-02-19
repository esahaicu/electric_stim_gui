import time
import os
import clr

from System import Array, UInt32, Int32, UInt64
from System import Action

clr.AddReference(os.getcwd() + '\\..\\..\\McsUsbNet\\x64\\McsUsbNet.dll')
from Mcs.Usb import CMcsUsbListNet, DeviceEnumNet, CStg200xDownloadNet
from Mcs.Usb import McsBusTypeEnumNet, STG_DestinationEnumNet

def PollHandler(status, stgStatusNet, index_list):
    # This might need to be adjusted to log the trigger number specifically
    print('%x %s' % (status, str(stgStatusNet.TiggerStatus[0])))

deviceList = CMcsUsbListNet(DeviceEnumNet.MCS_DEVICE_USB)
print("found %d devices" % (deviceList.Count))

for i in range(deviceList.Count):
    listEntry = deviceList.GetUsbListEntry(i)
    print("Device: %s   Serial: %s" % (listEntry.DeviceName, listEntry.SerialNumber))

device = CStg200xDownloadNet()
device.Stg200xPollStatusEvent += PollHandler
device.Connect(deviceList.GetUsbListEntry(0))

# Stimulus configuration
amplitude = Array[Int32]([-50, 50,0])  # Amplitudes in µA
duration = Array[UInt64]([100, 100, 999800])  # Durations in µs

# Sync pulse configuration - Assuming the sync pulse needs to be tied to the stimulus in some way
syncoutmap = Array[UInt32]([1, 0, 0, 0])  # Assuming channel 0 is used for sync, adjust as necessary
repeat = Array[UInt32]([1, 0, 0, 0])  # Repeat once for simplicity, adjust if needed

device.SetupTrigger(0, Array[UInt32]([1,0,0,0]), syncoutmap, repeat)  # Setup trigger for the stimulus
device.SetCurrentMode()  # Assuming current mode is needed, change to SetVoltageMode() if voltage mode is required

# For the sync pulse, if it needs to be exactly 4000us, further configuration might be needed,
# possibly involving additional calls or adjusting the setup here.

device.PrepareAndSendData(0, amplitude, duration, STG_DestinationEnumNet.channeldata_current)
device.SendStart(1)  # Start the stimulus
time.sleep(1)  # Wait for 1 second to complete the cycle

device.Disconnect()
