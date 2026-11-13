/*
 * SPDX-License-Identifier: CC-BY-NC-4.0
 * Copyright (c) 2025-2026 diggahpl - https://github.com/diggahpl/Regatta-start-timer
 *
 * Regatta Start Timer
 *
 * One short press of START runs the five-minute start sequence. The relay
 * output (D6) sounds the horn at 05:00, 04:00, 01:00 and 00:00. Holding START
 * for three seconds aborts the sequence and returns to 05:00.
 *
 * Settings: Config.h        Wiring: docs/hardware.md
 * Behaviour: docs/firmware.md
 */

#include <Arduino.h>
#include <TM1637Display.h>

#include "Config.h"

struct SoundCue {
  uint32_t atMs;        // time from the accepted START
  uint32_t durationMs;  // how long the relay stays pulled in
};

constexpr SoundCue SOUND_CUES[] = {
  {0UL, SOUND_AT_FIVE_MS},
  {60UL * 1000UL, SOUND_AT_FOUR_MS},
  {240UL * 1000UL, SOUND_AT_ONE_MS},
  {COUNTDOWN_MS, SOUND_AT_START_MS},
};

// The cycle is over when the last sound has finished.
constexpr uint32_t CYCLE_END_MS = COUNTDOWN_MS + SOUND_AT_START_MS;

TM1637Display display(PIN_TM_CLK, PIN_TM_DIO);
uint16_t displayedSeconds = UINT16_MAX;
uint32_t displayDrawnAt = 0;

bool cycleActive = false;
uint32_t cycleStartedAt = 0;

// Button state machine
bool rawPressed = false;        // instantaneous reading
bool stablePressed = false;     // reading stable for DEBOUNCE_MS
bool pressTracked = false;      // a stable press that may still become a click
bool startPermitted = false;    // the current press may start a cycle
bool releaseGapActive = false;  // PRESS_GAP_MS after the last release
uint32_t rawChangedAt = 0;
uint32_t pressStartedAt = 0;
uint32_t releasedAt = 0;

void setHorn(bool on) {
  digitalWrite(PIN_HORN_RELAY, on ? HORN_LEVEL_ON : HORN_LEVEL_OFF);
}

// Milliseconds since the accepted START, corrected by CLOCK_TRIM_PPM.
uint32_t cycleElapsedMs(uint32_t now) {
  const uint32_t rawMs = now - cycleStartedAt;
  if (CLOCK_TRIM_PPM == 0) {
    return rawMs;
  }
  return static_cast<uint32_t>(static_cast<uint64_t>(rawMs) *
                               static_cast<uint32_t>(1000000L + CLOCK_TRIM_PPM) /
                               1000000UL);
}

void showTime(uint16_t seconds, uint32_t now) {
  if (seconds == displayedSeconds && now - displayDrawnAt < DISPLAY_REFRESH_MS) {
    return;
  }
  displayedSeconds = seconds;
  displayDrawnAt = now;
  const int minutesAndSeconds = (seconds / 60) * 100 + seconds % 60;
  display.showNumberDecEx(minutesAndSeconds, COLON_MASK, true);
}

void updateButton(uint32_t now) {
  const bool reading = digitalRead(PIN_START) == LOW;
  if (reading != rawPressed) {
    rawPressed = reading;
    rawChangedAt = now;
    if (rawPressed && !stablePressed) {
      // The pause is checked at the moment of the press, before debouncing.
      const bool gapPassed = !releaseGapActive || now - releasedAt >= PRESS_GAP_MS;
      startPermitted = !cycleActive && gapPassed;
    }
  }

  if (rawPressed != stablePressed && now - rawChangedAt >= DEBOUNCE_MS) {
    stablePressed = rawPressed;
    if (stablePressed) {
      pressStartedAt = rawChangedAt;
      pressTracked = true;
    } else {
      if (pressTracked) {
        if (rawChangedAt - pressStartedAt >= RESET_HOLD_MS) {
          cycleActive = false;
        } else if (startPermitted) {
          cycleStartedAt = now;
          cycleActive = true;
        }
      }
      pressTracked = false;
      releasedAt = rawChangedAt;
      releaseGapActive = true;
    }
  }

  // Long press: abort while the button is still held.
  if (pressTracked && rawPressed && now - pressStartedAt >= RESET_HOLD_MS) {
    cycleActive = false;
    pressTracked = false;
  }

  if (!rawPressed && !stablePressed && releaseGapActive &&
      now - releasedAt >= PRESS_GAP_MS) {
    releaseGapActive = false;
  }
}

void updateOutputs(uint32_t now) {
  if (!cycleActive) {
    setHorn(false);
    digitalWrite(PIN_LED, HIGH);
    showTime(START_SECONDS, now);
    return;
  }

  const uint32_t elapsedMs = cycleElapsedMs(now);

  // A window that has already closed is skipped, never played late.
  bool hornOn = false;
  for (const SoundCue& cue : SOUND_CUES) {
    if (elapsedMs >= cue.atMs && elapsedMs - cue.atMs < cue.durationMs) {
      hornOn = true;
      break;
    }
  }
  setHorn(hornOn);

  if (elapsedMs >= COUNTDOWN_MS) {
    digitalWrite(PIN_LED, HIGH);
    showTime(0, now);
  } else {
    const bool ledOn = (elapsedMs / 500UL) % 2 == 0;
    digitalWrite(PIN_LED, ledOn ? HIGH : LOW);
    // Round up so that 00:00 appears together with the starting signal.
    showTime((COUNTDOWN_MS - elapsedMs + 999UL) / 1000UL, now);
  }
}

void setup() {
  // Release the relay before the pin becomes an output, so it never pulses.
  setHorn(false);
  pinMode(PIN_HORN_RELAY, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_START, INPUT_PULLUP);

  // A button that is already pressed at power-up must not start a cycle.
  rawPressed = stablePressed = digitalRead(PIN_START) == LOW;
  rawChangedAt = millis();

  display.setBrightness(DISPLAY_BRIGHTNESS);
  updateOutputs(rawChangedAt);
}

void loop() {
  const uint32_t now = millis();
  if (cycleActive && cycleElapsedMs(now) >= CYCLE_END_MS) {
    cycleActive = false;
  }
  updateButton(now);
  updateOutputs(now);
}
