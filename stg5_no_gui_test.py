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

class STGDeviceController:
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

    def channel_data(self):
        return [self.waveform, self.amplitude, self.pulse_duration, self.frequency, self.events, self.duration_between_events, self.total_trains, self.time_between_trains, self.external_signal_dur]
        # Additional initializations as necessary
    def dat_data(self):
        waveform, amplitude, pulse_duration, frequency, events, duration_between_events, total_trains, time_between_trains, external_signal_dur = self.channel_data()
        #channels_data = {1: [], 2:[], 3: [], 4: [], 5: [], 6:[], 7: [], 8: [], 9: [], 10:[], 11: [], 12: [], 13: [], 14:[], 15: [], 16: []}
        
        channels_data = {channel: [] for channel in range(1, 17)}
    
        # Helper function to add pulse data
        def add_pulse_data(channel, pulse, value1, value2, duration):
            channels_data[channel].append({
                "pulse": pulse,
                "value1": f"{value1:.3f}",
                "value2": f"{value2:.3f}",
                "time": duration
            })
        
        # Initial delay for channel 1 and initial signal for channel 3
        add_pulse_data(1, 0, 0.000, 0.000, 5050)  # Initial delay for channel 1
        add_pulse_data(9, 0, 0.000, 0.000, 5050)  # Initial delay for channel 9
        add_pulse_data(10, 0, 0.000, 1.000, 5000)  # Initial 5000 time unit on signal for channel 3
        add_pulse_data(10, 0, 0.000, 0.000, 50)    # Followed by 50 time unit off signal for channel 3
        
        for train in range(total_trains):
            for event in range(events):
                # Assign waveform-specific values and add pulse data
                if waveform == "Monophasic":
                    total_time = events * (pulse_duration + duration_between_events)
                    add_pulse_data(1, 0, 0, amplitude, pulse_duration)
                    add_pulse_data(1, 0, 0, 0, duration_between_events)
                    if event == events - 1:  # Add rest time at the end of each train, except after the last event
                        add_pulse_data(1, 0, 0, 0, time_between_trains - total_time)
                elif waveform == "Biphasic":
                    total_time = events * (2 * pulse_duration + duration_between_events)
                    # Biphasic waveform: first phase amplitude, then negative phase
                    add_pulse_data(1, 0, 0, amplitude, pulse_duration)
                    add_pulse_data(1, 0, 0, -amplitude, pulse_duration)
                    add_pulse_data(1, 0, 0, 0, duration_between_events)
                    if event == events - 1:
                        add_pulse_data(1, 0, 0, 0, time_between_trains - total_time)
                elif waveform == "Sinusoidal":
                    total_time = events * (1/frequency + duration_between_events)
                    # For simplicity, assuming each event in a sinusoidal train lasts for 'pulse_duration'
                    add_pulse_data(1, 0, 0, amplitude, pulse_duration)
                    add_pulse_data(1, 0, 0, 0, duration_between_events)
                    if event == events - 1:
                        add_pulse_data(1, 0, 0, 0, time_between_trains - total_time)

        # Process external signal duration and delay from stimulus for relevant channels
            add_pulse_data(9, 0, 0, 1.000, external_signal_dur)
            add_pulse_data(9, 0, 0, 0.000, time_between_trains-external_signal_dur)  # Example for external signal duration
        return channels_data

    def create_dat_file(self, file_path, dat_data):
        with open(file_path, 'w') as file:
            # Write header information
            file.write("Multi Channel Systems MC_Stimulus II\n")
            file.write("ASCII import Version 1.10\n\n")
            file.write(f"channels:\t{int(len(dat_data)/2)}\n")
            file.write(f"output mode:\t{'current' if self.modulation_type == 'Current' else 'voltage'}\n")
            file.write("format:\t5\n\n")
            
            # Iterate over each channel and its data
            for channel, data in dat_data.items():
                file.write(f"channel: {channel}\n")
                file.write("pulse\tvalue\tvalue\ttime\n")
                for row in data:
                    file.write(f"{row['pulse']}\t{row['value1']}\t{row['value2']}\t{row['time']}\n")
                file.write("\n")  # Add an empty line after each channel's data

    def configure_and_send_stimulation(self):
        def PollHandler(status, stgStatusNet, index_list):
            print('%x %s' % (status, str(stgStatusNet.TiggerStatus[0])))

        deviceList = CMcsUsbListNet(DeviceEnumNet.MCS_DEVICE_USB)

        print("found %d devices" % (deviceList.Count))

        for i in range(deviceList.Count):
            listEntry = deviceList.GetUsbListEntry(i)
            print("Device: %s   Serial: %s" % (listEntry.DeviceName,listEntry.SerialNumber))


            device = CStg200xDownloadNet();

            device.Stg200xPollStatusEvent += PollHandler;

            device.Connect(deviceList.GetUsbListEntry(0))

        # Define channel and sync out maps for starting triggers
        channelmap = [1, 0, 0, 0]
        syncoutmap = [1, 0, 0, 0]
        start_channelmap = [2, 0, 0, 0]
        start_syncoutmap = [2, 0, 0, 0]
        start_repeat = [1, 0, 0, 0]

        total_channels = 2  # Assuming 16 channels for this example
    
        # Initialize arrays to hold the combined data for all events and trains
        amplitude_arr = []
        duration_arr = []
        sync_out_val_arr = []
        sync_out_dur_arr = []

        # Calculate the patterns based on waveform type
        for train in range(self.total_trains):
            for event in range(self.events):
                # Example for Monophasic waveform
                if self.waveform == "Monophasic":
                    amplitude_arr.append(self.amplitude)
                    duration_arr.append(self.pulse_duration)
                    # Assuming sync out patterns match the stimulus duration 1-to-1
                    sync_out_val_arr.append(1)  # Marking the sync signal high
                    sync_out_dur_arr.append(self.pulse_duration)
                    if event < self.events - 1:  # If not the last event, add inter-event duration
                        amplitude_arr.append(0)  # No stimulus during inter-event interval
                        duration_arr.append(self.duration_between_events)
                        sync_out_val_arr.append(0)  # Sync signal low during inter-event interval
                        sync_out_dur_arr.append(self.duration_between_events)

                # Add patterns for Biphasic and Sinusoidal waveforms as needed

            # After all events in a train, add delay until the next train, if applicable
            if train < self.total_trains - 1:
                total_train_duration = sum(duration_arr)  # Sum of durations so far
                inter_train_delay = self.time_between_trains - total_train_duration
                if inter_train_delay > 0:
                    amplitude_arr.append(0)  # No stimulus during inter-train interval
                    duration_arr.append(inter_train_delay)
                    sync_out_val_arr.append(0)  # Sync signal low during inter-train interval
                    sync_out_dur_arr.append(inter_train_delay)

        # Convert Python lists to .NET arrays for sending to the device
        amplitude = Array[Int32](amplitude_arr)
        duration = Array[UInt64]([UInt64(d) for d in duration_arr])
        syncout = Array[Int32](sync_out_val_arr)
        syncout_dur = Array[UInt64]([UInt64(d) for d in sync_out_dur_arr])
        device.SetupTrigger(1, Array[UInt32](channelmap), Array[UInt32](syncoutmap), Array[UInt32](start_repeat))
        # Clear previous data and prepare new data for channels and sync out
        for channel in range(0, total_channels):
            device.ClearChannelData(channel)
            device.ClearSyncData(channel)
            # Prepare and send data - this example sends the same data to each channel
            if self.modulation_type == 'Current':
                device.SetCurrentMode()
                print('Current Mode')
                device.SendChannelData(channel, amplitude, duration)#, STG_DestinationEnumNet.channeldata_current)
            else:
                device.SetVoltageMode()
                print('Voltage Mode')
                device.SendChannelData(0, amplitude, duration)#, STG_DestinationEnumNet.channeldata_voltage)
            #device.PrepareAndSendData(UInt32(channel), amplitude, duration, STG_DestinationEnumNet.channeldata_voltage)
        device.SendSyncData(0, syncout, syncout_dur, STG_DestinationEnumNet.syncoutdata)

        # Setup trigger configurations
        # Additional trigger setup as needed

        # Start the stimulation
        device.SendStart(1)  # Use triggermap 1 to start
        #device.SendPreparedData0,()  # Use triggermap 1 to start
        time.sleep(10)
        print('All Done!')
        device.Disconnect()
        print('Disconnected')
    def config(self):
        deviceList = CMcsUsbListNet(DeviceEnumNet.MCS_DEVICE_USB)
        device = CStg200xDownloadNet()
        device.Connect(deviceList.GetUsbListEntry(0))

        # Define memory layout and capacities
        total_memory = device.GetTotalMemory()
        nchannels = device.GetNumberOfAnalogChannels()
        nsync = device.GetNumberOfSyncoutChannels()

        # Divide total memory into segments and assign to channels and sync outputs
        segment_memory = [total_memory // 2, total_memory // 2]  # Example: 2 segments
        device.SegmentDefine(Array[UInt32](segment_memory))

        channel_capacity = Array[UInt32]([segment_memory[0] // (nchannels + nsync) for _ in range(nchannels)])
        syncout_capacity = Array[UInt32]([segment_memory[0] // (nchannels + nsync) for _ in range(nsync)])

        for i in range(2):  # Assuming 2 segments for simplicity
            device.SegmentSelect(UInt32(i))
            device.SetCapacity(channel_capacity, syncout_capacity)

        # Setup triggers
        trigger_inputs = device.GetNumberOfTriggerInputs()
        channelmap = Array[UInt32]([0] * trigger_inputs)
        syncoutmap = Array[UInt32]([0] * trigger_inputs)
        repeat = Array[UInt32]([0] * trigger_inputs)

        # Example trigger configuration
        channelmap[0] = 1  # Channel 1 to trigger 1
        syncoutmap[0] = 1  # Syncout 1 to trigger 1
        channelmap[1] = 4  # Channel 3 to trigger 2
        repeat[0] = 0  # Infinite repeat

        device.SetupTrigger(channelmap, syncoutmap, repeat)

        # Set mode based on modulation type and send data
        modulation_type = 'Voltage'  # or 'Current'
        if modulation_type == 'Current':
            device.SetCurrentMode()
        else:
            device.SetVoltageMode()

        # Prepare channel and sync data
        # Example data preparation for one channel (similar logic applies for others)
        l = 1000  # Length of data
        factor = 0.1  # Amplitude factor
        DACResolution = device.GetDACResolution()

        # Data for Channel 0
        pData_channel = Array[UInt16](l)
        tData_channel = Array[UInt64]([UInt64(20) for _ in range(l)])  # Duration in µs for each data point

        for i in range(l):
            # Example sin wave calculation
            sin_value = factor * (pow(2, DACResolution - 1) - 1.0) * math.sin(2.0 * i * math.pi / l)
            pData_channel[i] = UInt16(max(0, min(sin_value, pow(2, DACResolution) - 1)))

        # Send data to channel
        device.ClearChannelData(0)
        device.SendChannelData(0, pData_channel, tData_channel)

        # Data for Sync 0 (example)
        # Similar preparation and sending logic for sync data as shown for channel data

        # Start stimulation
        device.SendStart(UInt32(1))  # Start trigger 1

        # Add delay for the duration of the stimulation or monitoring

        print('Stimulation sent. Disconnecting...')
        device.Disconnect()
import math
from System import Array, UInt32, Int32, UInt64

# Assuming CLR references and MCS USB Library imports are done above

class STGStimulation:
    def __init__(self, waveform, amplitude, pulse_duration, frequency, events, duration_between_events, total_trains, time_between_trains, external_signal_dur, modulation_type):
        self.waveform = waveform
        self.amplitude = amplitude  # Expected to be a single value for simplicity in this context
        self.pulse_duration = pulse_duration
        self.frequency = frequency
        self.events = events
        self.duration_between_events = duration_between_events
        self.total_trains = total_trains
        self.time_between_trains = time_between_trains
        self.external_signal_dur = external_signal_dur
        self.modulation_type = modulation_type
        
        self.amplitude_arr = []
        self.duration_arr = []
        self.prepare_stimulation_pattern()
    def prepare_stimulation_pattern(self):
        # Implement logic based on waveform, frequency, etc., to fill amplitude_arr and duration_arr
        # This is a simplified version, adjust according to your waveform logic
        for _ in range(self.total_trains):
            for _ in range(self.events):
                self.amplitude_arr.append(self.amplitude)
                self.duration_arr.append(self.pulse_duration)

    def convert_to_device_data(self):
        # Convert amplitude and duration to the format required by the device
        pData, tData = self.prepare_device_data(self.amplitude_arr, self.duration_arr)
        return pData, tData

    def calculate_stimulation_pattern(self):
        for train in range(self.total_trains):
            for event in range(self.events):
                if self.waveform == "Monophasic":
                    self.append_monophasic_pattern(event)
                elif self.waveform == "Biphasic":
                    self.append_biphasic_pattern(event)
                elif self.waveform == "Sinusoidal":
                    self.append_sinusoidal_pattern(event)

                # Logic for inter-event duration
                if event < self.events - 1:
                    self.append_inter_event_duration()

            # Logic for inter-train delay
            self.append_inter_train_delay(train)

        # Final conversion to .NET arrays for device communication
        self.convert_to_net_arrays()

    def append_monophasic_pattern(self, event):
        self.amplitude_arr.append(self.amplitude)
        self.duration_arr.append(self.pulse_duration)
        self.sync_out_val_arr.append(1)  # High for pulse duration
        self.sync_out_dur_arr.append(self.pulse_duration)

    def append_biphasic_pattern(self, event):
        # Assuming equal duration for positive and negative phases
        #amplitude_value = -500000  # Direct assignment for debugging
        #print(type(amplitude_value), amplitude_value)
        self.amplitude_arr.extend([self.amplitude, -self.amplitude])
        self.duration_arr.extend([self.pulse_duration, self.pulse_duration])
        self.sync_out_val_arr.extend([1, 1])  # High for both phases
        self.sync_out_dur_arr.extend([self.pulse_duration, self.pulse_duration])

    def append_sinusoidal_pattern(self, event):
        # Approximation for a sinusoidal pattern as a series of monophasic pulses
        phase_duration = 1000 / self.frequency  # Convert frequency to period duration
        self.amplitude_arr.append(self.amplitude)
        self.duration_arr.append(phase_duration)
        self.sync_out_val_arr.append(1)  # High for phase duration
        self.sync_out_dur_arr.append(phase_duration)

    def append_inter_event_duration(self):
        self.amplitude_arr.append(0)  # No stimulus
        self.duration_arr.append(self.duration_between_events)
        self.sync_out_val_arr.append(0)  # Sync signal low
        self.sync_out_dur_arr.append(self.duration_between_events)

    def append_inter_train_delay(self, train):
        if train < self.total_trains - 1:
            total_train_duration = sum(self.duration_arr)
            inter_train_delay = self.time_between_trains - total_train_duration
            if inter_train_delay > 0:
                self.amplitude_arr.append(0)  # No stimulus during delay
                self.duration_arr.append(inter_train_delay)
                self.sync_out_val_arr.append(0)  # Sync signal low during delay
                self.sync_out_dur_arr.append(inter_train_delay)

    def convert_to_net_arrays(self):
        # Convert amplitude from Int32 to UInt16 with correct handling
        # Note: This assumes amplitude values are within UInt16 range after any necessary scaling
        #amplitude_uint16_array = np.array(self.amplitude_arr, dtype=np.uint16)
        #self.amplitude_net_array = Array[UInt16](amplitude_uint16_array.tolist())

        #self.duration_net_array = Array[UInt64]([UInt64(d) for d in self.duration_arr])
        #self.syncout_net_array = Array[UInt16]([UInt16(v) for v in self.sync_out_val_arr])  # Assuming sync signals are compatible with UInt16
        #self.syncout_dur_net_array = Array[UInt64]([UInt64(d) for d in self.sync_out_dur_arr])
        return
    @staticmethod
    def prepare_device_data(amplitude_arr, duration_arr):
        encoded_amplitude = []
        for amp in amplitude_arr:
            if amp < 0:
                encoded_value = (abs(amp) & 0xFFF) | 0x1000
            else:
                encoded_value = amp & 0xFFF
            encoded_amplitude.append(encoded_value)
        
        pData = Array[UInt16](encoded_amplitude)
        tData = Array[UInt64]([UInt64(max(20, (d // 20) * 20)) for d in duration_arr])
        return pData, tData

    def configure_device_and_send_data(self, device):
        if self.modulation_type.lower() == 'current':
            device.SetCurrentMode()
        else:
            device.SetVoltageMode()

        pData, tData = self.convert_to_device_data()
        
        # Assuming only one channel for simplicity
        device.ClearChannelData(UInt32(0))
        device.SendChannelData(UInt32(0), pData, tData)
        # Calculate stimulation pattern first
        self.calculate_stimulation_pattern()
        # Setup triggers, assuming the device.GetNumberOfTriggerInputs() works as expected
        TriggerInputs = device.GetNumberOfTriggerInputs()
        channelmap = Array[UInt32]([0] * TriggerInputs)
        syncoutmap = Array[UInt32]([0] * TriggerInputs)
        repeat = Array[UInt32]([0] * TriggerInputs)

        # Here we assume the first trigger (index 0) is used and set forever repeat
        channelmap[0] = 1  # Channel 1
        syncoutmap[0] = 1  # Syncout 1
        repeat[0] = 0  # Infinite repeat

        device.SetupTrigger(UInt32(1), channelmap, syncoutmap, repeat)

        # Sending channel data
        device.ClearChannelData(UInt32(0))
        # Assuming amplitude and duration are matched one-to-one
        device.SendChannelData(UInt32(0), pData, tData)
        device.ClearSyncoutData(UInt32(0))
        # Assuming amplitude and duration are matched one-to-one
        #device.SendSyncoutData(UInt32(0), syncout_net_array, syncout_dur_net_array)
        # If using SyncOut, make sure to clear and send sync data similarly
        # device.ClearSyncData(UInt32(0)) for example, and then device.SendSyncData() as needed

        # Start the stimulation
        device.SendStart(UInt32(1))  # Using the first trigger setup

        print("Stimulation started. Please wait...")
        time.sleep(20)  # Adjust this based on your expected stimulation duration
        print("Stimulation completed. Disconnecting from device.")
        
        device.Disconnect()






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
    amplitude=50000,
    pulse_duration=1000000,
    frequency=1,
    events=3,
    duration_between_events=100,
    total_trains=5,
    time_between_trains=10000000,
    external_signal_dur=200,
    modulation_type='Voltage'
)
stg5_controller.calculate_stimulation_pattern()

# Step 3: Configure the device and send the data
stg5_controller.configure_device_and_send_data(device)

#ch_data = stg5_controller.channel_data()
#dat_data = stg5_controller.dat_data()
#file_path = os.path.join(os.getcwd(), "output.dat")  # Save in current working directory
#stg5_controller.create_dat_file(file_path, dat_data)
#stg5_controller.config()