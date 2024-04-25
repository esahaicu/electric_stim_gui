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
import json
import math
import logging
pn.extension('terminal', console_output='disable')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("my_app_logger")


class STGDeviceController:
    def __init__(self, gui_instance, logger):
        self.gui = gui_instance
        self.logger = logger  # Use the passed logger
        self.stim_amplitude_arr = []
        self.stim_duration_arr = []
        self.sync_amplitude_arr = []
        self.sync_duration_arr = []

    def channel_data(self):
        config = self.gui.get_updated_data()
        config["amplitude_microamps"] = self.convert_to_micro(config["amplitude"], config["amplitude_unit"])
        config["pulse_duration_microseconds"] = self.convert_to_micro(config["pulse_duration"], config["pulse_duration_unit"])
        config["duration_between_events_microseconds"] = self.convert_to_micro(config["duration_between_events"], config["duration_between_events_unit"])
        config["time_between_trains_microseconds"] = self.convert_to_micro(config["train_duration"], config["train_duration_unit"])
        config["external_signal_dur_microseconds"] = self.convert_to_micro(config["external_trigger_duration"], config["external_trigger_duration_unit"])
        if config["period_frequency_type"] == 'Frequency':
            period_seconds = 1 / config["period_frequency_value"] if config["period_frequency_value"] else float('inf')
            config["period_microseconds"] = self.convert_to_micro(period_seconds, 's')
        else:
            config["period_microseconds"] = self.convert_to_micro(config["period_frequency_value"], 's')
        return config

    def convert_to_micro(self, value, unit_type):
        unit_conversion_factors = {
            'us': 1, 'ms': 1000, 's': 1000000,
            'uA': 1, 'mA': 1000, 'A': 1000000,
            'uV': 0.001, 'mV': 1, 'V': 1000,
        }
        return value * unit_conversion_factors.get(unit_type, 1)
    def generate_stimulation_and_sync_data(self):
        return 1
    def configure_device_and_send_data(self):
        return 1
    def dat_data(self):
        config = self.channel_data()
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
        
        for train in range(config["total_trains"]):
            for event in range(config["number_of_events"]):
                # Assign waveform-specific values and add pulse data
                if config["waveform"] == "Monophasic":
                    total_time = config["number_of_events"] * (config["pulse_duration_microseconds"] + config["duration_between_events_microseconds"])
                    add_pulse_data(1, 0, 0, config["amplitude_microamps"], config["pulse_duration_microseconds"])
                    add_pulse_data(1, 0, 0, 0, config["duration_between_events_microseconds"])
                    if event == config["number_of_events"] - 1:  # Add rest time at the end of each train, except after the last event
                        add_pulse_data(1, 0, 0, 0, config["time_between_trains_microseconds"] - total_time)
                elif config["waveform"] == "Biphasic":
                    total_time = config["number_of_events"] * (2 * config["pulse_duration_microseconds"] + config["duration_between_events_microseconds"])
                    # Biphasic waveform: first phase amplitude, then negative phase
                    add_pulse_data(1, 0, 0, config["amplitude_microamps"], config["pulse_duration_microseconds"])
                    add_pulse_data(1, 0, 0, -config["amplitude_microamps"], config["pulse_duration_microseconds"])
                    add_pulse_data(1, 0, 0, 0, config["duration_between_events_microseconds"])
                    if event == config["number_of_events"] - 1:
                        add_pulse_data(1, 0, 0, 0, config["time_between_trains_microseconds"] - total_time)
                elif config["waveform"] == "Sinusoidal":
                    total_time = config["number_of_events"] * (config["period_microseconds"] + config["duration_between_events_microseconds"])
                    # For simplicity, assuming each event in a sinusoidal train lasts for 'pulse_duration'
                    add_pulse_data(1, 0, 0, config["amplitude_microamps"], config["pulse_duration_microseconds"])
                    add_pulse_data(1, 0, 0, 0, config["duration_between_events_microseconds"])
                    if event == config["number_of_events"] - 1:
                        add_pulse_data(1, 0, 0, 0, config["time_between_trains_microseconds"] - total_time)

        # Process external signal duration and delay from stimulus for relevant channels
            add_pulse_data(9, 0, 0, 1.000, config["external_trigger_duration"])
            add_pulse_data(9, 0, 0, 0.000, config["time_between_trains_microseconds"]-config["external_trigger_duration"])  # Example for external signal duration
        return channels_data

    def create_dat_file(self, file_path, dat_data):
        config = self.channel_data()
        with open(file_path, 'w') as file:
            # Write header information
            file.write("Multi Channel Systems MC_Stimulus II\n")
            file.write("ASCII import Version 1.10\n\n")
            file.write(f"channels:\t{int(len(dat_data)/2)}\n")
            file.write(f"output mode:\t{'current' if self.gui.modulation_type_group.value == 'Current' else 'voltage'}\n")
            file.write("format:\t5\n\n")
            
            # Iterate over each channel and its data
            for channel, data in dat_data.items():
                file.write(f"channel: {channel}\n")
                file.write("pulse\tvalue\tvalue\ttime\n")
                for row in data:
                    file.write(f"{row['pulse']}\t{row['value1']}\t{row['value2']}\t{row['time']}\n")
                file.write("\n")  # Add an empty line after each channel's data
    
    def start_stimulation(self):
        self.logger.debug("hello")
        self.logger.debug(self.channel_data())
        time.sleep(10)
        self.logger.debug("ALL DONE!")
        return 1

class DynamicStimGui:
    def __init__(self,logger=None):
        self.logger = logger
        self.channel_buttons = {}  # Stores RadioButtonGroup for each channel
        self._setup_widgets()
        self._setup_layout()
        self._connect_callbacks()
        self._setup_finalize_tab()
        self._setup_logging_and_debugger()
        #self.upload_old_settings_button = pn.widgets.FileInput(accept='.json', name='Upload Old Settings')

    def _setup_logging_and_debugger(self):
        # Setup logging and debugger as before
        self.debugger = pn.widgets.Debugger(name='My Debugger', level=logging.DEBUG, 
                                            logger_names=['my_app_logger'], 
                                            formatter_args={'fmt':'%(asctime)s [%(name)s - %(levelname)s]: %(message)s'})    
    def _setup_widgets(self):

        ### THIS IS THE SECTION THAT DEFINES THE EVENT SELECTION

        self.waveform_group = pn.widgets.RadioButtonGroup(name='Waveform Type', options=['Monophasic', 'Biphasic', 'Sinusoidal'], button_type='primary')
        self.modulation_type_group = pn.widgets.RadioButtonGroup(name='Modulation Type', options=['Voltage', 'Current'], button_type='success')
        self.period_frequency_group = pn.widgets.RadioButtonGroup(
            name='Period or Frequency', 
            options=['Period', 'Frequency'], 
            button_type='warning', 
            visible=False  # Initially set to not visible
        )
        # Define sliders
        self.amplitude_slider = pn.widgets.EditableIntSlider(name='Amplitude', start=-100, end=100, step=1, value=0)
        self.pulse_duration_slider = pn.widgets.EditableIntSlider(name='Pulse Duration', start=0, end=1000, step=1, value=100)
        self.number_of_events_input = pn.widgets.IntInput(name='Number of Events', value=1, start=1, end=100)
        self.duration_between_events_slider = pn.widgets.EditableIntSlider(name='Duration Between Events', start=0, end=1000, step=1, value=100, visible=False)
        self.period_frequency_value_input = pn.widgets.IntInput(name='Period', start=1, end=1000, visible=False)
        
        # Define randomize buttons
        self.randomize_amplitude = pn.widgets.Button(name='Randomize', button_type='warning')
        self.randomize_pulse_duration = pn.widgets.Button(name='Randomize', button_type='warning')
        self.randomize_number_of_events = pn.widgets.Button(name='Randomize', button_type='warning')
        self.randomize_duration_between_events = pn.widgets.Button(name='Randomize', button_type='warning', visible=False)
        self.randomize_period_frequency_value = pn.widgets.Button(name='Randomize', button_type='warning', visible=False)
        
        self.phase_text = pn.pane.Markdown(visible=False)
        self.sinusoidal_calculation_text = pn.pane.Markdown(visible=False)

        # Define Unit Selectors
        self.amplitude_unit_selector = pn.widgets.RadioButtonGroup(
            name='Amplitude Unit', options=['uA', 'mA', 'A'], button_type='default')
        self.pulse_duration_unit_selector = pn.widgets.RadioButtonGroup(
            name='Duration Unit', options=['us', 'ms', 's'], button_type='default', visible=False)
        self.period_frequency_unit_selector = pn.widgets.RadioButtonGroup(
            name='Period/Frequency Unit', options=['us', 'ms', 's'], button_type='default', visible=False)
        self.duration_between_events_unit_selector = pn.widgets.RadioButtonGroup(
            name='Duration Between Events Unit', options=['us', 'ms', 's'], button_type='default', visible=False)

        # Defining the range sliders
        self.amplitude_range_slider = pn.widgets.EditableRangeSlider(name='Random Amplitude Range', start=-100, end=100, value=(-100, 100), step=1)
        self.pulse_duration_range_slider = pn.widgets.EditableRangeSlider(name='Random Pulse Duration Range', start=0, end=1000, value=(0, 1000), step=1)
        self.period_frequency_range_slider = pn.widgets.EditableRangeSlider(name='Random Period/Frequency Range', start=1, end=1000, value=(1, 1000), step=1)
        self.number_of_events_range_slider = pn.widgets.EditableRangeSlider(name='Random Number of Events Range', start=1, end=1000, value=(1, 1000), step=1)
        self.duration_between_events_range_slider = pn.widgets.EditableRangeSlider(name='Duration Between Events Range', start=0, end=1000, value=(0, 1000), step=1)


        ### TRAIN WIDGETS
        self.number_of_trains_input = pn.widgets.IntInput(name='Number of Trains', value=1, start=1, end=100)
        self.train_duration_slider = pn.widgets.EditableIntSlider(name='Minimum Train Duration', start=0, end=1000000, step=1, value=100)
        self.randomize_number_of_trains = pn.widgets.Button(name='Randomize', button_type='warning')
        self.randomize_train_duration = pn.widgets.Button(name='Randomize', button_type='warning')
        self.accept_external_trigger = pn.widgets.Toggle(name='Accept External Trigger for Train?', value=False)
        # Additional widgets for Train Settings
        self.number_of_trains_range_slider = pn.widgets.EditableRangeSlider(name='Random Number of Trains Range', start=1, end=100, value=(1, 100), step=1)
        self.train_duration_unit_selector = pn.widgets.RadioButtonGroup(name='Train Duration Unit', options=['us', 'ms', 's'], button_type='default')
        self.train_duration_range_slider = pn.widgets.EditableRangeSlider(name='Random Train Duration Range', start=0, end=100000, value=(0, 1000), step=1)




        # External Trigger Widgets
        self.external_trigger_duration = pn.widgets.EditableFloatSlider(name='External Trigger Duration', start=0, end=1000000, step=1, value=100)
        self.randomize_external_trigger = pn.widgets.Button(name='Randomize', button_type='warning')
        self.set_to_pulse_duration = pn.widgets.Button(name='Set to Pulse Duration', button_type='primary')
        self.external_trigger_duration_unit_selector = pn.widgets.RadioButtonGroup(name='External Trigger Duration Unit', options=['us', 'ms', 's'], button_type='default')
        self.external_trigger_duration_range_slider = pn.widgets.RangeSlider(name='Random External Trigger Duration Range', start=0, end=100000, value=(0, 1000), step=1)

        ### CHANNEL CHOOSING WIDGETS
        self.channel_select_widgets = []  # This should store the radio button widgets for access in randomization

        for i in range(1, 17):
            # Using f-string for name might not be necessary for RadioButtonGroup, but helpful for debugging
            radio_button_group = pn.widgets.RadioButtonGroup(
                name=f'Channel {i}', options=['Floating', 'Cathode', 'Anode', 'Ground'], 
                button_type='danger', button_style='outline',
                value='Floating'  # Default to 'Floating'
            )
            self.channel_select_widgets.append(radio_button_group)  # Store the widget for later reference

        self.random_ca_button = pn.widgets.Button(name="Random Cathode/Anode", button_type="success")


        ### SELECTION PANE


    def _setup_layout(self):
        event_settings_layout = pn.Column(
            # Waveform selection and modulation type
            self.waveform_group,
            self.modulation_type_group,
            
            # Amplitude setting with unit selector and randomize options
            pn.Row(
                self.amplitude_slider, 
                self.amplitude_unit_selector, 
                self.randomize_amplitude,
                self.amplitude_range_slider),  # Amplitude range slider
            
            # Pulse duration with unit selector and randomize options
            pn.Row(
                self.pulse_duration_slider, 
                self.pulse_duration_unit_selector, 
                self.randomize_pulse_duration,
                self.pulse_duration_range_slider),  # Pulse duration range slider
            
            # Period or frequency with unit selector and randomize options
            self.period_frequency_group,
            pn.Row(
                self.period_frequency_value_input, 
                self.period_frequency_unit_selector, 
                self.randomize_period_frequency_value,
                self.period_frequency_range_slider),  # Period/Frequency range slider
            pn.Row(
                self.number_of_events_input,
                self.randomize_number_of_events,
                self.number_of_events_range_slider),
            # Duration between events with unit selector and randomize options
            pn.Row(
                self.duration_between_events_slider, 
                self.duration_between_events_unit_selector, 
                self.randomize_duration_between_events,
                self.duration_between_events_range_slider),  # Duration between events range slider
            
            # Dynamic text updates based on waveform type
            self.phase_text,
            self.sinusoidal_calculation_text,
        )

        # Train Settings layout
        train_settings_layout = pn.Column(
            self.accept_external_trigger,
            pn.Row(self.number_of_trains_input, self.randomize_number_of_trains, self.number_of_trains_range_slider),
            pn.Row(self.train_duration_slider, self.train_duration_unit_selector, self.randomize_train_duration, self.train_duration_range_slider),
        )        
        external_trigger_layout = pn.Column(
            pn.Row(self.external_trigger_duration, self.external_trigger_duration_unit_selector, self.randomize_external_trigger, self.external_trigger_duration_range_slider),
            self.set_to_pulse_duration,
        )
        

        # GRAPHS LAYOUT
        self.projected_graphs_layout = pn.Column(

        ) 

        # CHANNEL SELECTION LAYOUT
        self.channel_select_layout = pn.Column(sizing_mode='stretch_width')
        for i, widget in enumerate(self.channel_select_widgets, start=1):
            self.channel_select_layout.append(pn.Row(pn.pane.Markdown(f"**Channel {i}:**"), widget))
        self.channel_select_layout.append(self.random_ca_button)

        # Combine into tabs
        self.tabs = pn.Tabs(
            ('Event Settings', event_settings_layout),
            ('Train Settings', train_settings_layout),
            ('External Trigger Settings', external_trigger_layout),
            ('Projected Graphs', self.projected_graphs_layout),
            ('Channel Select', self.channel_select_layout)
        )
        self._update_visibility_and_content()
    def _connect_callbacks(self):
        #Event Settings
        self.waveform_group.param.watch(self._update_visibility_and_content, 'value')
        self.number_of_events_input.param.watch(self._update_visibility_and_content, 'value')
        self.amplitude_slider.param.watch(self._update_visibility_and_content, 'value')
        self.period_frequency_group.param.watch(self._update_visibility_and_content, 'value')
        self.period_frequency_value_input.param.watch(self._update_visibility_and_content, 'value')
        self.modulation_type_group.param.watch(self._update_visibility_and_content, 'value')
        #self.phase_text.param.watch(self._update_visibility_and_content, 'value')

        # Randomize button clicks
        self.randomize_amplitude.on_click(self._randomize_amplitude)
        self.randomize_pulse_duration.on_click(self._randomize_pulse_duration)
        self.randomize_number_of_events.on_click(self._randomize_number_of_events)
        self.randomize_duration_between_events.on_click(self._randomize_duration_between_events)
        self.randomize_period_frequency_value.on_click(self._randomize_period_frequency_value)

        # No 'on_click' event for RangeSlider or Select widget, use 'value' watchers
        # No actions defined in your provided code for unit selectors, assuming no direct action needed

        # Adding missing param.watch for range sliders - should watch 'value', not 'on_click'
        self.amplitude_range_slider.param.watch(lambda event: self._update_range('amplitude', event.new), 'value')
        self.pulse_duration_range_slider.param.watch(lambda event: self._update_range('pulse_duration', event.new), 'value')
        self.period_frequency_range_slider.param.watch(lambda event: self._update_range('period_frequency', event.new), 'value')
        self.duration_between_events_range_slider.param.watch(lambda event: self._update_range('duration_between_events', event.new), 'value')


        #Train Settings
        self.number_of_trains_input.param.watch(self._update_train_settings, 'value')
        self.train_duration_slider.param.watch(self._update_train_settings, 'value')
        self.accept_external_trigger.param.watch(self._update_train_settings_visibility, 'value')
        self.randomize_number_of_trains.on_click(self._randomize_number_of_trains)
        self.randomize_train_duration.on_click(self._randomize_train_duration)
        

        # Add watchers for the new range sliders and unit selectors
        self.train_duration_unit_selector.param.watch(self._update_train_settings, 'value')
        self.train_duration_range_slider.param.watch(lambda event: self._randomize_train_duration_range(event.new), 'value')
        # Ensure updates to Train Duration are based on Event Settings

        #External Trigger Settings
        self.randomize_external_trigger.on_click(self._randomize_external_trigger)
        self.set_to_pulse_duration.on_click(self._on_event_settings_changed)
        #self.external_trigger_duration_unit_selector.param.watch(self._on_event_settings_changed, 'value')
        self.external_trigger_duration_range_slider.param.watch(lambda event: self._randomize_external_trigger_duration_range(event.new), 'value')

        # Ensure updates based on event settings changes
        self.amplitude_slider.param.watch(lambda event: self._update_time_based_on_event_settings(), 'value')
        self.pulse_duration_slider.param.watch(self._on_event_settings_changed, 'value')
        self.duration_between_events_slider.param.watch(self._on_event_settings_changed, 'value')
        self.number_of_events_input.param.watch(self._on_event_settings_changed, 'value')
        #self.pulse_duration_unit_selector.watch(self._on_event_settings_changed, 'value')
        #self.duration_between_events_unit_selector.watch(self._on_event_settings_changed, 'value')

    def _on_event_settings_changed(self, event):
        self._update_external_trigger_settings_based_on_event_duration()

        #GRAPHING
        self.amplitude_slider.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.waveform_group.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.number_of_events_input.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.period_frequency_group.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.period_frequency_value_input.param.watch(lambda event: self.update_projected_graphs(), 'value')

        self.number_of_trains_input.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.train_duration_slider.param.watch(lambda event: self.update_projected_graphs(), 'value')
        
        self.accept_external_trigger.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.external_trigger_duration.param.watch(lambda event: self.update_projected_graphs(), 'value')
        

        #   selectors
        self.amplitude_unit_selector.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.period_frequency_unit_selector.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.duration_between_events_unit_selector.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.train_duration_unit_selector.param.watch(lambda event: self.update_projected_graphs(), 'value')
        self.external_trigger_duration_unit_selector.param.watch(lambda event: self.update_projected_graphs(), 'value')


        ### Channel Setting
        self.random_ca_button.on_click(self.randomize_cathode_anode)


    def _update_visibility_and_content(self, event=None):
        is_sinusoidal = self.waveform_group.value == 'Sinusoidal'
        is_period_selected = self.period_frequency_group.value == 'Period'

        # Update visibility based on waveform type
        self.pulse_duration_slider.visible = not is_sinusoidal
        self.pulse_duration_unit_selector.visible = not is_sinusoidal and self.pulse_duration_slider.visible  # Ensure units follow the same visibility
        self.randomize_pulse_duration.visible = not is_sinusoidal  # Update to ensure range slider follows visibility
        self.pulse_duration_range_slider.visible = not is_sinusoidal  # Update to ensure range slider follows visibility
        
        # Period/Frequency visibility logic
        self.period_frequency_group.visible = is_sinusoidal
        self.period_frequency_value_input.visible = is_sinusoidal
        self.period_frequency_unit_selector.visible = is_sinusoidal and is_period_selected
        self.period_frequency_range_slider.visible = is_sinusoidal  # Ensure it's only visible when 'Period' is selected
        self.randomize_period_frequency_value.visible = is_sinusoidal

        self.duration_between_events_slider.visible = self.number_of_events_input.value > 1
        self.duration_between_events_unit_selector.visible = self.number_of_events_input.value > 1  # Show/Hide unit selector for duration between events
        self.randomize_duration_between_events.visible = self.number_of_events_input.value > 1
        self.duration_between_events_range_slider.visible = self.number_of_events_input.value > 1  # Show/Hide range slider for duration between events

        
        
        # Update unit selectors based on modulation type
        if self.modulation_type_group.value == 'Current':
            self.amplitude_unit_selector.options = ['uA', 'mA', 'A']
        else:  # Voltage
            self.amplitude_unit_selector.options = ['uV', 'mV', 'V']
        
        # Biphasic-specific logic
        if self.waveform_group.value == 'Biphasic':
            if self.amplitude_slider.value < 0:
                self.phase_text.object = "Phase: Cathode Leading"
            elif self.amplitude_slider.value > 0:
                self.phase_text.object = "Phase: Anode Leading"
            else:
                self.phase_text.object = "Phase: Neither"
            self.phase_text.visible = True  # Show the text only if 'Biphasic' is selected
        else:
            self.phase_text.visible = False  # Hide the text for non-Biphasic waveforms

        # Update text and calculations for sinusoidal waveform
        if is_sinusoidal:
            self.period_frequency_value_input.name = self.period_frequency_group.value
            if self.period_frequency_group.value == 'Period':
                freq = 1 / self.period_frequency_value_input.value if self.period_frequency_value_input.value != 0 else 0
                self.sinusoidal_calculation_text.object = f"Calculated Frequency: {freq} Hz"
            else:
                period = 1 / self.period_frequency_value_input.value if self.period_frequency_value_input.value != 0 else 0
                self.sinusoidal_calculation_text.object = f"Calculated Period: {period} seconds"
            self.sinusoidal_calculation_text.visible = True  # Show the text only if 'Biphasic' is selected
        else:
            self.sinusoidal_calculation_text.visible = False


    def _randomize_amplitude(self, event):
        self.amplitude_slider.value = random.randint(*self.amplitude_range_slider.value)

    def _randomize_pulse_duration(self, event):
        self.pulse_duration_slider.value = random.randint(*self.pulse_duration_range_slider.value)

    def _randomize_period_frequency_value(self, event):
        self.period_frequency_value_input.value = random.randint(*self.period_frequency_range_slider.value)
    
    def _randomize_number_of_events(self, event):
        self.number_of_events_input.value = random.randint(*self.number_of_events_range_slider.value)

    def _randomize_duration_between_events(self, event):
        self.duration_between_events_slider.value = random.randint(*self.duration_between_events_range_slider.value)

    def _update_train_settings(self, event):
        # Calculate the minimum value for the train duration slider
        duration_between_events = self.duration_between_events_slider.value if self.number_of_events_input.value > 1 else 0
        if self.waveform_group.value == 'Monophasic':
            min_duration = (self.pulse_duration_slider.value + duration_between_events) * self.number_of_events_input.value
        elif self.waveform_group.value == 'Biphasic':
            min_duration = (2 * self.pulse_duration_slider.value + duration_between_events) * self.number_of_events_input.value
        elif self.waveform_group.value == 'Sinusoidal':
            min_duration = (self.period_frequency_value_input.value + duration_between_events) * self.number_of_events_input.value
        self.train_duration_slider.start = max(0, min_duration)  # Ensure minimum is not negative

    def _update_train_settings_visibility(self, event):
        is_external = self.accept_external_trigger.value
        self.number_of_trains_input.visible = not is_external
        self.train_duration_slider.visible = not is_external
        self.randomize_number_of_trains.visible = not is_external
        self.randomize_train_duration.visible = not is_external
    def _randomize_number_of_trains(self, event):
        self.number_of_trains_input.value = np.random.randint(self.number_of_trains_input.start, self.number_of_trains_input.end)

    def _randomize_train_duration(self, event):
        self.train_duration_slider.value = np.random.randint(self.train_duration_slider.start, self.train_duration_slider.end)

    # EXTERNAL TRIGGER
    def _randomize_external_trigger(self, event):
        max_duration = self.train_duration_slider.value  # Assuming this is the maximum
        self.external_trigger_duration.value = np.random.randint(0, max_duration + 1)
    
    def _calculate_total_event_duration(self):
        # Assuming the pulse_duration_slider value is in the unit selected in pulse_duration_unit_selector
        unit_multiplier = {'us': 1, 'ms': 1000, 's': 1000000}
        pulse_duration_in_us = self.pulse_duration_slider.value * unit_multiplier[self.pulse_duration_unit_selector.value]
        
        # Same for duration between events
        duration_between_events_in_us = self.duration_between_events_slider.value * unit_multiplier[self.duration_between_events_unit_selector.value]
        
        # Total duration of all events in microseconds
        total_event_duration_in_us = (pulse_duration_in_us + duration_between_events_in_us) * self.number_of_events_input.value
        return total_event_duration_in_us
    
    def _convert_duration_and_unit(self, duration_microseconds):
        if duration_microseconds >= 1000000:  # More than 1 second
            return 's', duration_microseconds / 1000000
        elif duration_microseconds >= 1000:  # More than 1 millisecond
            return 'ms', duration_microseconds / 1000
        else:
            return 'us', duration_microseconds

    def _update_external_trigger_settings_based_on_event_duration(self):
        total_event_duration_in_us = self._calculate_total_event_duration()
        recommended_unit, converted_duration = self._convert_duration_and_unit(total_event_duration_in_us)
        
        # Update the external trigger duration unit selector and value
        self.external_trigger_duration_unit_selector.value = recommended_unit
        self.external_trigger_duration.value = converted_duration
    def _update_time_based_on_event_settings(self):
        # Example of calculating total event duration and deciding the unit
        total_duration = self._calculate_total_event_duration()
        recommended_unit, converted_duration = self._convert_duration_and_unit(total_duration)

        # Update external trigger duration and unit based on calculations
        self.external_trigger_duration_unit_selector.value = recommended_unit
        self.external_trigger_duration.value = converted_duration

        # You might need a similar method for updating train settings

    def _convert_duration_and_unit(self, duration_microseconds):
        if duration_microseconds >= 1_000_000:  # More than 1 second
            return 's', duration_microseconds / 1_000_000
        elif duration_microseconds >= 1_000:  # More than 1 millisecond
            return 'ms', duration_microseconds / 1_000
        else:
            return 'us', duration_microseconds

    def _randomize_train_duration_range(self, new_range):
        # Assuming new_range is a tuple (min, max)
        self.train_duration_slider.value = random.randint(new_range[0], new_range[1])

    def _randomize_external_trigger_duration_range(self, new_range):
        # Adjust the external trigger duration within the new range
        self.external_trigger_duration.value = random.randint(new_range[0], new_range[1])

    
    #GRAPHING
    def update_projected_graphs(self):
        unit_multiplier = {'us': 1, 'ms': 1000, 's': 1000000}
        unit_multiplier_volt = {'uV': 1, 'mV': 1000, 'V': 1000000}
        unit_multiplier_amp = {'uA': 1, 'mA': 1000, 'A': 1000000}
        
        # Calculate necessary values
        pulse_duration_us = self.pulse_duration_slider.value * unit_multiplier[self.pulse_duration_unit_selector.value]
        duration_between_events_us = self.duration_between_events_slider.value * unit_multiplier[self.duration_between_events_unit_selector.value]
        trigger_duration_us = self.external_trigger_duration.value * unit_multiplier[self.external_trigger_duration_unit_selector.value]
        
        # Decide amplitude unit multiplier based on modulation type
        if self.modulation_type_group.value == 'Voltage':
            #amplitude_uA_uV = self.amplitude_slider.value * unit_multiplier_volt[self.amplitude_unit_selector.value]
            modulation_type_val = self.amplitude_unit_selector.value
        else:  # Current
            #amplitude_uA_uV = self.amplitude_slider.value * unit_multiplier_amp[self.amplitude_unit_selector.value]
            modulation_type_val = self.amplitude_unit_selector.value
        
        delay_between_trains_us = self.train_duration_slider.value * unit_multiplier[self.train_duration_unit_selector.value]
        # Generate the single event plot
        single_event_plot = self.generate_single_event_plot(
            self.amplitude_slider.value, 
            pulse_duration_us, 
            self.waveform_group.value, 
            trigger_duration_us,
            duration_between_events_us if self.number_of_events_input.value > 1 else 0, 
            self.number_of_events_input.value, 
            self.period_frequency_value_input.value,
            self.period_frequency_group.value,
            modulation_type_val
        )
        full_sequence_plot = self.generate_full_sequence_plot(
            self.amplitude_slider.value, 
            pulse_duration_us, 
            self.waveform_group.value,
            self.number_of_events_input.value,
            duration_between_events_us,
            trigger_duration_us,
            self.number_of_trains_input.value,
            delay_between_trains_us,
            self.period_frequency_value_input.value,
            self.period_frequency_group.value,
            modulation_type_val

        )

        self.projected_graphs_layout.clear()
        self.projected_graphs_layout.extend([pn.panel(single_event_plot), pn.panel(full_sequence_plot)])

    def generate_single_event_plot(self, amplitude, pulse_duration, waveform_type, trigger_duration, duration_between_events, number_of_events, period_frequency, period_frequency_type, modulation_type):
        # Logic for single event plot generation adjusted for correct sine wave...
        event_duration = self._calculate_event_length(waveform_type, pulse_duration, duration_between_events, number_of_events)
        time = np.linspace(-event_duration/10, event_duration+event_duration/10, 10000)
        pulse = np.zeros_like(time)
        #print(np.shape(pulse))
        trigger = np.zeros_like(time)
        trigger_height = amplitude if amplitude > 0 else -amplitude
        
        for i in range(number_of_events):
            #print(start_time,end_time)
            if waveform_type == 'Monophasic':
                start_time = i * (pulse_duration + duration_between_events)
                end_time = start_time + duration_between_events
                pulse[(time >= start_time) & (time < end_time)] = amplitude
            elif waveform_type == 'Biphasic':
                start_time = i * (2*pulse_duration + duration_between_events)
                end_time = start_time + 2*pulse_duration
                pulse[(time >= start_time) & (time < start_time + pulse_duration)] = amplitude
                pulse[(time >= start_time + pulse_duration) & (time < end_time)] = -amplitude
            else:
                break

        if waveform_type == 'Sinusoidal':
            if period_frequency_type == 'Period':
                wave_duration = period_frequency
            else:  # Frequency given
                wave_duration = 1 / period_frequency if period_frequency != 0 else 0
            total_duration = number_of_events * wave_duration + (number_of_events - 1) * duration_between_events
            time = np.linspace(total_duration/50, total_duration+total_duration/50, 10000)
            pulse = np.zeros_like(time)
            trigger = np.zeros_like(time)
            trigger_height = amplitude if amplitude > 0 else -amplitude
            event_duration = number_of_events * (wave_duration + duration_between_events)
            for i in range(number_of_events):
                start_time = i * (wave_duration + duration_between_events)
                end_time = start_time + wave_duration
                condition_mask = (time >= start_time) & (time < end_time)
                num_points = condition_mask.sum()  # Number of points where the condition is True
                sine_time = np.linspace(0, wave_duration, num_points)  # Use num_points to match the target segment size
                pulse[condition_mask] = amplitude * np.sin(2 * np.pi * sine_time / wave_duration)
        # Trigger waveform
        trigger_start = 0  # Assuming trigger starts with the event
        trigger_end = trigger_duration
        trigger[(time >= trigger_start) & (time <= trigger_end)] = trigger_height

        df = pd.DataFrame({'Time': time, 'Pulse': pulse, 'Trigger': trigger})
        plot = df.hvplot.line(
            x='Time', y=['Pulse', 'Trigger'], color=['blue', 'red'], height=400, width=600,
            xlim=(-event_duration / 10, event_duration + event_duration / 10),  # Example axis limits
            ylim=(-1.1 * abs(amplitude), 1.1 * abs(amplitude)),
            xlabel='Time (us)', ylabel=f'Amplitude ({modulation_type})'
        ).opts(title="Single Event Plot", framewise=True, shared_axes=False)
        return plot


    def generate_full_sequence_plot(self, amplitude, pulse_duration, waveform_type, number_of_events, duration_between_events, trigger_duration, number_of_trains, delay_between_trains, period_frequency, period_frequency_type, modulation_type):
        
        if waveform_type == 'Sinusoidal':
            # Calculate waveform duration based on input type (period or frequency)
            if period_frequency_type == 'Period':
                wave_duration = period_frequency
            else:  # Frequency given
                wave_duration = 1 / period_frequency if period_frequency != 0 else 0
            event_duration = number_of_events * (wave_duration + duration_between_events)
            total_duration = number_of_trains * (number_of_events * (wave_duration + duration_between_events) - duration_between_events) + (number_of_trains - 1) * delay_between_trains
            time = np.linspace(0, total_duration, int(10000 * total_duration / event_duration))
            pulse = np.zeros_like(time)
            trigger = np.zeros_like(time)
            trigger_height = amplitude if amplitude > 0 else -amplitude

            for n in range(number_of_trains):
                train_start_time = n * (number_of_events * (wave_duration + duration_between_events) - duration_between_events + delay_between_trains)
                for i in range(number_of_events):
                    start_time = train_start_time + i * (wave_duration + duration_between_events)
                    end_time = start_time + wave_duration
                    mask = (time >= start_time) & (time < end_time)
                    num_points = np.sum(mask)
                    sine_wave = amplitude * np.sin(2 * np.pi * np.linspace(0, wave_duration, num_points) / wave_duration)
                    pulse[mask] = sine_wave

            # Setting up the trigger for each event
            for n in range(number_of_trains):
                for i in range(number_of_events):
                    trigger_start_time = n * (number_of_events * (wave_duration + duration_between_events) - duration_between_events + delay_between_trains) + i * (wave_duration + duration_between_events)
                    trigger_end_time = trigger_start_time + trigger_duration
                    trigger[(time >= trigger_start_time) & (time < trigger_end_time)] = trigger_height
            total_simulation_duration=total_duration
        else:
        # Determine the total duration of a single train including delays between events
            single_train_duration = self._calculate_event_length(waveform_type, pulse_duration, duration_between_events, number_of_events)
            
            # Total simulation time includes all trains and delays between them
            total_simulation_duration = number_of_trains * single_train_duration + (number_of_trains - 1) * delay_between_trains
            
            time = np.linspace(0, total_simulation_duration, 10000 * number_of_trains)
            pulse = np.zeros_like(time)

            for n in range(number_of_trains):
                train_start_time = n * (single_train_duration + delay_between_trains)
                
                for i in range(number_of_events):                
                    if waveform_type == 'Monophasic':
                        event_start_time = train_start_time + i * (pulse_duration + duration_between_events)
                        event_end_time = event_start_time + pulse_duration
                        pulse[(time >= event_start_time) & (time < event_end_time)] = amplitude
                    elif waveform_type == 'Biphasic':
                        event_start_time = train_start_time + i * (pulse_duration + duration_between_events)
                        event_end_time = event_start_time + 2* pulse_duration
                        pulse[(time >= event_start_time) & (time < event_start_time + pulse_duration)] = amplitude
                        pulse[(time >= event_start_time + pulse_duration) & (time < event_end_time)] = -amplitude            
            # Assuming the trigger starts with the first event of each train and lasts for 'trigger_duration'
                trigger = np.zeros_like(time)
                for n in range(number_of_trains):
                    train_start_time = n * (single_train_duration + delay_between_trains)
                    trigger_start_time = train_start_time
                    trigger_end_time = trigger_start_time + trigger_duration
                    trigger[(time >= trigger_start_time) & (time <= trigger_end_time)] = amplitude if amplitude > 0 else -amplitude

        df = pd.DataFrame({'Time': time, 'Pulse': pulse, 'Trigger': trigger})
        plot = df.hvplot.line(
            x='Time', y='Pulse', color='blue', height=400, width=800,
            xlim=(0, total_simulation_duration),
            ylim=(-1.1 * abs(amplitude), 1.1 * abs(amplitude)),
            xlabel='Time (us)', ylabel=f'Amplitude ({modulation_type})'
        ).opts(title="Full Sequence Plot", framewise=True, shared_axes=False) * \
        df.hvplot.line(x='Time', y='Trigger', color='red', height=400, width=800).opts(framewise=True, shared_axes=False)
        return plot



    def _calculate_event_length(self, waveform_type, pulse_duration, duration_between_events, number_of_events):
        # Here's a basic calculation. Adjust according to your waveform definitions.
        if waveform_type == 'Monophasic':
            return (pulse_duration + duration_between_events) * number_of_events 
        elif waveform_type == 'Biphasic':
            return (2 * pulse_duration + duration_between_events)  * number_of_events   # Considering both phases
        elif waveform_type == 'Sinusoidal':
            # Assuming 'pulse_duration' represents one full cycle of the sine wave
            return (pulse_duration + duration_between_events)  * number_of_events
        else:
            return 0  # Default case, should not happen




    def randomize_cathode_anode(self, event=None):
        # First, ensure all channels are reset to 'Floating'
        for widget in self.channel_select_widgets:
            widget.value = 'Floating'
        
        # Randomly pick two distinct channels
        cathode_channel, anode_channel = random.sample(range(len(self.channel_select_widgets)), 2)
        
        # Assign one channel to 'Cathode' and the other to 'Anode'
        self.channel_select_widgets[cathode_channel].value = 'Cathode'
        self.channel_select_widgets[anode_channel].value = 'Anode'





    def _setup_finalize_tab(self):
        self.comment_input = pn.widgets.TextInput(name="Comments", placeholder="Add any comment here...")
        self.save_config_button = pn.widgets.Button(name="Save Configuration", button_type="primary")
        self.save_dat_button = pn.widgets.Button(name="Save .dat File", button_type="success")
        self.run_stimulation_button = pn.widgets.Button(name="Run Stimulation", button_type="primary")
        self.back_button = pn.widgets.Button(name="Back", button_type="danger", visible=False)
        self.directory_selector = pn.widgets.FileSelector('~')
        self.download_json = pn.widgets.Button(name="Download .JSON", button_type="success", visible=False)
        self.download_dat = pn.widgets.Button(name="Download .DAT", button_type="success", visible=False)
        self.start_run = pn.widgets.Button(name="START", button_type="success", visible=False)
        self.filename_input = pn.widgets.TextInput(name="Filename", placeholder="Enter filename here", visible=False)
        self.file_extension_label_json = pn.pane.Markdown(".json", visible=False)  # Default to .json; adjust as needed
        self.file_extension_label_dat = pn.pane.Markdown(".dat", visible=False)  # Default to .dat; adjust as needed    
        self.file_extension_label_csv = pn.pane.Markdown(".csv", visible=False)  # Default to .csv; adjust as needed    
        self.progress_bar = pn.widgets.Progress(name='Stimulation Progress', value=0, max=100, visible=False)  # Progress bar initialization

        # Setup the FileDownload widget without a file for now
        self.file_download = pn.widgets.FileDownload(filename='', label='Download File', button_type='primary', auto=False, visible=False)

        self.upload_settings_button = pn.widgets.FileInput(accept='.json')

        self.debug = pn.widgets.Debugger(name='My Debugger')

        # Connecting buttons to their callbacks
        self.save_config_button.on_click(self.set_configuration)
        self.save_dat_button.on_click(self.set_dat_file)
        self.run_stimulation_button.on_click(self.set_run)
        self.back_button.on_click(self.show_original_finalize_layout)
        self.download_json.on_click(self.download_configuration)
        self.download_dat.on_click(self.download_dat_file)
        self.start_run.on_click(self.run_stimulation)
        self.upload_settings_button.param.watch(self.load_settings_from_file, 'value')
        self.progress_bar.param.watch(lambda event: self.schedule_progress_update())
        #self.debug.param.watch(self.running_program())
        
        self.dynamic_finalize_layout = pn.Column(
            self.comment_input,
            self.save_config_button,
            self.save_dat_button,
            self.run_stimulation_button,
            self.upload_settings_button,
            #self.file_download  # Include the FileDownload widget in the layout
        )
        self.table = pn.pane.DataFrame(pd.DataFrame())
        self.finalize_tab_layout = pn.Row(self.table, self.dynamic_finalize_layout)
        #self.update_table_data(None)
        self.on_any_change(None)
        self.tabs.append(('Finalize', self.finalize_tab_layout))
    
    def schedule_progress_update(self, progress):
        """Schedules a progress bar update on the next tick."""
        def callback():
            # Update the progress bar value
            self.progress_bar.value = int(progress)
        
        # Schedule the callback to be run at the next opportunity
        pn.state.curdoc().add_next_tick_callback(callback)

    def set_configuration(self, event):
        self.dynamic_finalize_layout.clear()
        self.dynamic_finalize_layout.extend([
            pn.pane.Markdown('You are almost there! Set the file location for your .json file.'),
            self.back_button,
            pn.Row(self.filename_input,self.file_extension_label_json),
            self.directory_selector,
            self.download_json
        ])
        self.back_button.visible = True
        self.directory_selector.visible = True
        self.download_json.visible = True
        self.filename_input.visible = True
        self.file_extension_label_json.visible = True

    def set_dat_file(self, event):
        self.dynamic_finalize_layout.clear()
        self.dynamic_finalize_layout.extend([
            pn.pane.Markdown('You are almost there! Set the file location for your .dat file.'),
            self.back_button,
            pn.Row(self.filename_input, self.file_extension_label_dat),
            self.directory_selector,
            self.download_dat
        ])
        self.filename_input.visible = True
        self.back_button.visible = True
        self.directory_selector.visible = True
        self.download_dat.visible = True
        self.file_extension_label_dat.visible = True
    def download_csv_file(self,event):
        selected_directory = self.directory_selector.value[0]  # Assuming the directory is the first selected item
        filename = f"{self.filename_input.value}.csv"
        config = self.get_updated_data()
        df = pd.DataFrame(list(config.items()), columns=['Name', 'Value'])
        # Exporting the DataFrame to a CSV file
        csv_path = os.path.join(selected_directory, filename)  # Combine into a full path
        df.T.to_csv(csv_path, index=False)

    def download_configuration(self, event):
        # Save the current configuration to a JSON file
        selected_directory = self.directory_selector.value[0]  # Assuming the directory is the first selected item
        filename = f"{self.filename_input.value}.json"  # Construct filename with extension
        config_path = os.path.join(selected_directory, filename)  # Combine into a full path
        config = {
            "waveform": self.waveform_group.value,
            "modulation_type": self.modulation_type_group.value,
            "amplitude": self.amplitude_slider.value,
            "pulse_duration": self.pulse_duration_slider.value,
            "number_of_events": self.number_of_events_input.value,
            "duration_between_events": self.duration_between_events_slider.value,
            "period_frequency_type": self.period_frequency_group.value,  # 'Period' or 'Frequency'
            "period_frequency_value": self.period_frequency_value_input.value,
            "total_trains": self.number_of_trains_input.value,
            "train_duration": self.train_duration_slider.value,
            "accept_external_trigger": self.accept_external_trigger.value,
            "external_trigger_duration": self.external_trigger_duration.value,
            # Add amplitude, pulse_duration, and duration units if you need them
            "amplitude_unit": self.amplitude_unit_selector.value,
            "pulse_duration_unit": self.pulse_duration_unit_selector.value,
            "duration_between_events_unit": self.duration_between_events_unit_selector.value,
            "train_duration_unit": self.train_duration_unit_selector.value,
            "external_trigger_duration_unit": self.external_trigger_duration_unit_selector.value,
            # Channel configurations
            "channel_configurations": {f"Channel {i+1}": widget.value for i, widget in enumerate(self.channel_select_widgets)}
        }

        # Define the path where the config JSON will be saved
        #config_path = os.path.join(os.getcwd(), 'config.json')

        # Write the configuration dictionary to a JSON file
        #with open(config_path, 'w') as f:
        #    json.dump(config, f, indent=4)  # Use indent for pretty-printing
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)

        # Show the UI elements for downloading the saved configuration
        self.show_original_finalize_layout()
        #self.switch_to_file_save_ui('Configuration saved. Ready to download.')
    def get_updated_data(self):
        config = {
            "waveform": self.waveform_group.value,
            "modulation_type_group": self.modulation_type_group.value,
            "amplitude": self.amplitude_slider.value,
            "pulse_duration": self.pulse_duration_slider.value,
            "number_of_events": self.number_of_events_input.value,
            "duration_between_events": self.duration_between_events_slider.value,
            "period_frequency_type": self.period_frequency_group.value,  # 'Period' or 'Frequency'
            "period_frequency_value": self.period_frequency_value_input.value,
            "total_trains": self.number_of_trains_input.value,
            "train_duration": self.train_duration_slider.value,
            "accept_external_trigger": self.accept_external_trigger.value,
            "external_trigger_duration": self.external_trigger_duration.value,
            # Add amplitude, pulse_duration, and duration units if you need them
            "amplitude_unit": self.amplitude_unit_selector.value,
            "pulse_duration_unit": self.pulse_duration_unit_selector.value,
            "duration_between_events_unit": self.duration_between_events_unit_selector.value,
            "train_duration_unit": self.train_duration_unit_selector.value,
            "external_trigger_duration_unit": self.external_trigger_duration_unit_selector.value,
            # Channel configurations
            "channel_configurations": {f"Channel {i+1}": widget.value for i, widget in enumerate(self.channel_select_widgets)}
        }
        return config

    def download_dat_file(self, event):
        selected_directory = self.directory_selector.value[0]  # Assuming the directory is the first selected item
        filename = f"{self.filename_input.value}.dat"  # Construct filename with extension
        file_path = os.path.join(selected_directory, filename)  # Combine into a full path
        
        # Generate .dat file content
        channels_data = self.controller.dat_data()
        self.controller.create_dat_file(file_path, channels_data)
        #print(file_path, channels_data)
        self.show_original_finalize_layout()

    def show_original_finalize_layout(self, event=None):
        self.dynamic_finalize_layout.clear()
        self.dynamic_finalize_layout.extend([
            self.comment_input,
            self.save_config_button,
            self.save_dat_button,
            self.run_stimulation_button,
            self.upload_settings_button,
        ])
        self.back_button.visible = False
        self.directory_selector.visible = False
        self.download_json.visible = False
        self.download_dat.visible = False
    def on_any_change(self, event):
        self.update_table_data(None)

        # Example of connecting widgets to the on_any_change method
        watched_widgets = [
            self.waveform_group, self.modulation_type_group, self.amplitude_slider, 
            self.pulse_duration_slider, self.number_of_events_input, self.duration_between_events_slider,
            self.period_frequency_group, self.period_frequency_value_input, self.number_of_trains_input,
            self.train_duration_slider, self.accept_external_trigger, self.external_trigger_duration,
            # Include any other widgets that affect the table data
        ]

        for widget in watched_widgets:
            widget.param.watch(self.on_any_change, 'value')
    def set_run(self, event):
        self.dynamic_finalize_layout.clear()
        self.dynamic_finalize_layout.extend([
            pn.pane.Markdown('You are almost there! Set the file location for your .csv file.'),
            self.back_button,
            pn.Row(self.filename_input,self.file_extension_label_csv),
            self.directory_selector,
            self.start_run
        ])
        self.back_button.visible = True
        self.directory_selector.visible = True
        self.start_run.visible = True
        self.filename_input.visible = True
        self.file_extension_label_csv.visible = True
    def run_stimulation(self, event):
        self._update_visibility_and_content()
        self.download_csv_file(None)
        self.running_program(None)
        self.update_table_data(None)  # Update any GUI components as necessary after starting the stimulation
        self.controller.start_stimulation()  # Assuming start_stimulation is implemented

        

    def update_table_data(self, event):
        # Initialize data collection
        total_event_duration_in_us = self._calculate_total_event_duration()
        recommended_unit, converted_duration = self._convert_duration_and_unit(total_event_duration_in_us)

        # Update the data dictionary with calculated values
        data = {
            "Parameter": [
                "Waveform", "Voltage or Current", "Amplitude", "Pulse Duration",
                "Phase", self.period_frequency_group.value, "Event Count",
                "Event Duration", "External Triggering", "Total Trains",
                "Time Between Trains", "External Signal Duration", "Comments"
            ],
            "Value": [
                self.waveform_group.value,
                self.modulation_type_group.value,
                f"{self.amplitude_slider.value} {self.amplitude_unit_selector.value}",
                f"{self.pulse_duration_slider.value} {self.pulse_duration_unit_selector.value}",
                self.phase_text.object if self.phase_text.visible else "N/A",
                f"{self.period_frequency_value_input.value} {self.period_frequency_unit_selector.value if self.period_frequency_group.visible else 'N/A'}",
                self.number_of_events_input.value,
                f"{converted_duration} {recommended_unit}",
                "Yes" if self.accept_external_trigger.value else "No",
                self.number_of_trains_input.value,
                f"{self.train_duration_slider.value} {self.train_duration_unit_selector.value}",
                f"{self.external_trigger_duration.value} {self.external_trigger_duration_unit_selector.value}",
                self.comment_input.value
            ]
            }

        # Collect channel configurations
        channel_configs = {"Floating": [], "Cathode": [], "Anode": [], "Ground": []}
        for i, widget in enumerate(self.channel_select_widgets, start=1):
            channel_configs[widget.value].append(str(i))
        
        # Append channel configurations to the data dictionary
        for config, channels in channel_configs.items():
            data["Parameter"].append(config)
            data["Value"].append(", ".join(channels) if channels else "None")

        # Create DataFrame and update the table
        self.df = pd.DataFrame(data)
        self.table.object = self.df#.to_dict('list')  # Update the DataFrame widget with new data

    def load_settings_from_file(self, event):
        # Parse the uploaded file's content
        file_val = self.upload_settings_button.value
        
        #print(file_val)
        file_content = json.loads(file_val)
        
        # Update GUI widgets with settings from file
        self.waveform_group.value = file_content['waveform']
        self.modulation_type_group.value = file_content['modulation_type']
        self.amplitude_slider.value = file_content['amplitude']
        self.pulse_duration_slider.value = file_content['pulse_duration']
        self.number_of_events_input.value = file_content['number_of_events']
        self.duration_between_events_slider.value = file_content['duration_between_events']
        self.period_frequency_group.value = file_content['period_frequency_type'] if 'period_frequency_type' in file_content else 'Period'
        self.period_frequency_value_input.value = file_content['period_frequency_value']
        self.number_of_trains_input.value = file_content['total_trains']
        self.train_duration_slider.value = file_content['train_duration']
        self.accept_external_trigger.value = file_content['accept_external_trigger']
        self.external_trigger_duration.value = file_content['external_trigger_duration']
        self.amplitude_unit_selector.value = file_content['amplitude_unit']
        self.pulse_duration_unit_selector.value = file_content['pulse_duration_unit']
        self.duration_between_events_unit_selector.value = file_content['duration_between_events_unit']
        self.train_duration_unit_selector.value = file_content['train_duration_unit']
        self.external_trigger_duration_unit_selector.value = file_content['external_trigger_duration_unit']
        #print('MY VALUES:', self.waveform_group.value, 'Modulation type:', self.modulation_type_group.value)
        # Update channel configurations
        for channel_label, setting in file_content['channel_configurations'].items():
            channel_index = int(channel_label.split(' ')[1]) - 1  # Convert channel label to index
            self.channel_select_widgets[channel_index].value = setting

        # Ensure GUI updates are applied properly
        self._update_visibility_and_content()
        self.update_table_data(None)

    def running_program(self, event=None):
        self.dynamic_finalize_layout.clear()
        self.dynamic_finalize_layout.extend([
            pn.pane.Markdown('You are almost there! Set the file location for your .csv file.'),
            self.back_button,
            self.debugger,
            self.progress_bar
        ])
        self.back_button.visible = True
        self.debugger.visible = True
        logger.debug("This is a test debug message.")

    def show(self):
        return self.tabs

# To use the class and display the GUI in a notebook or as a Panel app
stim_gui = DynamicStimGui(logger=logger)
controller = STGDeviceController(stim_gui, logger=logger)
stim_gui.controller = controller
stim_gui.show().servable().show('Stimulation Gui')