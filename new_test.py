import numpy as np
import hvplot.pandas  # Import hvplot for Pandas
import pandas as pd
import panel as pn
import random
# Ensure extensions are loaded
#pn.extension('bokeh', 'hvplot')  # Load both bokeh and hvplot extensions
#pd.options.plotting.backend = 'holoviews'

# Ensure Panel extension is initialized
pn.extension()
import csv
import pendulum
import time
import os
import clr

from System import Action
from System import *

#change this path to the McsUsbNet for your computer
clr.AddReference(r"C:\Users\denma\Documents\GitHub\McsUsbNet_Examples-master\McsUsbNet\x64\McsUsbNet.dll")

from Mcs.Usb import CMcsUsbListNet
from Mcs.Usb import DeviceEnumNet

from Mcs.Usb import CStg200xDownloadNet
from Mcs.Usb import McsBusTypeEnumNet
from Mcs.Usb import STG_DestinationEnumNet

import math
from System import Array, UInt32, Int32, UInt64

class STGStimulation:
    def __init__(self, waveform, amplitude, pulse_duration, frequency, events, duration_between_events, total_trains, time_between_trains, external_signal_dur, modulation_type):
        self.waveform = waveform
        self.amplitude = amplitude
        self.pulse_duration = pulse_duration
        self.frequency = frequency
        self.events = events
        self.duration_between_events = duration_between_events
        self.total_trains = total_trains
        self.time_between_trains = time_between_trains
        self.external_signal_dur = external_signal_dur
        self.modulation_type = modulation_type
        
        # Initialize empty lists for stimulation and synchronization data
        self.stim_amplitude_arr = []
        self.stim_duration_arr = []
        self.sync_amplitude_arr = []
        self.sync_duration_arr = []
    """
    def generate_stimulation_and_sync_data(self):
        self.stim_amplitude_arr.clear()
        self.stim_duration_arr.clear()
        self.sync_amplitude_arr.clear()
        self.sync_duration_arr.clear()

        for train in range(self.total_trains):
            # Add a sync signal at the start of each train.
            self.sync_amplitude_arr.append(1)  # Assuming sync signal goes high at the start
            # Ensure the duration is positive; adjust according to your needs.
            self.sync_duration_arr.append(max(1000, 0))  # Example: 1ms high, prevent negative values

            for event in range(self.events):
                self.add_waveform_event()
                if event < self.events - 1:
                    self.add_delay(self.duration_between_events)

            # Inter-train delay, if applicable
            if train < self.total_trains - 1:
                self.add_delay(self.time_between_trains)

            # Optionally, add a sync signal marking the end of a train
            # Make sure the added duration or logic here does not result in negative values

        # Add a final sync signal at the end, if needed, ensuring its duration is positive
        self.sync_amplitude_arr.append(0)  # Sync high to mark the end
        self.sync_duration_arr.append(max(5000, 0))  # Example: 5ms high, prevent negative values


    def add_waveform_event(self):
        if self.waveform == "Monophasic":
            self.stim_amplitude_arr.append(self.amplitude)  # Positive phase
            self.stim_duration_arr.append(self.pulse_duration)
        elif self.waveform == "Biphasic":
            self.stim_amplitude_arr.append(self.amplitude)  # Positive phase
            self.stim_duration_arr.append(self.pulse_duration)
            self.stim_amplitude_arr.append(-self.amplitude)  # Negative phase
            self.stim_duration_arr.append(self.pulse_duration)
        elif self.waveform == "Sinusoidal":
            # For simplicity, treating sinusoidal as a series of monophasic pulses
            self.stim_amplitude_arr.append(self.amplitude)
            self.stim_duration_arr.append(1000 / self.frequency)  # Period of one cycle

    def add_delay(self, delay_duration):
        # Adding delay as zero amplitude
        self.stim_amplitude_arr.append(0)
        self.stim_duration_arr.append(delay_duration)
    """
    def generate_stimulation_and_sync_data(self):
        self.stim_amplitude_arr.clear()
        self.stim_duration_arr.clear()
        self.sync_amplitude_arr.clear()
        self.sync_duration_arr.clear()

        # Variable to track the cumulative duration for the correct placement of sync signals
        cumulative_duration = 0
        train_duration = 0  # Initialize train duration

        for train in range(self.total_trains):
            # Start of each train marked with a high sync signal
            self.sync_amplitude_arr.append(1)
            # Assuming the sync pulse duration matches the first event pulse
            self.sync_duration_arr.append(self.pulse_duration)
            cumulative_duration += self.pulse_duration
            train_duration += self.pulse_duration  # Update train duration
            for event in range(self.events):
                # Add event and its duration
                self.stim_amplitude_arr.append(self.amplitude)
                self.stim_duration_arr.append(self.pulse_duration)
                if event < self.events - 1:
                    # Inter-event delay
                    self.add_delay(self.duration_between_events)
                    cumulative_duration += self.duration_between_events + self.pulse_duration
                    train_duration += self.duration_between_events

            if train < self.total_trains - 1:
                # Calculate inter-train delay from the end of the last event of the current train
                # to the start of the first event of the next train
                next_train_start = cumulative_duration + self.time_between_trains
                inter_train_delay = self.time_between_trains - (self.events * self.pulse_duration + (self.events - 1) * self.duration_between_events)
                sync_inter_train_delay = next_train_start - cumulative_duration - self.pulse_duration
                if inter_train_delay > 0:
                # Append a delay at the end of each train to match the time until the next train starts
                    self.add_delay(inter_train_delay)
                cumulative_duration += sync_inter_train_delay

                # Add a low sync signal during the inter-train delay to demarcate trains
                self.sync_amplitude_arr.append(0)  # Sync signal low to mark inter-train delay
                self.sync_duration_arr.append(sync_inter_train_delay)

    def add_waveform_event(self):
        # Logic to add waveform-specific event
        if self.waveform == "Monophasic":
            self.stim_amplitude_arr.append(self.amplitude)
            self.stim_duration_arr.append(self.pulse_duration)
        elif self.waveform == "Biphasic":
            self.stim_amplitude_arr.append(self.amplitude)
            self.stim_duration_arr.append(self.pulse_duration)
            # For biphasic, add the negative phase immediately after
            self.stim_amplitude_arr.append(-self.amplitude)
            self.stim_duration_arr.append(self.pulse_duration)
        elif self.waveform == "Sinusoidal":
            self.stim_amplitude_arr.append(self.amplitude)
            self.stim_duration_arr.append(1000 / self.frequency)  # One cycle's duration

    def add_delay(self, delay_duration):
        # Logic to add delay between events or trains
        self.stim_amplitude_arr.append(0)  # Zero amplitude for delay
        self.stim_duration_arr.append(delay_duration)

    @staticmethod
    def prepare_device_data(amplitude_arr, duration_arr):
        encoded_amplitude = []
        for amp in amplitude_arr:
            if amp < 0:
                encoded_value = (abs(amp) & 0xFFF) | 0x1000  # Set sign bit for negative amplitudes
            else:
                encoded_value = amp & 0xFFF  # Positive amplitudes directly
            encoded_amplitude.append(encoded_value)

        pData = Array[UInt16](encoded_amplitude)
        tData = Array[UInt64]([UInt64(d) for d in duration_arr])
        return pData, tData
    
    def encode_amplitude(self, amplitude_arr):
        # Encode amplitude values with sign bit as per STG requirements
        encoded_amplitude = []
        for amp in amplitude_arr:
            if amp < 0:
                encoded_value = (abs(amp) & 0xFFF) | 0x1000  # Set sign bit for negative amplitudes
            else:
                encoded_value = amp & 0xFFF  # Positive amplitudes directly
            encoded_amplitude.append(encoded_value)
        return Array[UInt16](encoded_amplitude)

    # Method to send data to the device would go here
    # For simplicity, it's not included
    def configure_device_and_send_data(self, device):
        # Generate stimulation and synchronization data based on input parameters
        self.generate_stimulation_and_sync_data()
        print(self.stim_amplitude_arr)
        print(self.stim_duration_arr)
        print(self.sync_amplitude_arr)
        print(self.sync_duration_arr)

        # Prepare the data with the correct arrays directly using the static method
        pData, tData = self.prepare_device_data(self.stim_amplitude_arr, self.stim_duration_arr)
        sync_pData = Array[UInt16]([UInt16(v) for v in self.sync_amplitude_arr])
        sync_tData = Array[UInt64]([UInt64(d) for d in self.sync_duration_arr])

        # Configure the device mode based on modulation type
        if self.modulation_type.lower() == 'current':
            device.SetCurrentMode()
        else:
            device.SetVoltageMode()
        # Setup triggers, assuming the device supports configuring multiple triggers
        trigger_inputs = device.GetNumberOfTriggerInputs()
        channelmap = Array[UInt32]([1] + [0] * (trigger_inputs - 1))  # Activate the first channel
        syncoutmap = Array[UInt32]([1] + [0] * (trigger_inputs - 1))  # Sync signal for synchronization
        repeat = Array[UInt32]([0] * trigger_inputs)  # Infinite repeat for simplicity
        print(channelmap)
        device.SetupTrigger(UInt32(0), channelmap, syncoutmap, repeat)

        # Clear any previous data on the channel and sync output
        device.ClearChannelData(UInt32(0))
        device.ClearSyncData(UInt32(0))

        # Send stimulation data to the device
        device.SendChannelData(UInt32(0), pData, tData)

        # For synchronization signal, assuming simple on/off logic
        print(sync_pData)
        device.SendSyncData(UInt32(0), sync_pData, sync_tData)

        # Start the stimulation based on the trigger configuration
        device.SendStart(UInt32(1))

        print("Stimulation started. Please wait for completion...")
        
        # Wait for stimulation to complete based on the duration (simplified)
        total_duration = (sum(self.stim_duration_arr)/1000000) #+ 0.00001  # Convert µs to seconds
        time.sleep(total_duration)
        device.SendStop(1)
        print("Stimulation completed. Disconnecting from device.")
        device.Disconnect()

    #def prepare_device_data(self):
    #    # Wrap the method call with correct parameters
    #    return self.prepare_device_data(self.stim_amplitude_arr, self.stim_duration_arr)

def PollHandler(status, stgStatusNet, index_list):
            print('%x %s' % (status, str(stgStatusNet.TiggerStatus[0])))

deviceList = CMcsUsbListNet(DeviceEnumNet.MCS_DEVICE_USB)
#print(deviceList)
print("found %d devices" % (deviceList.Count))

for i in range(deviceList.Count):
    listEntry = deviceList.GetUsbListEntry(i)
    print("Device: %s   Serial: %s" % (listEntry.DeviceName,listEntry.SerialNumber))


    device = CStg200xDownloadNet();

    device.Stg200xPollStatusEvent += PollHandler;

    device.Connect(deviceList.GetUsbListEntry(0))

stg5_controller = STGStimulation(
    waveform='Monophasic',
    amplitude=500000,
    pulse_duration=1000,
    frequency=1,
    events=3,
    duration_between_events=10000,
    total_trains=5,
    time_between_trains=2000000,
    external_signal_dur=1000,
    modulation_type='Voltage'
)

# Step 3: Configure the device and send the data
stg5_controller.configure_device_and_send_data(device)