import panel as pn
from panel.widgets import CheckButtonGroup, Button
import gpiozero
import random
import time
import sys

class SimulatedGPIO:
    @staticmethod
    def setup(pin, mode):
        print(f"Setting up {pin} as {mode}")

    @staticmethod
    def output(pin, state):
        print(f"Setting {pin} to {state}")

GPIO = SimulatedGPIO
# Define the mappings for the electrode pins
channel_state = [None] * 16

oe_pin = 22
oe_device = None

le_gpio_pins = [ 23, 24, 25, 27 ]
le_gpio_devices = [ ]

def chan_to_le(chan):
    return (chan-1)%4


state2pin_logic_map = {
    "C" : [ 1, 0 ],
    "A" : [ 0, 1 ],
    "G" : [ 1, 1 ],
    "F" : [ 0, 0 ]
}


sp3t_selector_gpio_pins = [
    [5, 6],
    [12, 13],
    [16, 17],
    [19, 26]
]

sp3t_selector_gpio_devices = []



def chan_to_sp3t(chan):
    return int((chan-1)/4)

# UI sets channel_state array values to A/C/G#thencalls the folllwing routine

def init_gpio_devices():
    global oe_device
    oe_device= gpiozero.DigitalOutputDevice(oe_pin)
    for inx in range(4):
        pins = sp3t_selector_gpio_pins[inx]
        sp3t_selector_gpio_devices.append([
            gpiozero.DigitalOutputDevice(pins[0]),
            gpiozero.DigitalOutputDevice(pins[1])
        ])
        le_gpio_devices.append(
            gpiozero.DigitalOutputDevice(le_gpio_pins[inx])
        )

def setup_and_latch():
    oe_device.on()
    for cgroup in range(0,4):
        le_pin = le_gpio_pins[cgroup]
        le_device=le_gpio_devices[cgroup]
        for rch in range(0, 4):
            channel = cgroup * 4 + rch
            state = channel_state[channel]
            sp3t_logic_values = state2pin_logic_map[state]
            print(f'{state= } {sp3t_logic_values= }')
            sp3t = ""
            #print("SP3T selector devies: ", sp3t_selector_gpio_devices[rch])
            for inx, device in enumerate(sp3t_selector_gpio_devices[rch]):
                sp3t_pins = sp3t_selector_gpio_pins[rch]
                logic = sp3t_logic_values
                #print(sp3t_pins, logic)
                sp3t += f' GPIO{sp3t_pins} = {logic}'
                if logic[inx] == 1:
                    device.on()
                else:
                    device.off()
                print(f'Setting {channel = }  {state = }, {cgroup = } {le_pin = } {sp3t}')
            
       
        le_device.on()
        time.sleep(0.001)
        le_device.off()
    oe_device.off()

def main():
    init_gpio_devices()
    #if len(sys.argv) == 2:
    #    ch_val=sys.argv[1]
    #else:
    #    ch_val = None
    #for i in range(16):
    #    channel_state[i] = ch_val if ch_val is not None else random.choice(["A", "C","G","F"])
    channel_state = ["C","A","G","G","G","G","G","G","G","G","G","G","G","G","G","G"]
    print(f'{channel_state = }')
    setup_and_latch()
    channel_state = ["G","G","C","A","G","G","G","G","G","G","G","G","G","G","G","G"]
    print(f'{channel_state = }')
    setup_and_latch()

if __name__ == "__main__":
    main()
    time.sleep(100)

"""
def set_electrode_state(electrode_num, state):
    if electrode_num not in electrode_mappings:
        print("Invalid electrode number")
        return
    
    if state not in electrode_mappings[electrode_num]:
        print("Invalid state")
        return
    
    ground_pins = electrode_mappings[electrode_num]["G"]
    for pin in ground_pins:
        GPIO.setup(pin, "OUTPUT")
        GPIO.output(pin, True)
    
    # Get the LE pin for this electrode
    le_group = (electrode_num - 1) // 4 + 1
    le_pin = LE_pins[le_group]
    
    oe_pin = "GP22"
    
    state_pins = electrode_mappings[electrode_num][state]
    
    GPIO.setup(le_pin, "OUTPUT")
    GPIO.output(le_pin, True)
    
    GPIO.setup(oe_pin, "OUTPUT")
    GPIO.output(oe_pin, True)
    
    for pin in state_pins:
        GPIO.setup(pin, "OUTPUT")
        GPIO.output(pin, True)

electrode_selector = pn.widgets.Select(name='Select Electrode Pin', options=list(range(1, 17)))

state_selector = CheckButtonGroup(name='Select State', options=['C', 'A', 'G'])

apply_button = Button(name="Apply Configuration", button_type="primary")

def apply_configuration(event):
    electrode_num = electrode_selector.value
    
    for state in state_selector.value:
        set_electrode_state(electrode_num, state)
        break

def update_checkbox_group(attr, old, new):
    if len(new) > 1:
        state_selector.value = [new[-1]]

state_selector.param.watch(update_checkbox_group, 'value')

apply_button.on_click(apply_configuration)

layout = pn.Column(pn.Row(electrode_selector, state_selector),apply_button)

layout.servable()
pn.serve(layout)
"""