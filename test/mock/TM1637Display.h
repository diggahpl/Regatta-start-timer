// Mock of the avishorp TM1637 library API used by the sketch.

#pragma once

#include <cstdint>

#include "Arduino.h"

class TM1637Display {
 public:
  TM1637Display(uint8_t pinClk, uint8_t pinDIO, unsigned int bitDelay = 100) {
    (void)bitDelay;
    mock::st().displayClkPin = pinClk;
    mock::st().displayDioPin = pinDIO;
  }

  void setBrightness(uint8_t brightness, bool on = true) {
    (void)brightness;
    (void)on;
    mock::st().brightnessCalls++;
  }

  void showNumberDecEx(int num, uint8_t dots = 0, bool leading_zero = false,
                       uint8_t length = 4, uint8_t pos = 0) {
    (void)leading_zero;
    (void)length;
    (void)pos;
    mock::State& s = mock::st();
    s.displayDraws++;
    s.displayDots = dots;
    if (num != s.displayValue) {
      s.displayEvents.push_back({s.simMs, num});
      s.displayValue = num;
    }
  }
};
