import csv
import pendulum
import time
import os
import json
import clr
from typing import Tuple, List

from System import Action
from System import *
from time import perf_counter_ns
clr.AddReference(r"C:\Users\denma\Desktop\McsUsbNet_Examples-master\McsUsbNet\x64\McsUsbNet.dll")

# Change this path to the McsUsbNet for your computer

from Mcs.Usb import CMcsUsbListNet
from Mcs.Usb import DeviceEnumNet
from Mcs.Usb import CStg200xDownloadNet
from Mcs.Usb import McsBusTypeEnumNet
from Mcs.Usb import STG_DestinationEnumNet

import math
from System import Array, UInt32, Int32, UInt64

class STGDeviceController:
    def __init__(self, logger):
        self.logger = logger
        self.stim_amplitude_arr = []
        self.stim_duration_arr = []
        self.sync_amplitude_arr = []
        self.sync_duration_arr = []

    def convert_to_micro(self, value, unit_type):
        unit_conversion_factors = {
            'us': 1, 'ms': 1000, 's': 1000000,
            'uA': 1000, 'mA': 1000000, 'A': 1000000000,
            'uV': 1, 'mV': 1000, 'V': 1000000,
        }
        return value * unit_conversion_factors.get(unit_type, 1)
    
    def generate_stimulation_and_sync_data(self, config):
        self.stim_amplitude_arr.clear()
        self.stim_duration_arr.clear()
        self.sync_amplitude_arr.clear()
        self.sync_duration_arr.clear()

        cumulative_duration = 0
        train_duration = 0  # Initialize train duration

        for train in range(config["total_trains"]):
            self.sync_amplitude_arr.append(1)
            self.sync_duration_arr.append(config["external_signal_dur_microseconds"])
            cumulative_duration += config["pulse_duration_microseconds"]
            train_duration += config["pulse_duration_microseconds"]
            for event in range(config["number_of_events"]):
                if config["waveform"] == "Monophasic":
                    self.stim_amplitude_arr.append(config["amplitude_microamps"])
                    self.stim_duration_arr.append(config["pulse_duration_microseconds"])
                    if event < config["number_of_events"] - 1:
                        self.add_delay(config["duration_between_events_microseconds"])
                        cumulative_duration += config["duration_between_events_microseconds"] + config["pulse_duration_microseconds"]
                        train_duration += config["duration_between_events_microseconds"]
                if config["waveform"] == "Biphasic":
                    self.stim_amplitude_arr.append(config["amplitude_microamps"])
                    self.stim_duration_arr.append(config["pulse_duration_microseconds"])
                    self.stim_amplitude_arr.append(-config["amplitude_microamps"])
                    self.stim_duration_arr.append(config["pulse_duration_microseconds"])
                    if event < config["number_of_events"] - 1:
                        self.add_delay(config["duration_between_events_microseconds"])
                        cumulative_duration += config["duration_between_events_microseconds"] + 2*config["pulse_duration_microseconds"]
                        train_duration += config["duration_between_events_microseconds"]

            if train < config["total_trains"] - 1:
                next_train_start = cumulative_duration + config["time_between_trains_microseconds"]
                if config["waveform"] == "Monophasic":
                    inter_train_delay = config["time_between_trains_microseconds"] - (config["number_of_events"]*config["pulse_duration_microseconds"]+(config["number_of_events"]-1)*config["duration_between_events_microseconds"])
                if config["waveform"] == "Biphasic":
                    inter_train_delay = config["time_between_trains_microseconds"] - (config["number_of_events"]*config["pulse_duration_microseconds"]*2+(config["number_of_events"]-1)*config["duration_between_events_microseconds"])

                sync_inter_train_delay = config["time_between_trains_microseconds"] - config["external_signal_dur_microseconds"]
                if inter_train_delay > 0:
                # Append a delay at the end of each train to match the time until the next train starts
                    self.add_delay(inter_train_delay)
                cumulative_duration += sync_inter_train_delay
                self.sync_amplitude_arr.append(0)  # Sync signal low to mark inter-train delay
                self.sync_duration_arr.append(sync_inter_train_delay)

    def add_delay(self, delay_duration):
        self.stim_amplitude_arr.append(0)
        self.stim_duration_arr.append(delay_duration)
    @staticmethod
    def prepare_device_data(amplitude_arr, duration_arr):
        encoded_amplitude = []
        for amp in amplitude_arr:
            magnitude = abs(amp) & 0xFFF
            if amp < 0:
                # Set sign bit for negative amplitudes
                encoded_value = (1 << 15) | magnitude
            else:
                # Positive amplitudes directly
                encoded_value = (0 << 7) | magnitude

            # Convert encoded_value to int for formatting purposes
            formatted_value = (encoded_value)
            #print(f"Encoded: {formatted_value} | Binary: {formatted_value:016b}")
            encoded_amplitude.append(encoded_value)

        pData = Array[UInt16](UInt16(d) for d in encoded_amplitude)
        tData = Array[UInt64]([UInt64(int(d)) for d in duration_arr])
        return pData, tData

    def configure_device_and_send_data(self, config):
        deviceList = CMcsUsbListNet(DeviceEnumNet.MCS_DEVICE_USB)
        if deviceList.Count == 0:
            self.logger.error("No devices found")
            return

        device = CStg200xDownloadNet()
        device.Connect(deviceList.GetUsbListEntry(0))

        if config["modulation_type_group"].lower() == 'current':
            device.SetCurrentMode()
            device.SetCurrentRangeSelectedIndex(0,1)
            print(device.GetCurrentRangeInNanoAmpByIndex(0,1))
            currentRange = device.GetCurrentRangeInNanoAmp(0);
            currentResolution = device.GetCurrentResolutionInNanoAmp(0);
            print('Current Mode:  Range: %d uA  Resolution: %1.2f uA' % (currentRange/1000, currentResolution/1000.0))

        else:
            device.SetVoltageMode()

        self.generate_stimulation_and_sync_data(config)

        pData, tData = self.prepare_device_data(self.stim_amplitude_arr, self.stim_duration_arr)
        #device.SendChannelData(UInt32(0), pData, tData)

        sync_pData = Array[UInt16]([UInt16(d) for d in self.sync_amplitude_arr])
        sync_tData = Array[UInt64]([UInt64(d) for d in self.sync_duration_arr])
        device.PrepareAndSendData(0, self.stim_amplitude_arr, self.stim_duration_arr,STG_DestinationEnumNet.channeldata_current)
        #device.SendChannelData(0)
        device.SendSyncData(UInt32(0), sync_pData, sync_tData)

        device.SendStart(UInt32(1))
        print("Stimulation started. Please wait for completion...")

        # Wait for stimulation to complete based on the total duration of all events
        total_duration = sum(self.stim_duration_arr) / 1000000.0  # Converting microseconds to seconds
        time.sleep(total_duration)

        device.SendStop(UInt32(1))
        print("Stimulation completed.")
        device.Disconnect()

# Example usage
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

controller = STGDeviceController(logger)
config = {
    'total_trains': 5,
    'number_of_events': 3,
    'amplitude_microamps': 100000,
    'pulse_duration_microseconds': 100,
    'duration_between_events_microseconds': 100,
    'time_between_trains_microseconds': 2000000,
    'modulation_type_group': 'current',
    'waveform': 'Biphasic',
    'external_signal_dur_microseconds': 100  # Assuming 100 microseconds as an example
}
controller.configure_device_and_send_data(config)
