// Minimal Arduino core mock for running the sketch natively.
// Single translation unit: every definition is inline or static on purpose.

#pragma once

#include <cstdint>
#include <string>
#include <vector>

#define HIGH 0x1
#define LOW 0x0
#define INPUT 0x0
#define OUTPUT 0x1
#define INPUT_PULLUP 0x2

namespace mock {

struct PinEvent {
  uint64_t t;
  uint8_t pin;
  uint8_t level;
};

struct DisplayEvent {
  uint64_t t;
  int value;  // digits as passed to showNumberDecEx, e.g. 459 for 04:59
};

struct State {
  uint64_t simMs = 0;          // simulated time since the "power-on"
  uint32_t millisOffset = 0;   // lets tests start near the millis() rollover
  uint8_t input[32];           // levels read by digitalRead()
  uint8_t output[32];          // last level written by digitalWrite()
  bool outputKnown[32];
  std::vector<PinEvent> pinEvents;
  std::vector<DisplayEvent> displayEvents;  // value changes only
  std::vector<std::string> callLog;         // pinMode / digitalWrite order
  int displayValue = -1;
  uint8_t displayDots = 0;
  uint32_t displayDraws = 0;   // every showNumberDecEx call
  uint32_t brightnessCalls = 0;
  int displayClkPin = -1;      // pins the sketch passed to the display driver
  int displayDioPin = -1;

  State() {
    for (int i = 0; i < 32; ++i) {
      input[i] = HIGH;  // idle level of a pulled-up input
      output[i] = LOW;
      outputKnown[i] = false;
    }
  }
};

inline State& st() {
  static State s;
  return s;
}

}  // namespace mock

inline unsigned long millis() {
  return static_cast<uint32_t>(mock::st().simMs + mock::st().millisOffset);
}

inline int digitalRead(uint8_t pin) { return mock::st().input[pin]; }

inline void pinMode(uint8_t pin, uint8_t mode) {
  const char* name = mode == OUTPUT ? "OUTPUT" : (mode == INPUT_PULLUP ? "INPUT_PULLUP" : "INPUT");
  mock::st().callLog.push_back("pinMode " + std::to_string(pin) + " " + name);
}

inline void digitalWrite(uint8_t pin, uint8_t level) {
  mock::State& s = mock::st();
  s.callLog.push_back("digitalWrite " + std::to_string(pin) + " " + std::to_string(level));
  if (!s.outputKnown[pin] || s.output[pin] != level) {
    s.pinEvents.push_back({s.simMs, pin, level});
  }
  s.output[pin] = level;
  s.outputKnown[pin] = true;
}

void setup();
void loop();
