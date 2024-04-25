#include <Arduino.h>

#define NUM_CHAN 16     //  Number of channels
#define NUM_LE    4     // Number od Latch Enables / Number of Channel Groups
#define NUM_CHAN_PER_GROUP  (NUM_CHAN/NUM_LE)
#define NUM_CONTROL  2  // Number of CONTROL pins per Channel Group
#define LE_0  1
#define LE_1  2
#define LE_2  3
#define LE_3  4
#define OE    16
#define CS_0  5
#define CS_1  (CS_0+1)
#define CS_2  (CS_0+2)
#define CS_3  (CS_0+3)
#define CS_4  (CS_0+4)
#define CS_5  (CS_0+5)
#define CS_6  (CS_0+9)
#define CS_7  (CS_0+10)


#define STATE_IDLE  0
#define STATE_GET_CHAN_NUM  1
#define STATE_GET_CHAN_VALUE  2
#define STATE_APPLY   3
#define STATE_ERROR   4
#define STATE_SET_DELAY 5
#define STATE_EXTERNAL_WAIT   6
#define STATE_EXECUTE_COMMAND 7
#define STATE_SET_LOOP   8
#define STATE_LOOP_EXECUTE 9

// Pin definitions
#define EXTERNAL_TRIGGER_PIN 2

long delayDuration = 0; // to store the delay duration
char delayUnit = 'u'; // default to microseconds
bool trig_started = false;

int loops_number = -1; // -1 indicates no looping by default
bool is_looping = false; // Whether looping is active
char commandHistory[1000];
int character_pos = 0;
int current_state = STATE_IDLE;

char channel_state[] = {'F','F','F','F','F','F','F','F','F','F','F','F','F','F','F','F'};
int le_state[NUM_LE] = {1, 1, 1, 1};
int le_gpio_pins[4] = {LE_0, LE_1, LE_2, LE_3} ; // Example GPIO pins, adjust as needed

struct Position {
    int x;
    int y;
};

Position map_value_to_logic(char value) {
    switch (value) {
        case 'F': return {0, 0};
        case 'C': return {1, 0};
        case 'A': return {0, 1};
        case 'G': return {1, 1};
        default:  return {-1, -1};
    }
}

int to_hex(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    else if (c >= 'a' && c <= 'f') return (c - 'a') + 10;
    else if (c >= 'A' && c <= 'F') return (c - 'A') + 10;
    else return -1;
}

int sp3t_selector_gpio_pins[NUM_LE][NUM_CONTROL] = {
    {CS_0, CS_1}, // Pins for channel group 0
    {CS_2, CS_3}, // Pins for channel group 1
    {CS_4, CS_5}, // Pins for channel group 2
    {CS_6, CS_7} // Pins for channel group 3
};

int is_channel_value(char c) {
    switch(c) {
      case 'A':
      case 'C':
      case 'F':
      case 'G':
      case 'a':
      case 'c':
      case 'f':
      case 'g':
        return 1;
      default:
        return 0;
    }
}

void set_channel_state(int channel, Position pos) {
    int group = floor(channel / 4);
    int channelWithinGroup = channel % 4;
    int x = sp3t_selector_gpio_pins[channelWithinGroup][0];
    int y = sp3t_selector_gpio_pins[channelWithinGroup][1];

    digitalWrite(x, pos.x);
    digitalWrite(y, pos.y);
    Serial.print("Setting Pin ");
    Serial.print(x);
    Serial.print(" to ");
    Serial.println(pos.x);
    Serial.print("and Setting Pin ");
    Serial.print(y);
    Serial.print(" to ");
    Serial.println(pos.y);
}

void setup_and_latch(int gn) {
   

    for (int channel = gn*NUM_CHAN_PER_GROUP; channel < gn*NUM_CHAN_PER_GROUP + NUM_CHAN_PER_GROUP; channel++) {
        Position pos = map_value_to_logic(channel_state[channel]);
        set_channel_state(channel, pos);
    }
     // Activate and deactivate LE pin for the group with precise timing
     Serial.print("Toggling LE pin: ");
     Serial.println(le_gpio_pins[gn]);
    digitalWrite(le_gpio_pins[gn], HIGH);
    delayMicroseconds(3);
    digitalWrite(le_gpio_pins[gn], LOW);
}

void setup() {
    Serial.begin(115200);
    while (!Serial) continue; // Wait for Serial port to connect
    for (int i = LE_0; i <= LE_3; ++i) { // Setup LE pins as output
        pinMode(i, OUTPUT);
    }
    for (int i = CS_0; i <= CS_7; ++i) { // Setup CS pins as output
        pinMode(i, OUTPUT);
    }
    pinMode(OE, OUTPUT); // Setup OE pin as output
    pinMode(EXTERNAL_TRIGGER_PIN, INPUT); // Setup external trigger pin as input
    for (int i = 0; i < 50; i++) {
        commandHistory[i] = 0;
    }
    apply();
}

int get_char() {
  if (Serial.available() > 0) {
    char ch = Serial.read();
    Serial.print("GOT: ");
    Serial.println(ch);
    commandHistory[character_pos] = ch;
    character_pos++;
    Serial.println(commandHistory);
    return ch;
  } else if (is_looping == true)
  {
    Serial.println(character_pos);
    char ch = commandHistory[character_pos];
    Serial.print("GOT: ");
    Serial.println(ch);
    character_pos++;
    return ch;
  }
}

void print_current_state() {
  Serial.print( "[CS=>");
  for (int i=0; i < NUM_CHAN; i++) {
    Serial.print(channel_state[i]);
  }
  Serial.println("]\n");
}

void set_channel_value(int n, char v) {
  channel_state[n] = v;
  int gn = n / NUM_LE;
  le_state[gn] = 1;
}

void apply() {
  digitalWrite(OE, HIGH); // Disable output
  
  for (int gn = 0; gn < NUM_LE; gn++) {
    if (le_state[gn] == 0)
      continue;
    // Program the CS and toggle LE and reset LE to 0
    setup_and_latch(gn);
    le_state[gn] = 0;
  }
  digitalWrite(OE, LOW); // Enable output
  print_current_state();
}


void loop()
{
static char c = '\0';  // Initialize with a non-numeric and non-control value
static int current_chan_num;

//Serial.print(current_state);

switch (current_state) {
  case STATE_IDLE:
  {
    //Serial.println("State Idle");
    c = get_char();
    if (c == 'l') {
        Serial.println("Loop command detected.");
        current_state = STATE_SET_LOOP;
    }
    else if (c == -1)
      break;
    else if (c == 'x') {
      Serial.println("Reading!");
      current_state = STATE_EXTERNAL_WAIT;
      break;
    } else if (c == '[') {
      Serial.println("Reading!");
      current_state = STATE_GET_CHAN_NUM;
      break;
    } else if (c == -1)
        trig_started = true;
        break; // No data available
    break;
  }
  case STATE_GET_CHAN_NUM:
  {
    Serial.println("State Get Chan Num");
    c = get_char();
    if (c == -1) {
      Serial.println("Failed to get chan num");
      break;
    } else if (c == ']') {
      Serial.println("Headed to apply from CHAN NUM!");
      current_state = STATE_APPLY;
      break;
    } else {
      current_chan_num = to_hex(c);
      Serial.println(current_chan_num);
      if (current_chan_num == -1) {
        Serial.println("UH OH!");
        current_state = STATE_IDLE;
        break;
      } else {
        current_state = STATE_GET_CHAN_VALUE;
        break;
      }
    }
}
  case STATE_GET_CHAN_VALUE:
  {
    Serial.println("State Get Chan Value");
    c = get_char();
    if (c == -1)
      break;
    else if (c == ']') {
      Serial.println("Headed to Apply from CHAN VALUE");
      current_state = STATE_APPLY;
      break;
    }
    int tf = is_channel_value(c);
    if (tf == 0) {
      Serial.println("Uh oh at is_channel_value");
      current_state = STATE_IDLE;
      break;
    } else {
      set_channel_value(current_chan_num, c);
      current_state = STATE_GET_CHAN_NUM;
      Serial.println(c);
      break;
    }
  }
  case STATE_APPLY:
  {
    Serial.println("State Apply");
    apply();
    current_state = STATE_SET_DELAY; // Move to the new state to set delay
    delayDuration = 0; // Reset delay duration
    delayUnit = 'u'; // Reset to default microseconds
    c = '\0'; // IMPORTANT: Reset 'c' so the delay state can process new characters
    break;
  }
  case STATE_EXTERNAL_WAIT:
  {
      while (digitalRead(EXTERNAL_TRIGGER_PIN) != HIGH) {
        if (trig_started == true) trig_started = false;
          //if (message_sent == false) Serial.println("Waiting for External Trigger...");
          delayMicroseconds(1);
      }
      while (digitalRead(EXTERNAL_TRIGGER_PIN) == HIGH && trig_started == false){
          Serial.println("External trigger received, continuing...");
          trig_started = true;
          current_state = STATE_APPLY;
      }
      //if (message_sent == false) Serial.println("Waiting for External Trigger to end");
      delayMicroseconds(1);
      break;
  }
  case STATE_SET_DELAY:
  {
    Serial.println("State Set Delay");
    if (c == '\0') {
        c = get_char(); // Get the next character if we need to start processing delay
    }

    // If 'c' is not a digit and not a delay unit, reset the state machine
    if (c == '[') {
      // ... handle the case for '['
    } else if (c < '0' || c > '9') {
      // We received a non-digit, non-unit character, go back to idle
      current_state = STATE_IDLE;
    }

    if (c == -1)
        break; // No data available

    if (c >= '0' && c <= '9') {
        delayDuration = delayDuration * 10 + (c - '0'); // Building the number
        c = '\0';  // We consumed this character, reset 'c' to read a new one next time
    } else if (c == 's' || c == 'm' || c == 'u') {
        delayUnit = c; // Set the correct delay unit
        // Apply the delay based on the unit
        if (delayUnit == 's'){
            Serial.println(delayDuration);
            Serial.print(' s Delay');
            delay(delayDuration * 1000);
        }
        else if (delayUnit == 'm'){
            Serial.println(delayDuration);
            Serial.print(' ms Delay');
            delay(delayDuration);
        }
        else if (delayUnit == 'u'){
            Serial.println(delayDuration);
            Serial.print(' u Delay');
            delayMicroseconds(delayDuration);
        }
        current_state = STATE_IDLE; // Delay has been applied, go back to idle
        c = '\0';  // We consumed this character, reset 'c' to read a new one next time
    } else {
        // If we get any other character, we assume there is no delay and go back to idle
        // This handles the case where ']' is immediately followed by '[' or any other non-numeric character
        current_state = STATE_IDLE;
    }
    break;
  }
  case STATE_ERROR:
  {
    Serial.print("ERROR got unexpected character");
    Serial.println(c);
    c = get_char();
    current_state = STATE_IDLE;
    break;
  }
  case STATE_SET_LOOP:
  {
    bool number_given = false;
    c = get_char();
    if (isdigit(c)) {
        loops_number = (loops_number == -1 ? 0 : loops_number) * 10 + (c - '0');
        bool number_given = true;
        Serial.print("Number of Loops: ");
        Serial.println(loops_number);
    } else if ((c == 'l' || c == '\0') && number_given == true) {
        loops_number = -1; // Set infinite loop on 'l' or no input
        Serial.print("Infinite loop set.");
        current_state = STATE_LOOP_EXECUTE;
    } else {
        is_looping = true;
        Serial.println("Starting loop execution.");
        current_state = STATE_LOOP_EXECUTE;
    }
    break;

  }
  case STATE_LOOP_EXECUTE:
  {
      if (is_looping) {
          Serial.println("Replaying commands:");
          Serial.println(commandHistory);  // Print the entire command history

          if (loops_number > 0) {  // Decrement loop count if not infinite
              loops_number--;
              Serial.print("Loops remaining: ");
              Serial.println(loops_number);
              if (loops_number == 0) {  // Check if loops are finished
                  is_looping = false;
                  for (int i = 0; i < 50; i++) {  // Clear command history
                      commandHistory[i] = 0;
                  }
                  current_state = STATE_IDLE;
              }
          } else if (loops_number == -1) {  // Handle infinite loop separately
              // Keep looping or add condition to break infinite loop
          }
      } else {
          current_state = STATE_IDLE;  // Ensure the state returns to IDLE if not looping
      }
      break;
  }
    // other states as necessary
  default:
  {
    Serial.print("Unknown state");
    Serial.println(current_state);
  }
}
}


