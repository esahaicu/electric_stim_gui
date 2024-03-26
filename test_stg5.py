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

class DynamicStimGui:
    def __init__(self):
        self.channel_buttons = {}  # Stores RadioButtonGroup for each channel
        self._setup_widgets()
        self._setup_layout()
        self._connect_callbacks()
        self._setup_finalize_tab()

    
    def _setup_widgets(self):
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
    



        ### TRAIN WIDGETS
        self.number_of_trains_input = pn.widgets.IntInput(name='Number of Trains', value=1, start=1, end=100)
        self.train_duration_slider = pn.widgets.EditableIntSlider(name='Minimum Train Duration', start=0, end=1000000, step=1, value=100)
        self.randomize_number_of_trains = pn.widgets.Button(name='Randomize', button_type='warning')
        self.randomize_train_duration = pn.widgets.Button(name='Randomize', button_type='warning')
        self.accept_external_trigger = pn.widgets.Toggle(name='Accept External Trigger for Train?', value=False)




        # External Trigger Widgets
        self.external_trigger_duration = pn.widgets.EditableIntSlider(name='External Trigger Duration', start=0, end=1000000, step=1, value=100)
        self.randomize_external_trigger = pn.widgets.Button(name='Randomize', button_type='warning')
        self.set_to_pulse_duration = pn.widgets.Button(name='Set to Pulse Duration', button_type='primary')

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
            self.waveform_group,
            self.modulation_type_group,
            pn.Row(self.amplitude_slider, self.randomize_amplitude),
            pn.Row(self.pulse_duration_slider, self.randomize_pulse_duration),
            self.period_frequency_group,
            pn.Row(self.period_frequency_value_input, self.randomize_period_frequency_value),
            pn.Row(self.number_of_events_input, self.randomize_number_of_events),
            pn.Row(self.duration_between_events_slider, self.randomize_duration_between_events),
            self.phase_text,
            self.sinusoidal_calculation_text,
        )
        # Train Settings layout
        train_settings_layout = pn.Column(
            self.accept_external_trigger,
            pn.Row(self.number_of_trains_input,self.randomize_number_of_trains),
            pn.Row(self.train_duration_slider,self.randomize_train_duration),
        )
        
        external_trigger_layout = pn.Column(
            self.external_trigger_duration,
            self.randomize_external_trigger,
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
    def _connect_callbacks(self):
        #Event Settings
        self.waveform_group.param.watch(self._update_visibility_and_content, 'value')
        self.number_of_events_input.param.watch(self._update_visibility_and_content, 'value')
        self.amplitude_slider.param.watch(self._update_visibility_and_content, 'value')
        self.period_frequency_group.param.watch(self._update_visibility_and_content, 'value')
        self.period_frequency_value_input.param.watch(self._update_visibility_and_content, 'value')
        self.randomize_amplitude.on_click(self._randomize_amplitude)
        self.randomize_pulse_duration.on_click(self._randomize_pulse_duration)
        self.randomize_number_of_events.on_click(self._randomize_number_of_events)
        self.randomize_duration_between_events.on_click(self._randomize_duration_between_events)
        self.randomize_period_frequency_value.on_click(self._randomize_period_frequency_value)        
        
        #Train Settings
        self.number_of_trains_input.param.watch(self._update_train_settings, 'value')
        self.train_duration_slider.param.watch(self._update_train_settings, 'value')
        self.accept_external_trigger.param.watch(self._update_train_settings_visibility, 'value')
        self.randomize_number_of_trains.on_click(self._randomize_number_of_trains)
        self.randomize_train_duration.on_click(self._randomize_train_duration)
        
        # Ensure updates to Train Duration are based on Event Settings

        #External Trigger Settings
        self.randomize_external_trigger.on_click(self._randomize_external_trigger)
        self.set_to_pulse_duration.on_click(self._set_to_pulse_duration)

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


        ### Channel Setting
        self.random_ca_button.on_click(self.randomize_cathode_anode)


    def _update_visibility_and_content(self, event):
        is_sinusoidal = self.waveform_group.value == 'Sinusoidal'
        self.pulse_duration_slider.visible = not is_sinusoidal
        self.randomize_pulse_duration.visible = not is_sinusoidal
        self.period_frequency_group.visible = is_sinusoidal
        self.period_frequency_value_input.visible = is_sinusoidal
        self.randomize_period_frequency_value.visible = is_sinusoidal
        self.sinusoidal_calculation_text.visible = is_sinusoidal
        self.duration_between_events_slider.visible = self.number_of_events_input.value > 1
        self.randomize_duration_between_events.visible = self.number_of_events_input.value > 1
        self.phase_text.visible = self.waveform_group.value == 'Biphasic'
        
        if self.waveform_group.value == 'Biphasic':
            if self.amplitude_slider.value < 0:
                self.phase_text.object = "Phase: Cathode Leading"
            elif self.amplitude_slider.value > 0:
                self.phase_text.object = "Phase: Anode Leading"
            else:
                self.phase_text.object = "Phase: None"
        
        if is_sinusoidal:
            self.period_frequency_value_input.name = self.period_frequency_group.value
            if self.period_frequency_group.value == 'Period':
                freq = 1 / self.period_frequency_value_input.value if self.period_frequency_value_input.value != 0 else 0
                self.sinusoidal_calculation_text.object = f"Calculated Frequency: {freq} Hz"
            else:
                period = 1 / self.period_frequency_value_input.value if self.period_frequency_value_input.value != 0 else 0
                self.sinusoidal_calculation_text.object = f"Calculated Period: {period} seconds"
    def _randomize_amplitude(self, event):
        self.amplitude_slider.value = np.random.randint(self.amplitude_slider.start, self.amplitude_slider.end)

    def _randomize_pulse_duration(self, event):
        self.pulse_duration_slider.value = np.random.randint(self.pulse_duration_slider.start, self.pulse_duration_slider.end)

    def _randomize_number_of_events(self, event):
        self.number_of_events_input.value = np.random.randint(self.number_of_events_input.start, self.number_of_events_input.end + 1)

    def _randomize_duration_between_events(self, event):
        self.duration_between_events_slider.value = np.random.randint(self.duration_between_events_slider.start, self.duration_between_events_slider.end)

    def _randomize_period_frequency_value(self, event):
        self.period_frequency_value_input.value = np.random.randint(self.period_frequency_value_input.start, self.period_frequency_value_input.end + 1)

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
    
    def _set_to_pulse_duration(self, event):
        duration_between_events = self.duration_between_events_slider.value if self.number_of_events_input.value > 1 else 0
        if self.waveform_group.value == 'Monophasic':
            self.external_trigger_duration.value = (self.pulse_duration_slider.value + duration_between_events) * self.number_of_events_input.value
        elif self.waveform_group.value == 'Biphasic':
            self.external_trigger_duration.value = (2 * self.pulse_duration_slider.value + duration_between_events) * self.number_of_events_input.value
        elif self.waveform_group.value == 'Sinusoidal':
            self.external_trigger_duration.value = (self.period_frequency_value_input.value + duration_between_events) * self.number_of_events_input.value
    
    
    
    #GRAPHING
    def update_projected_graphs(self):
        # Generate plots based on current inputs
        single_event_plot = self.generate_single_event_plot(
                self.amplitude_slider.value, 
                self.pulse_duration_slider.value, 
                self.waveform_group.value, 
                self.external_trigger_duration.value,
                self.duration_between_events_slider.value if self.number_of_events_input.value > 1 else 0, 
                self.number_of_events_input.value, 
                self.period_frequency_value_input.value,
                self.period_frequency_group.value
                
            )

        full_sequence_plot = self.generate_full_sequence_plot(
            self.amplitude_slider.value, 
            self.pulse_duration_slider.value, 
            self.waveform_group.value, 
            self.number_of_events_input.value, 
            self.duration_between_events_slider.value if self.number_of_events_input.value > 1 else 0, 
            self.external_trigger_duration.value,
            self.number_of_trains_input.value,
            self.train_duration_slider.value,
            self.period_frequency_value_input.value,
            self.period_frequency_group.value
        )

        self.projected_graphs_layout.clear()
        self.projected_graphs_layout.extend([pn.panel(single_event_plot), pn.panel(full_sequence_plot)])

    def generate_single_event_plot(self, amplitude, pulse_duration, waveform_type, trigger_duration, duration_between_events, number_of_events, period_frequency, period_frequency_type):
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
            xlabel='Time (s)', ylabel='Amplitude'
        ).opts(title="Single Event Plot", framewise=True, shared_axes=False)
        return plot


    def generate_full_sequence_plot(self, amplitude, pulse_duration, waveform_type, number_of_events, duration_between_events, trigger_duration, number_of_trains, delay_between_trains, period_frequency, period_frequency_type):
        
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
            xlabel='Time (s)', ylabel='Amplitude'
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
        # Comment Input
        self.comment_input = pn.widgets.TextInput(name="Comments", placeholder="Add any comment here...")
        
        # Finalize Button - to update the table
        self.update_table_button = pn.widgets.Button(name="Update Table", button_type="primary")
        self.update_table_button.on_click(self.update_table_data)
        
        # Placeholder for the table
        self.table = pn.pane.DataFrame(pd.DataFrame(), index=False)
        self.update_table_data  # Populate the table with initial data
        
        # Adding the comment input and button to the layout
        finalize_layout = pn.Column(self.comment_input, self.update_table_button, self.table)
        
        # Add this layout to the tabs
        self.tabs.append(('Finalize', finalize_layout))
    def update_table_data(self, event):
        # Initialize data collection
        data = {
            "Parameter": [
                "Waveform", "Voltage or Current", "Amplitude", "Pulse Duration",
                "Phase", self.period_frequency_group.value, "Calculated Frequency",
                "Event Count", "Event Duration", "External Triggering",
                "Total Trains", "Time Between Trains", "External Signal Duration",
                "Comments"
            ],
            "Value": [
                self.waveform_group.value,
                self.modulation_type_group.value,
                f"{self.amplitude_slider.value} uA",
                f"{self.pulse_duration_slider.value} us",
                self.phase_text.object,
                f"{self.period_frequency_value_input.value}",
                "Calculated value here",  # You need to calculate this based on your logic
                self.number_of_events_input.value,
                f"{self.duration_between_events_slider.value if self.number_of_events_input.value > 1 else 0} ms",
                "Yes" if self.accept_external_trigger.value else "No",
                self.number_of_trains_input.value,
                f"{self.train_duration_slider.value} ms",
                f"{self.external_trigger_duration.value} us",
                self.comment_input.value  # Make sure to include the TextInput widget for comments in your class
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





    def show(self):
        return self.tabs

# To use the class and display the GUI in a notebook or as a Panel app
stim_gui = DynamicStimGui()
stim_gui.show().servable().show(8080)