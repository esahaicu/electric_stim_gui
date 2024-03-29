# Import necessary libraries
import param  # Used for declaring parameters for widgets
import panel as pn  # Core library for creating the GUI
import numpy as np  # For numerical operations
import holoviews as hv  # For data visualization
import pandas as pd  # For handling tabular data
from panel.template import DarkTheme  # Importing a dark theme for the GUI
from holoviews import opts  # For setting options on holoviews objects
import csv  # For CSV file operations
import pendulum  # For handling dates and times
import time  # For timing and delays
import os  # For interacting with the operating system
import clr  # For .NET integration, to interact with the MCS device

# Import specific .NET libraries needed to interact with the MCS STG device
from System import Action
from System import Array, UInt32, Int32, UInt64
clr.AddReference(r"C:\Users\denma\Documents\GitHub\McsUsbNet_Examples-master\McsUsbNet\x64\McsUsbNet.dll")
from Mcs.Usb import CMcsUsbListNet, DeviceEnumNet, CStg200xDownloadNet, McsBusTypeEnumNet, STG_DestinationEnumNet

# Initialize the HoloViews and Panel libraries with their respective extensions
hv.extension('bokeh')
pn.extension('katex')

# Define a base class for pipeline stages to handle updates
class PipelineStage(param.Parameterized):
    @staticmethod
    def update_output(*args, **kwargs):
        pass

# Define a class for configuring stimulation parameters
class StimulationParameters(PipelineStage):
    # Define selectable options and default values for parameters
    waveform = param.ClassSelector(class_=pn.widgets.RadioButtonGroup, default='Biphasic', objects=['Monophasic', 'Biphasic', 'Sinusoidal'])
    volt_or_curr = param.ClassSelector(class_=pn.widgets.RadioButtonGroup, default='Current', objects=['Current', 'Voltage'])
    amplitude = param.ClassSelector(class_=pn.widgets.IntSlider, default=0, bounds=(-1000, 1000))
    pulse_duration = param.ClassSelector(class_=pn.widgets.IntSlider, default=100, bounds=(0, 1000))
    frequency_or_period_choice = param.ClassSelector(class_=pn.widgets.RadioButtonGroup, default="Frequency", objects=["Frequency", "Period"])
    frequency_period_value = param.ClassSelector(class_=pn.widgets.IntSlider, default=1.0, bounds=(0.1, 1000), step=0.1)
    
    phase = param.String(default='Neither')
    frequency = param.Number(default=0, bounds=(0, None))
    period = param.Number(default=0, bounds=(0, None))
   
    def __init__(self, main_gui, **params):
        super().__init__(**params)
        self.main_gui = main_gui
        self._update_visibility()
        self._update_phase()
        self._update_frequency_period()

        self.param.watch(self._update_visibility, ['waveform', 'amplitude'])
        self.param.watch(self._update_phase, 'amplitude')
        self.param.watch(self._update_frequency_period, ['frequency_or_period_choice', 'frequency_period_value'])
    @param.depends('amplitude', watch=True)
    def _update_phase(self):
        if self.amplitude > 0:
            self.phase = "Anode"
        elif self.amplitude < 0:
            self.phase = "Cathode"
        else:
            self.phase = "Neither"

    @param.depends('frequency_or_period_choice', 'frequency_period_value', watch=True)
    def _update_frequency_period(self):
        if self.frequency_or_period_choice == "Frequency":
            self.frequency = self.frequency_period_value
            self.period = 1000 / self.frequency_period_value if self.frequency_period_value != 0 else float('inf')
        else:
            self.period = self.frequency_period_value
            self.frequency = 1000 / self.period if self.period != 0 else 0

    def _update_visibility(self):
        is_sinusoidal = self.waveform == 'Sinusoidal'
        self.param['frequency_or_period_choice'].precedence = 0 if is_sinusoidal else -1
        self.param['frequency_period_value'].precedence = 0 if is_sinusoidal else -1


# Class for configuring trigger parameters
class TriggerParameters(PipelineStage):
    # Define parameters for trigger settings
    allow_external = param.Boolean(False, label='Allow For External Trigger?')
    total_trains = param.Number(default=50, precedence=1, label='Total Number of Trains: ')
    time_between_trains = param.Number(default=2000, precedence=1, label = 'Time Between Each Train (ms):')
    def __init__(self, main_gui, **params):
        super().__init__(**params)
        self.main_gui = main_gui
        # Set up watchers on parameters that affect the view
        self.param.watch(self.update_output, ['allow_external', 'total_trains', 'time_between_trains'])
    @param.depends('allow_external', watch=True)
    def _update_fields(self):
        # Toggle the visibility of total trains and time between trains based on external trigger option
        if self.allow_external:
            self.param['total_trains'].precedence = -1  # Hide if external trigger is allowed
            self.param['time_between_trains'].precedence = -1
        else:
            self.param['total_trains'].precedence = 1
            self.param['time_between_trains'].precedence = 1
    # Generate GUI layout for trigger parameters
    def view(self):
        external_widget = pn.widgets.Toggle(name='Allow External Trigger?', button_type='success')
        total_trains_widget = pn.widgets.IntInput(name='Total Trains', value=self.total_trains)
        time_between_trains_widget = pn.widgets.IntInput(name='Time Between trains (ms)', step=1)

        # Combine widgets into a layout
        return pn.Column(external_widget, total_trains_widget, time_between_trains_widget)
    def update_output(self, event=None):
        # This method now contains logic to refresh the GUI components affected by parameter changes
        # For simplicity, you might just call self.view() if the entire view needs to be refreshed,
        # or implement more specific logic if only parts of the view need updating
        self._update_fields()
        return self.view()
# Class for setting up external signal parameters
class ExternalSignal(PipelineStage):
    # Define parameters for external signal settings
    duration = param.Number(default=0.0, label='Duration of External Signal (us):')
    delay = param.Number(default=0.0, label='Delay Between External Signal and Stimulation (us):')
    def __init__(self, main_gui, **params):
        super().__init__(**params)
        # Set up watchers on parameters that affect the view
        self.param.watch(self.update_output, ['duration', 'delay'])
        self.main_gui = main_gui

    # Generate GUI layout for external signal parameters
    def view(self):
        duration_widget = pn.widgets.FloatInput(name='Duration of External Signal (us)', value=self.duration)
        delay_widget = pn.widgets.FloatInput(name='Delay Between External Pulse and Stimulus (us)', value=self.delay)

        # Combine widgets into a layout
        return pn.Column(duration_widget, delay_widget)
    def update_output(self, event=None):
        # This method now contains logic to refresh the GUI components affected by parameter changes
        # For simplicity, you might just call self.view() if the entire view needs to be refreshed,
        # or implement more specific logic if only parts of the view need updating
        return self.view()
        # adapt to various experimental requirements. By using Panel widgets, the GUI is both functional and user-friendly.

# Class for displaying the output and running the simulation
class OutputDisplay(param.Parameterized):
    # Define parameters to control which elements to include in the output display
    include_waveform = param.Boolean(True, doc="Include Waveform")
    include_vc = param.Boolean(True, doc="Include VC")
    # Additional parameters to control visibility of each stimulation parameter in the output
    include_amplitude = param.Boolean(True, doc="Include Amplitude")
    include_pulse_duration = param.Boolean(True, doc="Include Pulse Duration")
    include_phase = param.Boolean(True, doc="Include Phase")
    include_frequency_period_value = param.Boolean(True, doc="Include Frequency/Period Value")
    include_calculated_frequency = param.Boolean(True, doc="Include Calculated Frequency")
    include_calculated_period = param.Boolean(True, doc="Include Calculated Period")
    include_external_triggering = param.Boolean(True, doc="Include External Triggering")
    include_total_trains = param.Boolean(True, doc="Include Total Trains")
    include_time_between_trains = param.Boolean(True, doc="Include Time Between Trains")
    include_external_signal_duration = param.Boolean(True, doc="Include External Signal Duration")
    include_delay_from_beginning = param.Boolean(True, doc="Include Delay From Beginning")
    include_comment = param.String(default='None', doc="Comment")
    output_location = param.String(default='/Users/eashan/DenmanLab/stg5_try/output_1.dat', doc="Output Location")
    run_action = param.Action(label='Run Simulation')  # Button to trigger the simulation

    def __init__(self, main_gui, stimulation_params, trigger_params, external_signal_params, **params):
        super(OutputDisplay, self).__init__(**params)
        self.stimulation_params = stimulation_params
        self.trigger_params = trigger_params
        self.external_signal_params = external_signal_params
        self.param.watch(self.update_table_data, [
            'include_waveform', 'include_vc', 'include_amplitude', 'include_pulse_duration', 'include_phase', 
            'include_frequency_period_value', 'include_calculated_frequency', 'include_calculated_period',
            'include_external_triggering', 'include_total_trains', 'include_time_between_trains',
            'include_external_signal_duration', 'include_delay_from_beginning'
        ])
        self.main_gui = main_gui
        # Watch for changes in parameters to update the output display accordingly

    def update_table_data(self, event=None):
        data = {
            "Parameter": [],
            "Value": []
        }
        # Dynamically add data based on the inclusion flags
        if self.include_waveform:
            data["Parameter"].append("Waveform")
            data["Value"].append(self.stimulation_params.waveform)
        if self.include_vc:
            data["Parameter"].append("Voltage or Current")
            data["Value"].append(self.stimulation_params.volt_or_curr)
        if self.include_amplitude:
            data["Parameter"].append("Amplitude")
            data["Value"].append(f"{self.stimulation_params.amplitude} {'uV' if self.stimulation_params.volt_or_curr == 'Voltage' else 'uA'}")
        if self.include_pulse_duration:
            data["Parameter"].append("Pulse Duration")
            data["Value"].append(f"{self.stimulation_params.pulse_duration} us")
        if self.include_phase:
            data["Parameter"].append("Phase")
            data["Value"].append(self.stimulation_params.phase)
        if self.include_frequency_period_value:
            data["Parameter"].append(self.stimulation_params.frequency_or_period_choice)
            data["Value"].append(self.stimulation_params.frequency_period_value)
        if self.include_calculated_frequency:
            data["Parameter"].append("Calculated Frequency")
            data["Value"].append(f"{self.stimulation_params.frequency} Hz")
        if self.include_calculated_period:
            data["Parameter"].append("Calculated Period")
            data["Value"].append(f"{self.stimulation_params.period} ms")
        if self.include_external_triggering:
            external_triggering = "Yes" if self.trigger_params.allow_external else "No"
            data["Parameter"].append("External Triggering")
            data["Value"].append(external_triggering)
        if self.include_total_trains:
            data["Parameter"].append("Total Trains")
            data["Value"].append(self.trigger_params.total_trains)
        if self.include_time_between_trains:
            data["Parameter"].append("Time Between Trains")
            data["Value"].append(f"{self.trigger_params.time_between_trains} ms")
        if self.include_external_signal_duration:
            data["Parameter"].append("External Signal Duration")
            data["Value"].append(f"{self.external_signal_params.duration} us")
        if self.include_delay_from_beginning:
            data["Parameter"].append("Delay From Beginning")
            data["Value"].append(f"{self.external_signal_params.delay} us")
        if self.include_comment:
            data["Parameter"].append("Comments:")
            data["Value"].append(f"{self.include_comment}")
        # Create DataFrame and update the table
        self.df = pd.DataFrame(data)
        self.table.object = self.df  # Assuming self.table is a pn.widgets.DataFrame or similar
    def _update_output_location(self, event):
        self.output_location = event.new
    def _update_comment_location(self, event):
        self.include_comment = event.new
    def view(self):
        # Generate the layout for the output display section
        # This now includes the loading bar and loading percent indicator along with the table, comment, and output location widgets

        # Define widgets for comment and output location
        comment_widget = pn.widgets.TextInput(value=self.include_comment, name='Comment: ')
        output_location_widget = pn.widgets.TextInput(value=self.output_location, name='Output Location')

        # Watch for changes in the comment and output location widgets
        comment_widget.param.watch(self._update_comment_location, 'value')
        output_location_widget.param.watch(self._update_output_location, 'value')

        # Initialize the DataFrame pane for displaying the table
        self.table = pn.pane.DataFrame(pd.DataFrame(), index=False)
        self.update_table_data()  # Populate the table with initial data

        # Define a run button to trigger the simulation
        run_button = pn.widgets.Button(name="RUN", button_type="primary", on_click=self.run_simulation)

        # Initialize the loading bar and loading percent indicator
        self.loading_bar_widget = pn.indicators.Progress(name='Progress', value=0, max=100, width=200)
        self.loading_percent = pn.indicators.Number(name='Progress', value=0, format='{value}%')

        # Assemble the layout with the loading bar and loading percent indicator
        layout = pn.Column(
            self.table,
            pn.layout.Divider(),
            comment_widget,
            output_location_widget,
            run_button,
            self.loading_bar_widget,  # Include the loading bar in the layout
            self.loading_percent       # Include the loading percent indicator in the layout
        )
        return layout
    def channel_data(self, volt_or_curr, waveform, amplitude, pulse_duration, frequency, total_trains, time_between_trains, external_signal_dur, delay_from_stim):
        # Initialize lists to hold amplitude and duration values, and repeat counts
        amplitudes = []
        durations = []
        repeats = []
        syncout_val = []
        syncout_dur = []
        
        # Calculate the base amplitude and duration for each waveform type
        if waveform == "Monophasic":
            # For Monophasic, we have a single phase of stimulation
            amplitudes.extend([amplitude,0])  # Amplitude in uA
            durations.extend([pulse_duration,time_between_trains-pulse_duration])  # Duration in us
            syncout_val.extend([1,0])
            syncout_dur.extend([external_signal_dur, time_between_trains-external_signal_dur])

        elif waveform == "Biphasic":
            # For Biphasic, we have two phases: positive and negative
            amplitudes.extend([amplitude, -amplitude,0])  # Positive then negative phase
            durations.extend([pulse_duration, pulse_duration, time_between_trains-(2*pulse_duration)])  # Same duration for both phases
            syncout_val.extend([1,1,0])
            syncout_dur.extend([int(external_signal_dur/2),int(external_signal_dur-int(external_signal_dur/2)), time_between_trains-external_signal_dur])

        elif waveform == "Sinusoidal":
            # For Sinusoidal, this is an approximation, as actual sinusoidal waveforms
            # would need continuous variation rather than discrete steps
            # Here, you might need a different approach for a true sinusoidal pattern
            # For simplicity, let's treat it as a single phase here
            amplitudes.extend([amplitude,0])  # Amplitude in uA
            pulse_time = 1000 / frequency  # Convert frequency to period (ms), then to us
            durations.append([pulse_time, time_between_trains-pulse_duration])  # Duration in us based on frequency
            syncout_val.extend([1,0])
            syncout_dur.extend([external_signal_dur, time_between_trains-external_signal_dur])

        # Handle repeats - Assuming each pattern is repeated 'total_trains' times
        # This is a simplification; actual implementation might need adjustment
        repeats = [total_trains, 0, 0, 0]  # Repeat each pattern 'total_trains' times
        
        # Convert lists to arrays suitable for STG device programming
        amplitude_arr = amplitudes  # Directly usable in your STG programming function
        duration_arr = durations  # Directly usable in your STG programming function
        repeat_arr = repeats  # Directly usable in your STG programming function
        sync_out_val_arr = syncout_val
        sync_out_dur_arr = syncout_dur
        print(repeat_arr)
        return volt_or_curr, amplitude_arr, duration_arr, repeat_arr, sync_out_val_arr, sync_out_dur_arr
    
    def stg5_connect_and_program(self, volt_or_curr, amplitude_arr, duration_arr, repeat_arr, sync_out_val_arr, sync_out_dur_arr):
    # Placeholder for actual connection logic
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

            #voltageRange = device.GetVoltageRangeInMicroVolt(0);
            #voltageResulution = device.GetVoltageResolutionInMicroVolt(0);
            #currentRange = device.GetCurrentRangeInNanoAmp(0);
            #currentResolution = device.GetCurrentResolutionInNanoAmp(0);

            #print('Voltage Mode:  Range: %d mV  Resolution: %1.2f mV' % (voltageRange/1000, voltageResulution/1000.0))
            #print('Current Mode:  Range: %d uA  Resolution: %1.2f uA' % (currentRange/1000, currentResolution/1000.0))

            channelmap = Array[UInt32]([1,0,0,0])
            syncoutmap = Array[UInt32]([1,0,0,0])
            start_channelmap = Array[UInt32]([2,0,0,0])
            start_syncoutmap = Array[UInt32]([2,0,0,0])
            start_repeat = Array[UInt32]([1,0,0,0])
            repeat = Array[Int32](repeat_arr)
            amplitude = Array[Int32](amplitude_arr)
            duration = Array[UInt64](duration_arr)
            syncout = Array[Int32](sync_out_val_arr)
            syncout_dur = Array[UInt64](sync_out_dur_arr)
            syncout_start = Array[Int32]([1,0])
            syncout_start_dur = Array[UInt64]([500,100])

            device.SetupTrigger(0, channelmap, syncoutmap, repeat)
            device.SetupTrigger(1, start_channelmap, start_syncoutmap, start_repeat)
            if volt_or_curr == 'Current':
                device.SetCurrentMode()
                print('Current Mode')
                device.PrepareAndSendData(0, amplitude*1000, duration, STG_DestinationEnumNet.channeldata_current)
            else:
                device.SetVoltageMode()
                print('Voltage Mode')
                device.PrepareAndSendData(0, amplitude, duration, STG_DestinationEnumNet.channeldata_voltage)

            device.PrepareAndSendData(0, syncout, syncout_dur, STG_DestinationEnumNet.syncoutdata)
            device.PrepareAndSendData(1, syncout_start, syncout_start_dur, STG_DestinationEnumNet.syncoutdata)
            print('Starting!')
            device.SendStart(2)
            time.sleep(0.001)
            print('Sending Pulses!')
            device.SendStart(1)
            tic = time.perf_counter()
            toc = 0
            #time.sleep((np.sum(duration_arr)/1000000)*np.max(repeat_arr))
            total_duration = int((np.sum(duration_arr)/1000000)*np.max(repeat_arr))
            
            while toc < total_duration:
                toc = time.perf_counter()-tic
                #print(toc)
                self.loading_bar_widget.value=int((toc/total_duration)*100)
                self.loading_percent.value = int((toc/total_duration)*100)
                self.update_table_data()
                #print('Updated')
            print('All Done!')
            device.Disconnect()
            print('Disconnected')
    def run_simulation(self, event=None):
                # Gather input values from the GUI
        datetime_val = pendulum.now(tz='America/Denver')

        waveform = self.stimulation_params.waveform
        volt_or_curr = self.stimulation_params.volt_or_curr
        amplitude = self.stimulation_params.amplitude
        pulse_duration = self.stimulation_params.pulse_duration
        frequency = self.stimulation_params.frequency  # Use the calculated frequency
        total_trains = self.trigger_params.total_trains
        time_between_trains = self.trigger_params.time_between_trains * 1000  # Convert from ms to us
        external_signal_dur = self.external_signal_params.duration
        delay_from_stim = self.external_signal_params.delay
        
        # Map GUI inputs to channel_data function parameters
        volt_or_curr, amplitude_arr, duration_arr, repeat_arr, sync_out_val_arr, sync_out_dur_arr = self.channel_data(volt_or_curr, waveform, amplitude, pulse_duration, frequency, total_trains, time_between_trains, external_signal_dur, delay_from_stim)
        print(np.shape(amplitude_arr), np.shape(duration_arr), np.shape(repeat_arr), np.shape(sync_out_val_arr), np.shape(sync_out_dur_arr))
        self.stg5_connect_and_program(volt_or_curr, amplitude_arr, duration_arr, repeat_arr, sync_out_val_arr, sync_out_dur_arr)
        # Specify the output file path from the GUI input
        #output_file_path = "/Users/eashan/DenmanLab/stg5_try/ascii_output/output_{}-{}-{}T{}_{}.dat".format(datetime_val.year, datetime_val.month, datetime_val.day, datetime_val.hour, datetime_val.minute)
        csv_file_path = r'C:\Users\denma\Desktop\stg5_trial_csvs\csv_{}.csv'.format(datetime_val.to_iso8601_string().replace(':','-').replace('T','_').replace('.','___'))
    # Save the DataFrame to a CSV file
        self.df.to_csv(csv_file_path, index=False)
        self.update_table_data()  # Update table data if needed

# Finally, the script combines all the components into a Panel Tabs layout for easy navigation between different sections of the GUI.
# Each section (Stimulation Parameters, Trigger Parameters, External Signal, and Output) is added as a separate tab.


class MainGUI(param.Parameterized):
    def __init__(self, **params):
        super(MainGUI, self).__init__(**params)
        
        # Pass self (MainGUI instance) to component classes
        self.stimulation_params = StimulationParameters(main_gui=self)
        self.trigger_params = TriggerParameters(main_gui=self)
        self.external_signal_params = ExternalSignal(main_gui=self)
        self.output_display = OutputDisplay(main_gui=self, stimulation_params=self.stimulation_params, 
                                             trigger_params=self.trigger_params, 
                                             external_signal_params=self.external_signal_params)

        self.tabs = self.setup_tabs()

    def setup_tabs(self):
        return pn.Tabs(
            ('Stimulation Parameters', self.stimulation_params),
            ('Trigger Parameters', self.trigger_params.view),
            ('External Signal', self.external_signal_params.view),
            ('Output', self.output_display.view)
        )
    def update_tabs(self):
        for stage in [self.stimulation_params, self.trigger_params, self.external_signal_params]:
            stage.param.watch(lambda event: self.output_display.update_table_data(), list(stage.param))
            #stage.param.watch(lambda event: self.stimulation_params.update_output(), list(stage.param))

            stage.param.watch(lambda event: self.trigger_params.update_output(), list(stage.param))

            stage.param.watch(lambda event: self.external_signal_params.update_output(), list(stage.param))


    def servable(self):
        return self.tabs.servable()

# Assuming the component classes are defined correctly and include a reference to MainGUI
# And assuming each component class correctly calls self.main_gui.refresh_view() when their state changes
main_gui = MainGUI()
main_gui.servable()